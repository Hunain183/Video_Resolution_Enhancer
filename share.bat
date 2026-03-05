@echo off
title AI Video Enhancer - Share Public URL
echo ========================================
echo    AI Video Enhancer - Internet Sharing
echo ========================================
echo.

:: Check Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

:: Check Node.js
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH
    pause
    exit /b 1
)

:: Ensure dependencies are available
python -c "import fastapi, uvicorn, aiofiles" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Missing backend dependencies. Running installer...
    call "%~dp0install.bat"
)

if not exist "client\node_modules" (
    echo [INFO] Missing frontend dependencies. Installing npm packages...
    cd /d "%~dp0client"
    call npm install
    cd /d "%~dp0"
)

:: Start backend
echo [INFO] Starting backend on http://localhost:8000
start "Backend Server" cmd /k "cd /d %~dp0server && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

:: Wait backend health
echo [INFO] Waiting for backend health...
set /a retries=0
:wait_backend
curl -s http://localhost:8000/health >nul 2>nul
if %ERRORLEVEL% neq 0 (
    set /a retries+=1
    if %retries% geq 25 (
        echo [ERROR] Backend did not start. Check Backend Server window.
        pause
        exit /b 1
    )
    timeout /t 1 /nobreak >nul
    goto wait_backend
)

:: Start frontend (host exposed for LAN too)
echo [INFO] Starting frontend on http://localhost:3000
start "Frontend Server" cmd /k "cd /d %~dp0client && npm run dev -- --host 0.0.0.0 --port 3000"
timeout /t 5 /nobreak >nul

:: Download cloudflared if not present
if not exist "%~dp0cloudflared.exe" (
    echo [INFO] Downloading cloudflared tunnel client...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%~dp0cloudflared.exe'"
)

if not exist "%~dp0cloudflared.exe" (
    echo [ERROR] Failed to download cloudflared.exe
    echo Download manually from:
    echo https://github.com/cloudflare/cloudflared/releases
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Starting Public Tunnel...
echo ========================================
echo.
echo [INFO] A new window will open with a public URL like:
echo        https://something.trycloudflare.com
echo [INFO] Share that URL with any device. No install needed there.
echo.

start "Public Tunnel" cmd /k "cd /d %~dp0 && cloudflared.exe tunnel --url http://localhost:3000"

echo [INFO] Local app:  http://localhost:3000
echo [INFO] API docs:   http://localhost:8000/docs
echo [INFO] To stop everything, run stop.bat
echo.
pause
