@echo off
echo ================================================
echo   WeatherAI — Starting All Servers
echo ================================================
echo.

REM ── Step 1: Activate Python venv and start Flask AI Engine
echo [1/3] Starting Flask AI Engine (port 5001)...
start "Flask AI Engine" cmd /k "cd /d "%~dp0" && .venv\Scripts\activate && python ai-engine/api/app.py"

REM ── Wait 3 seconds for Flask to initialise before starting Node
timeout /t 3 /nobreak >nul

REM ── Step 2: Start Express backend (port 5000)
echo [2/3] Starting Express Backend (port 5000)...
start "Express Backend" cmd /k "cd /d "%~dp0weather-ai-system\backend" && node server.js"

REM ── Wait 2 seconds for Express to initialise
timeout /t 2 /nobreak >nul

REM ── Step 3: Start React Vite frontend (port 5173)
echo [3/3] Starting React Frontend (port 5173)...
start "React Frontend" cmd /k "cd /d "%~dp0weather-ai-system\frontend" && npm run dev"

echo.
echo ================================================
echo   All servers starting in separate windows!
echo   Flask  → http://localhost:5001/health
echo   Express → http://localhost:5000/api/weather?city=London
echo   React  → http://localhost:5173
echo ================================================
pause
