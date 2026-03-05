@echo off
title Uninstall Dependencies - AI Video Enhancer
echo ========================================
echo    Remove Project Dependencies
echo ========================================
echo.

echo This will remove:
echo   - Python packages installed for this project (global Python env)
echo   - pip cache
echo   - client\node_modules and package lock
echo   - cloudflared.exe (if downloaded by share.bat)
echo.
choice /c YN /n /m "Continue? [Y/N]: "
if %ERRORLEVEL% neq 1 (
    echo Cancelled.
    exit /b 0
)

echo.
echo [1/5] Uninstalling Python dependencies...
python -m pip uninstall -y ^
  fastapi uvicorn python-multipart pydantic pydantic-settings aiofiles starlette python-dotenv ^
  opencv-python-headless pillow tqdm requests psutil ^
  torch torchvision torchaudio basicsr realesrgan facexlib gfpgan

echo.
echo [2/5] Removing pip cache...
python -m pip cache purge

echo.
echo [3/5] Removing frontend dependencies...
if exist "%~dp0client\node_modules" rmdir /s /q "%~dp0client\node_modules"
if exist "%~dp0client\package-lock.json" del /q "%~dp0client\package-lock.json"

echo.
echo [4/5] Removing downloaded tunnel binary...
if exist "%~dp0cloudflared.exe" del /q "%~dp0cloudflared.exe"

echo.
echo [5/5] Optional cleanup of temp outputs...
choice /c YN /n /m "Delete temp uploads/outputs/processing files too? [Y/N]: "
if %ERRORLEVEL%==1 (
    if exist "%~dp0temp\uploads" rmdir /s /q "%~dp0temp\uploads"
    if exist "%~dp0temp\outputs" rmdir /s /q "%~dp0temp\outputs"
    if exist "%~dp0temp\processing" rmdir /s /q "%~dp0temp\processing"
    mkdir "%~dp0temp\uploads" 2>nul
    mkdir "%~dp0temp\outputs" 2>nul
    mkdir "%~dp0temp\processing" 2>nul
)

echo.
echo ========================================
echo    Dependency Cleanup Complete
echo ========================================
echo.
echo If you need the app again, run install.bat.
pause
