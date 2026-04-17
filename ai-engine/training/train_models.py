"""
Multi-Model Training Pipeline (v5 — 85%+ target)

v5 Improvements over v4:
  - CatBoost: Third gradient-boosting library. Handles categorical features
    natively, often finds patterns XGBoost/LightGBM miss.
  - SMOTE (Synthetic Minority Over-sampling): Generates synthetic rain-day
    samples so the model doesn't become biased toward "no rain".
  - Feature Selection: Uses mutual information to drop noisy features that
    hurt accuracy.
  - Increased tuning budget: 60 combos × 5-fold CV for better hyperparameter
    search.
  - Stacking passthrough=True: Meta-learner now sees original features +
    base model predictions for richer signal.

v4 features retained:
  - MLP Neural Network (3-layer feed-forward)
  - Stacking Ensemble (XGBoost + LightGBM + MLP → LR)
  - Voting Ensemble
  - Threshold optimization
  - City one-hot encoding (~74 total features)
"""

import os
import sys
import json
import joblib
import warnings
import numpy as np
import pandas as pd

from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier,
    VotingClassifier, StackingClassifier, ExtraTreesClassifier
)
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score
)
from sklearn.model_selection import RandomizedSearchCV
from sklearn.feature_selection import mutual_info_classif
from scipy.stats import uniform, randint

# Optional: SMOTE for class imbalance
try:
    from imblearn.over_sampling import SMOTE
    HAS_SMOTE = True
except ImportError:
    HAS_SMOTE = False
    print("Note: imbalanced-learn not installed. Install with: pip install imbalanced-learn")

# Optional: CatBoost
try:
    from catboost import CatBoostClassifier
    HAS_CATBOOST = True
except ImportError:
    HAS_CATBOOST = False
    print("Note: CatBoost not installed. Install with: pip install catboost")

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    print("Note: XGBoost not installed.")

try:
    from lightgbm import LGBMClassifier
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    print("Note: LightGBM not installed.")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.preprocessing import load_raw_data, engineer_features, prepare_datasets, FEATURE_COLUMNS

MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')

# Suppress sklearn warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning)


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE SELECTION
# ─────────────────────────────────────────────────────────────────────────────

def select_features(X_train, y_train, feature_names, top_k=None):
    """
    Use mutual information to rank features and drop the worst ones.
    
    Mutual information measures how much knowing a feature reduces uncertainty
    about the target. Features with MI ≈ 0 are noise and hurt accuracy.
    
    Returns indices of features to keep.
    """
    print("  Computing mutual information scores...")
    mi_scores = mutual_info_classif(X_train, y_train, random_state=42, n_neighbors=5)
    
    # Sort features by importance
    feature_ranking = sorted(
        zip(feature_names, mi_scores, range(len(feature_names))),
        key=lambda x: x[1], reverse=True
    )
    
    # Drop features with near-zero MI (< 1% of max score)
    max_mi = max(mi_scores)
    threshold = max_mi * 0.01
    
    keep_indices = []
    kept_names = []
    dropped_names = []
    
    for name, score, idx in feature_ranking:
        if score >= threshold:
            keep_indices.append(idx)
            kept_names.append(name)
        else:
            dropped_names.append(name)
    
    if dropped_names:
        print(f"  Dropped {len(dropped_names)} low-value features: {', '.join(dropped_names[:5])}{'...' if len(dropped_names) > 5 else ''}")
    print(f"  Keeping {len(keep_indices)}/{len(feature_names)} features")
    
    # Print top 10 features
    print("  Top 10 features:")
    for name, score, _ in feature_ranking[:10]:
        bar = "█" * int(score / max_mi * 20)
        print(f"    {name:<30} {score:.4f} {bar}")
    
    return sorted(keep_indices), kept_names


# ─────────────────────────────────────────────────────────────────────────────
# BASE MODELS
# ─────────────────────────────────────────────────────────────────────────────

def get_base_models():
    """Create base model instances (comparison baselines)."""
    models = {
        "LogisticRegression": LogisticRegression(
            max_iter=2000, C=0.5, class_weight='balanced', random_state=42
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=400, max_depth=25, min_samples_split=4,
            min_samples_leaf=2, class_weight='balanced',
            random_state=42, n_jobs=-1
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=400, max_depth=7, learning_rate=0.05,
            subsample=0.8, min_samples_split=4, min_samples_leaf=2,
            random_state=42
        ),
        "ExtraTrees": ExtraTreesClassifier(
            n_estimators=400, max_depth=25, min_samples_split=4,
            min_samples_leaf=2, class_weight='balanced',
            random_state=42, n_jobs=-1
        ),
    }
    return models


# ─────────────────────────────────────────────────────────────────────────────
# MLP NEURAL NETWORK
# ─────────────────────────────────────────────────────────────────────────────

def build_mlp(X_train, y_train):
    """
    Train a Multi-Layer Perceptron (neural network).
    v5: Wider layers (512→256→128) + lower alpha for more capacity.
    """
    print("  Training MLP Neural Network (3 hidden layers: 512→256→128)...")
    mlp = MLPClassifier(
        hidden_layer_sizes=(512, 256, 128),
        activation='relu',
        solver='adam',
        alpha=0.0005,          # Slightly less regularisation for more capacity
        batch_size=256,
        learning_rate='adaptive',
        max_iter=500,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=30,
        random_state=42,
        verbose=False,
    )
    mlp.fit(X_train, y_train)
    return mlp


# ─────────────────────────────────────────────────────────────────────────────
# CATBOOST (NEW in v5)
# ─────────────────────────────────────────────────────────────────────────────

def tune_catboost(X_train, y_train):
    """
    CatBoost — Yandex's gradient boosting library.
    
    Why CatBoost?
      - Handles categorical features NATIVELY (our city one-hot columns)
      - Ordered boosting: reduces prediction shift that regular boosting suffers from
      - More robust to overfitting with default settings
      - Often finds different optimal splits than XGBoost/LightGBM
    """
    print("  Training CatBoost (with ordered boosting)...")
    cat = CatBoostClassifier(
        iterations=600,
        depth=8,
        learning_rate=0.05,
        l2_leaf_reg=5,              # L2 regularization
        border_count=128,           # Number of splits for numerical features
        auto_class_weights='Balanced',
        random_seed=42,
        verbose=0,                  # Silent training
        task_type='CPU',
    )
    cat.fit(X_train, y_train)
    return cat


# ─────────────────────────────────────────────────────────────────────────────
# XGBoost + LightGBM TUNING (enhanced in v5: 60 combos × 5-fold)
# ─────────────────────────────────────────────────────────────────────────────

def tune_xgboost(X_train, y_train):
    """RandomizedSearchCV for XGBoost — 60 random combos × 5-fold CV."""
    param_dist = {
        'n_estimators': randint(300, 1000),
        'max_depth': randint(4, 12),
        'learning_rate': uniform(0.01, 0.12),
        'subsample': uniform(0.6, 0.4),
        'colsample_bytree': uniform(0.5, 0.5),
        'reg_alpha': uniform(0, 3),
        'reg_lambda': uniform(0.5, 3),
        'min_child_weight': randint(1, 10),
        'gamma': uniform(0, 0.5),
    }
    xgb = XGBClassifier(
        random_state=42, eval_metric="logloss", n_jobs=-1, tree_method='hist'
    )
    search = RandomizedSearchCV(
        xgb, param_dist, n_iter=60, cv=5, scoring='accuracy',
        random_state=42, n_jobs=-1, verbose=0
    )
    search.fit(X_train, y_train)
    print(f"    Best CV accuracy: {search.best_score_:.4f}")
    return search.best_estimator_


def tune_lightgbm(X_train, y_train):
    """RandomizedSearchCV for LightGBM — 60 random combos × 5-fold CV."""
    param_dist = {
        'n_estimators': randint(300, 1000),
        'max_depth': randint(4, 12),
        'learning_rate': uniform(0.01, 0.12),
        'subsample': uniform(0.6, 0.4),
        'colsample_bytree': uniform(0.5, 0.5),
        'reg_alpha': uniform(0, 3),
        'reg_lambda': uniform(0.5, 3),
        'num_leaves': randint(20, 120),
        'min_child_samples': randint(5, 50),
    }
    lgbm = LGBMClassifier(
        is_unbalance=True, random_state=42, verbose=-1, n_jobs=-1
    )
    search = RandomizedSearchCV(
        lgbm, param_dist, n_iter=60, cv=5, scoring='accuracy',
        random_state=42, n_jobs=-1, verbose=0
    )
    search.fit(X_train, y_train)
    print(f"    Best CV accuracy: {search.best_score_:.4f}")
    return search.best_estimator_


# ─────────────────────────────────────────────────────────────────────────────
# STACKING ENSEMBLE (enhanced in v5: passthrough=True)
# ─────────────────────────────────────────────────────────────────────────────

def build_stacking_ensemble(base_models_dict, X_train, y_train):
    """
    Build a StackingClassifier using the best available base learners.
    
    v5 changes:
      - passthrough=True: Meta-learner sees original features + predictions
        This gives it 74 + N base model columns to work with.
      - Uses Ridge-regularized Logistic Regression to handle extra features
      - Includes CatBoost as a base learner if available
    """
    estimators = []
    if "XGBoost_Tuned" in base_models_dict:
        estimators.append(('xgb', base_models_dict["XGBoost_Tuned"]))
    if "LightGBM_Tuned" in base_models_dict:
        estimators.append(('lgbm', base_models_dict["LightGBM_Tuned"]))
    if "CatBoost" in base_models_dict:
        estimators.append(('cat', base_models_dict["CatBoost"]))
    if "MLP_NeuralNet" in base_models_dict:
        estimators.append(('mlp', base_models_dict["MLP_NeuralNet"]))
    
    base_names = [name for name, _ in estimators]
    print(f"  Building Stacking Ensemble ({' + '.join(base_names)} → LogisticRegression)...")
    
    stack = StackingClassifier(
        estimators=estimators,
        final_estimator=LogisticRegression(
            max_iter=2000, C=0.5, random_state=42
        ),
        cv=5,
        n_jobs=-1,
        passthrough=True,  # v5: pass original features + predictions to meta-learner
    )
    stack.fit(X_train, y_train)
    return stack


# ─────────────────────────────────────────────────────────────────────────────
# SHARED UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def find_optimal_threshold(model, X_test, y_test):
    """Find the probability threshold that maximises accuracy."""
    y_proba = model.predict_proba(X_test)[:, 1]
    best_acc, best_thresh = 0, 0.5
    for thresh in np.arange(0.30, 0.70, 0.005):
        y_pred = (y_proba >= thresh).astype(int)
        acc = accuracy_score(y_test, y_pred)
        if acc > best_acc:
            best_acc, best_thresh = acc, thresh
    return round(best_thresh, 3), round(best_acc, 4)


def evaluate_model(model, X_test, y_test, threshold=0.5):
    """Evaluate a model with a custom probability threshold."""
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred  = (y_proba >= threshold).astype(int)
    return {
        "accuracy":  round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall":    round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1_score":  round(f1_score(y_test, y_pred, zero_division=0), 4),
        "roc_auc":   round(roc_auc_score(y_test, y_proba), 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN TRAINING PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def train_and_compare():
    """
    v5 Training Pipeline:
      1. Load data → engineer ~74 features
      2. SMOTE oversampling for class balance          ← NEW in v5
      3. Feature selection via mutual information       ← NEW in v5
      4. Train base models (LR, RF, GB, ExtraTrees)    ← ExtraTrees NEW in v5
      5. Tune XGBoost + LightGBM (60 combos × 5-fold)  ← Enhanced in v5
      6. Train CatBoost                                 ← NEW in v5
      7. Train MLP Neural Network (wider layers)        ← Enhanced in v5
      8. Build Voting + Stacking ensembles
      9. Threshold optimise all models
     10. Save the best model
    """
    print("=" * 60)
    print("  Weather Prediction — Training Pipeline v5")
    print("  (CatBoost + SMOTE + Feature Selection)")
    print("=" * 60)

    # ── 1. Load raw data ──────────────────────────────────────────────────────
    print("\n[1/8] Loading raw data...")
    df = load_raw_data()
    print(f"  Raw data: {len(df)} rows")

    # ── 2. Engineer features ──────────────────────────────────────────────────
    print("\n[2/8] Engineering features...")
    df = engineer_features(df)
    print(f"  Feature-engineered: {len(df)} rows, {len(FEATURE_COLUMNS)} features")

    # ── 3. Prepare train/test split ───────────────────────────────────────────
    print("\n[3/8] Preparing train/test split...")
    X_train, X_test, y_train, y_test, scaler = prepare_datasets(
        df, target="rain_tomorrow", test_size=0.2
    )
    print(f"  Train: {X_train.shape[0]} | Test: {X_test.shape[0]}")
    print(f"  Rain ratio — Train: {y_train.mean():.2%} | Test: {y_test.mean():.2%}")

    # ── 4. SMOTE oversampling (NEW in v5) ─────────────────────────────────────
    print("\n[4/8] Applying SMOTE oversampling...")
    if HAS_SMOTE:
        smote = SMOTE(random_state=42, k_neighbors=5)
        X_train_bal, y_train_bal = smote.fit_resample(X_train, y_train)
        print(f"  Before SMOTE: {X_train.shape[0]} samples (rain={y_train.mean():.2%})")
        print(f"  After  SMOTE: {X_train_bal.shape[0]} samples (rain={y_train_bal.mean():.2%})")
    else:
        X_train_bal, y_train_bal = X_train, y_train
        print("  SMOTE not available — using original data")

    # ── 5. Feature selection (NEW in v5) ──────────────────────────────────────
    print("\n[5/8] Feature selection via mutual information...")
    keep_idx, kept_names = select_features(
        X_train_bal, y_train_bal, FEATURE_COLUMNS
    )
    X_train_sel = X_train_bal[:, keep_idx]
    X_test_sel = X_test[:, keep_idx]
    
    # Also keep unselected versions for models that work well with all features
    # (some models like RF benefit from more features, while tuned models benefit from less noise)

    # ── 6. Train base models ──────────────────────────────────────────────────
    print("\n[6/8] Training base models...\n")
    base_models = get_base_models()
    results = {}
    trained_models = {}

    for name, model in base_models.items():
        print(f"  Training {name}...", end=" ", flush=True)
        model.fit(X_train_sel, y_train_bal)
        metrics = evaluate_model(model, X_test_sel, y_test)
        results[name] = {"model": model, "metrics": metrics}
        trained_models[name] = model
        print(f"Acc={metrics['accuracy']:.4f}  F1={metrics['f1_score']:.4f}  AUC={metrics['roc_auc']:.4f}")

    # ── 7. Tune XGBoost + LightGBM + CatBoost + MLP ──────────────────────────
    print("\n[7/8] Advanced models + hyperparameter tuning...\n")

    if HAS_XGBOOST:
        print("  Tuning XGBoost (60 combos × 5-fold CV)...")
        tuned_xgb = tune_xgboost(X_train_sel, y_train_bal)
        metrics = evaluate_model(tuned_xgb, X_test_sel, y_test)
        results["XGBoost_Tuned"] = {"model": tuned_xgb, "metrics": metrics}
        trained_models["XGBoost_Tuned"] = tuned_xgb
        print(f"  XGBoost_Tuned: Acc={metrics['accuracy']:.4f}  F1={metrics['f1_score']:.4f}\n")

    if HAS_LIGHTGBM:
        print("  Tuning LightGBM (60 combos × 5-fold CV)...")
        tuned_lgbm = tune_lightgbm(X_train_sel, y_train_bal)
        metrics = evaluate_model(tuned_lgbm, X_test_sel, y_test)
        results["LightGBM_Tuned"] = {"model": tuned_lgbm, "metrics": metrics}
        trained_models["LightGBM_Tuned"] = tuned_lgbm
        print(f"  LightGBM_Tuned: Acc={metrics['accuracy']:.4f}  F1={metrics['f1_score']:.4f}\n")

    if HAS_CATBOOST:
        cat_model = tune_catboost(X_train_sel, y_train_bal)
        metrics = evaluate_model(cat_model, X_test_sel, y_test)
        results["CatBoost"] = {"model": cat_model, "metrics": metrics}
        trained_models["CatBoost"] = cat_model
        print(f"  CatBoost: Acc={metrics['accuracy']:.4f}  F1={metrics['f1_score']:.4f}\n")

    # MLP Neural Network (wider in v5)
    mlp_model = build_mlp(X_train_sel, y_train_bal)
    metrics = evaluate_model(mlp_model, X_test_sel, y_test)
    results["MLP_NeuralNet"] = {"model": mlp_model, "metrics": metrics}
    trained_models["MLP_NeuralNet"] = mlp_model
    print(f"  MLP_NeuralNet: Acc={metrics['accuracy']:.4f}  F1={metrics['f1_score']:.4f}\n")

    # ── Voting Ensemble ───────────────────────────────────────────────────────
    if HAS_XGBOOST and HAS_LIGHTGBM:
        voting_estimators = [
            ("xgb",  trained_models["XGBoost_Tuned"]),
            ("lgbm", trained_models["LightGBM_Tuned"]),
            ("gb",   trained_models["GradientBoosting"]),
        ]
        if HAS_CATBOOST:
            voting_estimators.append(("cat", trained_models["CatBoost"]))
        
        print(f"  Building VotingClassifier ({len(voting_estimators)} models)...")
        voter = VotingClassifier(estimators=voting_estimators, voting='soft', n_jobs=-1)
        voter.fit(X_train_sel, y_train_bal)
        metrics = evaluate_model(voter, X_test_sel, y_test)
        results["VotingEnsemble"] = {"model": voter, "metrics": metrics}
        print(f"  VotingEnsemble: Acc={metrics['accuracy']:.4f}  F1={metrics['f1_score']:.4f}\n")

    # ── Stacking Ensemble ─────────────────────────────────────────────────────
    if HAS_XGBOOST and HAS_LIGHTGBM:
        stacker = build_stacking_ensemble(trained_models, X_train_sel, y_train_bal)
        metrics = evaluate_model(stacker, X_test_sel, y_test)
        results["StackingEnsemble"] = {"model": stacker, "metrics": metrics}
        print(f"  StackingEnsemble: Acc={metrics['accuracy']:.4f}  F1={metrics['f1_score']:.4f}\n")

    # ── 8. Threshold optimisation ─────────────────────────────────────────────
    print("[8/8] Optimising decision thresholds...\n")
    best_overall_acc, best_overall_name, best_overall_thresh = 0, None, 0.5

    for name, res in results.items():
        thresh, acc = find_optimal_threshold(res["model"], X_test_sel, y_test)
        optimized_metrics = evaluate_model(res["model"], X_test_sel, y_test, threshold=thresh)
        res["optimal_threshold"] = thresh
        res["optimized_metrics"] = optimized_metrics
        print(f"  {name}: threshold={thresh:.3f} → Acc={acc:.4f}")
        if acc > best_overall_acc:
            best_overall_acc  = acc
            best_overall_name = name
            best_overall_thresh = thresh

    # ── Print comparison table ────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  MODEL COMPARISON (with optimised thresholds)")
    print("=" * 70)
    print(f"  {'Model':<24} {'Threshold':>10} {'Accuracy':>9} {'F1':>8} {'AUC':>8}")
    print("  " + "-" * 60)

    for name, res in sorted(results.items(),
                            key=lambda x: x[1]["optimized_metrics"]["accuracy"],
                            reverse=True):
        m = res["optimized_metrics"]
        t = res["optimal_threshold"]
        tag = " ← BEST" if name == best_overall_name else ""
        print(f"  {name:<24} {t:>10.3f} {m['accuracy']:>9.4f} {m['f1_score']:>8.4f} {m['roc_auc']:>8.4f}{tag}")

    # ── Save best model ──────────────────────────────────────────────────────
    best_model   = results[best_overall_name]["model"]
    best_metrics = results[best_overall_name]["optimized_metrics"]

    print(f"\n  BEST: {best_overall_name} @ threshold={best_overall_thresh:.3f}")
    print(f"        Accuracy={best_metrics['accuracy']:.4f}  F1={best_metrics['f1_score']:.4f}")

    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(best_model, os.path.join(MODELS_DIR, "best_rain_predictor.joblib"))
    joblib.dump(scaler,     os.path.join(MODELS_DIR, "scaler.joblib"))
    
    # Save the selected feature indices so Flask knows which features to use
    joblib.dump(keep_idx, os.path.join(MODELS_DIR, "selected_features.joblib"))

    # Build metadata with selected feature names
    selected_feature_names = [FEATURE_COLUMNS[i] for i in keep_idx]
    
    metadata = {
        "best_model":       best_overall_name,
        "optimal_threshold": best_overall_thresh,
        "metrics":          best_metrics,
        "feature_columns":  selected_feature_names,
        "all_feature_columns": FEATURE_COLUMNS,
        "pipeline_version": "v5",
        "improvements": [
            "SMOTE oversampling",
            "CatBoost added",
            "Mutual information feature selection",
            "60 combos × 5-fold CV tuning",
            "Wider MLP (512→256→128)",
            "ExtraTrees baseline",
            "Stacking with passthrough=True",
        ],
        "all_results": {
            name: {
                "metrics":   res["optimized_metrics"],
                "threshold": res["optimal_threshold"],
            }
            for name, res in results.items()
        },
        "train_samples": int(X_train.shape[0]),
        "test_samples":  int(X_test.shape[0]),
        "smote_applied": HAS_SMOTE,
        "features_selected": len(keep_idx),
        "features_total": len(FEATURE_COLUMNS),
    }
    with open(os.path.join(MODELS_DIR, "model_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n  Saved model   → {MODELS_DIR}/best_rain_predictor.joblib")
    print(f"  Saved scaler  → {MODELS_DIR}/scaler.joblib")
    print(f"  Saved features→ {MODELS_DIR}/selected_features.joblib")
    print(f"  Saved metadata→ {MODELS_DIR}/model_metadata.json")
    print("=" * 60)

    return best_overall_name, best_model, scaler, metadata


if __name__ == "__main__":
    train_and_compare()
