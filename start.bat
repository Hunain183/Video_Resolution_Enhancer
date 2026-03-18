@echo off
title AI Video Enhancer - Quick Start
echo Starting AI Video Resolution Enhancer...
echo.

:: If NVIDIA GPU is present but CUDA is not available in torch, fix dependencies first
where nvidia-smi >nul 2>nul
if %ERRORLEVEL% equ 0 (
	python -c "import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)" >nul 2>nul
	if %ERRORLEVEL% neq 0 (
		echo [INFO] NVIDIA GPU detected but PyTorch CUDA is not available.
		echo [INFO] Running install.bat to install CUDA-enabled dependencies...
		call "%~dp0install.bat"
		if %ERRORLEVEL% neq 0 (
			echo [ERROR] Dependency installation failed.
			pause
			exit /b 1
		)
	)
)

:: Start backend server in a new window
start "Backend Server" cmd /k "cd /d %~dp0server && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

:: Wait for backend health check
echo Waiting for backend to start...
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
