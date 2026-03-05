@echo off
title Install Dependencies - AI Video Enhancer
echo ========================================
echo    AI Video Enhancer - Dependency Installer
echo ========================================
echo.

:: Check Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed!
    echo Download from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: Check Node.js
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not installed!
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)

:: Check FFmpeg
where ffmpeg >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [WARNING] FFmpeg not found in PATH. Attempting automatic install...

    where winget >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        echo [INFO] Installing FFmpeg via winget...
        winget install --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements --silent
    ) else (
        where choco >nul 2>nul
        if %ERRORLEVEL% equ 0 (
            echo [INFO] Installing FFmpeg via Chocolatey...
            choco install ffmpeg -y
        ) else (
            echo [WARNING] winget/choco not found for auto-install.
        )
    )

    where ffmpeg >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [WARNING] FFmpeg still not found. Upload will work, but full processing may fail.
        echo          Install manually from: https://ffmpeg.org/download.html
    ) else (
        echo [INFO] FFmpeg installed successfully.
    )
    echo.
)

echo [INFO] Python and Node.js found. Starting installation...
echo.

:: Upgrade pip
echo [1/7] Upgrading pip...
python -m pip install --upgrade pip --quiet
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Failed to upgrade pip, continuing...
)

:: Install FastAPI and server dependencies
echo [2/7] Installing FastAPI and server packages...
pip install fastapi==0.109.0 uvicorn[standard]==0.27.0 python-multipart==0.0.6 --quiet
pip install pydantic==2.5.3 pydantic-settings==2.1.0 aiofiles==23.2.1 --quiet
pip install starlette==0.35.1 python-dotenv==1.0.0 --quiet

:: Install image/video processing
echo [3/7] Installing image and video processing packages...
pip install opencv-python-headless==4.9.0.80 numpy==1.26.3 pillow==10.2.0 --quiet

:: Install utilities
echo [4/7] Installing utility packages...
pip install tqdm==4.66.1 requests==2.31.0 psutil==5.9.8 --quiet

:: Install PyTorch (largest package)
echo [5/7] Installing PyTorch (this may take 5-10 minutes)...
echo      Downloading ~2GB - please be patient...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
if %ERRORLEVEL% neq 0 (
    echo [WARNING] CUDA version failed, trying CPU version...
    pip install torch torchvision
)

:: Install AI model packages
echo [6/7] Installing AI model packages...
pip install "basicsr>=1.4.2" --quiet
pip install "realesrgan>=0.3.0" --quiet
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Some AI packages may have failed. App will work with limited features.
)

:: Install Node.js dependencies
echo [7/7] Installing Node.js dependencies...
cd client
call npm install
cd ..

:: Create required directories
echo.
echo [INFO] Creating directories...
if not exist "temp\uploads" mkdir "temp\uploads"
if not exist "temp\outputs" mkdir "temp\outputs"
if not exist "temp\processing" mkdir "temp\processing"
if not exist "temp\processing\chunks" mkdir "temp\processing\chunks"
if not exist "models" mkdir "models"

echo.
echo ========================================
echo    Installation Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Run start.bat to launch the application
echo   2. Open http://localhost:3000 in your browser
echo.
pause
