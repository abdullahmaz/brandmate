@echo off
echo ================================================================
echo             DAILY CAPTION PROCESSING
echo ================================================================
echo.

REM Change to the fine_tuning directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

REM Check if required packages are installed
echo Checking dependencies...
python -c "import google.generativeai, PIL, tqdm" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Required packages not installed!
    echo.
    echo Installing packages...
    pip install google-generativeai Pillow tqdm
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install packages
        pause
        exit /b 1
    )
)

echo [OK] Dependencies checked
echo.

REM Run the daily processing script
echo Starting daily caption processing...
python run_daily_captioning.py

REM Pause to see results
echo.
echo Processing complete. Press any key to exit...
pause >nul