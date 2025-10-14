@echo off
REM Gemini Caption Generator - Easy Runner
REM API keys are loaded from run_captioning_config.py
REM Edit that file to add/change your API keys

echo ============================================================
echo GEMINI FASHION CAPTIONING - 5 API KEYS LOADED
echo ============================================================
echo.

REM Choose category: Summer_Men, Summer_Women, Winter_Men, Winter_Women, or all
set CATEGORY=Summer_Men

REM Test mode: Remove REM below to test with only 10 images first
REM set TEST_MODE=--test 10

echo Category: %CATEGORY%
echo Config: run_captioning_config.py
echo.
echo Starting captioning with automatic key rotation...
echo Keys will rotate when quota is reached
echo.

py -3 gemini_caption_multi_key.py --category %CATEGORY% %TEST_MODE%

echo.
echo ============================================================
echo Captioning Complete!
echo ============================================================
echo.
echo Check your data folder for .txt caption files
pause
