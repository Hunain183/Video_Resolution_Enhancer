@echo off
title AI Video Resolution Enhancer
echo ========================================
echo    AI Video Resolution Enhancer
echo ========================================
echo.

:: Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.10+ and add it to your PATH
    pause
    exit /b 1
)

:: Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH
    echo Please install Node.js 18+ and add it to your PATH
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist "server\venv" (
    echo [INFO] Creating Python virtual environment...
    cd server
    python -m venv venv
    cd ..
)

:: Activate virtual environment and install dependencies
echo [INFO] Installing Python dependencies...
cd server
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
cd ..

:: Install Node.js dependencies
echo [INFO] Installing Node.js dependencies...
cd client
call npm install --silent
cd ..

:: Create required directories
if not exist "temp\uploads" mkdir "temp\uploads"
if not exist "temp\outputs" mkdir "temp\outputs"
if not exist "temp\processing" mkdir "temp\processing"
if not exist "models" mkdir "models"

echo.
echo ========================================
echo    Starting Services...
echo ========================================
echo.

:: Start backend server in a new window
echo [INFO] Starting backend server on http://localhost:8000
start "Backend Server" cmd /k "cd server && call venv\Scripts\activate.bat && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait a moment for backend to start
timeout /t 3 /nobreak >nul

:: Start frontend dev server in a new window
echo [INFO] Starting frontend server on http://localhost:5173
start "Frontend Server" cmd /k "cd client && npm run dev"

:: Wait a moment for frontend to start
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo    Services Started!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to open the app in your browser...
pause >nul

:: Open browser
start http://localhost:5173

echo.
echo To stop the services, close the Backend and Frontend terminal windows.
echo.
pause
