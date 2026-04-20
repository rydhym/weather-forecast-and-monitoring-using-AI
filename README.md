# WeatherAI — Real-time Weather Forecasting & Monitoring System 🌦️🤖

An intelligent, full-stack weather monitoring platform that leverages Machine Learning to predict rainfall probabilities, detect severe weather patterns, and provide smart alerts. Features a beautiful, emotion-based UI that dynamically adapts to weather conditions!

## 🚀 Key Features

*   **Real-time Weather Monitoring:** Live weather data (temperature, humidity, wind, pressure) fetched seamlessly from a reliable weather API.
*   **AI Rainfall Prediction (CatBoost):** An advanced ML pipeline trained on historical datasets to accurately predict the chance of rain.
*   **Weather Pattern Detection:** Analyzes incoming metrics (like rapid pressure drops or high winds) to detect early warning signs of extreme conditions.
*   **Emotion-Based Dynamic UI:** The React frontend automatically shifts themes, color palettes, and animations depending on the live weather conditions (Sunny, Rainy, Stormy, etc.).
*   **Smart Alerts:** Active alert dashboard notifying users of impending extreme weather, high UV index, or precipitation warnings.

## 🛠️ Technology Stack

*   **Frontend:** React, Vite, Recharts (for Analytics), Vanilla CSS
*   **Backend:** Node.js, Express.js
*   **AI Engine:** Python, Flask, CatBoost, Scikit-learn
*   **Database:** MongoDB
*   **External Data:** WeatherAPI.com

## ⚙️ How to Run the Project Locally

We have provided a convenient `start.bat` script that automatically launches all three required servers in one go!

### Prerequisites
1. Node.js installed
2. Python installed
3. MongoDB running locally or a cloud URI
4. A `.env` file in the root folder configured with your `WEATHER_API_KEY` and `MONGODB_URI`.

### Steps to Start

1. **Install Node Dependencies:**
   Make sure you have installed the necessary packages for both the backend and frontend:
   ```bash
   cd weather-ai-system\backend
   npm install
   cd ..\frontend
   npm install
   cd ..\..
   ```

2. **Run the Start Script:**
   Double-click the `start.bat` file in the root folder, OR run it via your terminal:
   ```cmd
   .\start.bat
   ```

3. **Access the Application:**
   The start script will automatically open three separate terminal windows:
   *   **Flask AI Engine** starts on port `5001`.
   *   **Express Backend** starts on port `5000`.
   *   **React Frontend** starts on port `5173`.
   
   Open your web browser and navigate to [http://localhost:5173](http://localhost:5173) to view the dashboard!

---
## 👨‍💻 Project Team
*   **Rydhym Agarwal** (Developer)
*   **Shreya** (Developer)
*   **Kreesh Singh Negi** (Developer)

*Developed as part of our Software Engineering Project.*
