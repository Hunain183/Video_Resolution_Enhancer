@echo off
title AI Video Enhancer - Quick Start
echo Starting AI Video Resolution Enhancer...
echo.

:: Start backend server in a new window
start "Backend Server" cmd /k "cd /d %~dp0server && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

:: Wait for backend
echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

:: Start frontend server in a new window
start "Frontend Server" cmd /k "cd /d %~dp0client && npm run dev"

:: Wait for frontend
timeout /t 5 /nobreak >nul

:: Open browser
start http://localhost:3000

echo.
echo Services started!
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Close the terminal windows to stop the services.
pause
