@echo off
cd /d "%~dp0"

echo ========================================
echo    CVM colorBot Launcher
echo ========================================
echo.

:: Check if venv exists
if not exist "venv" (
    echo [ERROR] Virtual environment not found!
    echo Please run setup.bat first
    echo.
    pause
    exit /b 1
)

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

:: Start CVM colorBot using venv Python
echo [*] Starting CVM colorBot...
echo.

:: Use venv Python directly
venv\Scripts\python.exe main.py

:: Pause if error occurred
if errorlevel 1 (
    echo.
    echo [ERROR] Program exited with error
    pause
)

