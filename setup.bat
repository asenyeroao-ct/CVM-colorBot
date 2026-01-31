@echo off
cd /d "%~dp0"

echo ========================================
echo    CVM colorBot Setup Script
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please download and install from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [*] Checking Python version...
python --version

:: Create virtual environment
if exist "venv" (
    echo [*] Virtual environment already exists, skipping creation
) else (
    echo [*] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully
)

:: Activate virtual environment
echo [*] Activating virtual environment...
call venv\Scripts\activate
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)

:: Upgrade pip
echo [*] Upgrading pip...
python -m pip install --upgrade pip --quiet

:: Install dependencies
if exist requirements.txt (
    echo [*] Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed successfully
) else (
    echo [WARNING] requirements.txt not found
)

echo.
echo ========================================
echo    Setup Complete!
echo ========================================
echo.
echo You can now run run.bat to start the program
echo.
pause

