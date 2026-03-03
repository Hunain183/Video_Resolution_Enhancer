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

:: Upgrade pip first
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip --quiet

:: Install Python dependencies globally with extended timeout
echo [INFO] Installing Python dependencies (this may take a while)...
cd server
pip install -r requirements.txt --timeout 120 --retries 5
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Some packages failed to install. Retrying...
    pip install -r requirements.txt --timeout 180 --retries 3
)
cd ..

:: Install Node.js dependencies
echo [INFO] Installing Node.js dependencies...
cd client
call npm install
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
start "Backend Server" cmd /k "cd /d %~dp0server && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait for backend to start
echo [INFO] Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

:: Start frontend dev server in a new window
echo [INFO] Starting frontend server on http://localhost:3000
start "Frontend Server" cmd /k "cd /d %~dp0client && npm run dev"

:: Wait for frontend to start
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo    Services Started!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to open the app in your browser...
pause >nul

:: Open browser
start http://localhost:3000

echo.
echo To stop the services, close the Backend and Frontend terminal windows.
echo.
pause
