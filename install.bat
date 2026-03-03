@echo off
title Install Dependencies
echo ========================================
echo    Installing Dependencies
echo ========================================
echo.

:: Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [INFO] Installing PyTorch (this may take several minutes)...
echo [NOTE] If this fails, try running with better internet or install manually:
echo        pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
echo.
pip install torch torchvision --timeout 300

echo.
echo [INFO] Installing other Python dependencies...
cd server
pip install -r requirements.txt --timeout 180 --retries 5
cd ..

echo.
echo [INFO] Installing Node.js dependencies...
cd client
call npm install
cd ..

echo.
echo ========================================
echo    Installation Complete!
echo ========================================
echo.
echo Now run start.bat to launch the application.
echo.
pause
