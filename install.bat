@echo off
title Install Dependencies - AI Video Enhancer
echo ========================================
echo    AI Video Enhancer - Dependency Installer
echo ========================================
echo.

setlocal EnableExtensions
cd /d "%~dp0"

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

:: Auto-detect GPU support and choose PyTorch wheel index
set "TORCH_INDEX=https://download.pytorch.org/whl/cpu"
set "TORCH_MODE=CPU"
where nvidia-smi >nul 2>nul
if %ERRORLEVEL% equ 0 (
    nvidia-smi >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set "TORCH_INDEX=https://download.pytorch.org/whl/cu118"
        set "TORCH_MODE=CUDA"
    )
)
echo [INFO] Selected mode: %TORCH_MODE%
echo.

:: Upgrade pip tooling
echo [1/6] Upgrading pip tooling...
python -m pip install --upgrade pip setuptools wheel --quiet
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Failed to upgrade pip tooling, continuing...
)

:: Install backend dependencies from requirements file
echo [2/6] Installing backend dependencies from server\requirements.txt...
python -m pip install -r server\requirements.txt --no-cache-dir
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install Python dependencies from server\requirements.txt
    pause
    exit /b 1
)

:: Install PyTorch wheels (CUDA or CPU)
echo [3/6] Installing PyTorch %TORCH_MODE% wheels (this may take a few minutes)...
python -m pip install --upgrade --force-reinstall torch==2.1.2 torchvision==0.16.2 --index-url %TORCH_INDEX%
if %ERRORLEVEL% neq 0 (
    if /I "%TORCH_MODE%"=="CUDA" (
        echo [WARNING] CUDA wheel install failed. Falling back to CPU wheels...
        set "TORCH_INDEX=https://download.pytorch.org/whl/cpu"
        set "TORCH_MODE=CPU"
        python -m pip install --upgrade --force-reinstall torch==2.1.2 torchvision==0.16.2 --index-url %TORCH_INDEX%
    )
)
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install PyTorch %TORCH_MODE% wheels.
    pause
    exit /b 1
)

:: Ensure NumPy stays compatible with Torch/BasicSR
echo [4/6] Enforcing NumPy compatibility (numpy^<2)...
python -m pip install "numpy<2" --force-reinstall --no-cache-dir

:: Install AI model packages
echo [5/6] Installing AI model packages...
python -m pip install --force-reinstall torchvision==0.16.2 --no-cache-dir
python -m pip install "numpy<2" --force-reinstall --no-cache-dir
python -m pip install "basicsr==1.4.2" "realesrgan==0.3.0" --no-cache-dir
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Initial Real-ESRGAN install failed. Retrying with source install...
    python -m pip install git+https://github.com/xinntao/Real-ESRGAN.git --no-cache-dir
)

:: Verify Real-ESRGAN imports work
python -c "from basicsr.archs.rrdbnet_arch import RRDBNet; from realesrgan import RealESRGANer; print('Real-ESRGAN import OK')" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Real-ESRGAN packages are still not importable in this Python environment.
    echo [ERROR] Run this manually and share output:
    echo        python -c "from basicsr.archs.rrdbnet_arch import RRDBNet; from realesrgan import RealESRGANer"
    pause
    exit /b 1
)
echo [INFO] Real-ESRGAN dependencies installed successfully.

:: Install Node.js dependencies
echo [6/6] Installing Node.js dependencies...
cd /d "%~dp0client"
call npm install
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install Node.js dependencies.
    cd /d "%~dp0"
    pause
    exit /b 1
)
cd /d "%~dp0"

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
