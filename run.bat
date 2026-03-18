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

:: Check if dependencies are installed
python -c "import fastapi, uvicorn, aiofiles" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Dependencies not found. Running installer...
    echo.
    call "%~dp0install.bat"
)

:: Validate CUDA availability when NVIDIA GPU is present
where nvidia-smi >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python -c "import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)" >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [INFO] NVIDIA GPU detected but current PyTorch build cannot use CUDA.
        echo [INFO] Running installer to switch to CUDA-enabled PyTorch...
        call "%~dp0install.bat"
        if %ERRORLEVEL% neq 0 (
            echo [ERROR] Failed to repair CUDA dependencies.
            pause
            exit /b 1
        )
    )
)

:: Check if node_modules exists
if not exist "client\node_modules" (
    echo [INFO] Node modules not found. Installing...
    cd client
    call npm install
    cd ..
)

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
start "Backend Server" cmd /k "cd /d %~dp0server && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

:: Wait for backend to become healthy
echo [INFO] Waiting for backend health check...
set /a retries=0
:wait_backend
curl -s http://localhost:8000/health >nul 2>nul
if %ERRORLEVEL% neq 0 (
    set /a retries+=1
    if %retries% geq 20 (
        echo [ERROR] Backend failed to start or is not reachable at http://localhost:8000/health
        echo Check the "Backend Server" window for the exact Python error.
        pause
        exit /b 1
    )
    timeout /t 1 /nobreak >nul
    goto wait_backend
)

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
