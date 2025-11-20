@echo off
REM Quick Test Runner Script
REM Run this before pushing to catch test failures locally

echo ========================================
echo Running Backend Tests Locally
echo ========================================

cd app\backend

echo.
echo Installing dependencies...
pip install -q -r requirements.txt
pip install -q pytest

echo.
echo Running tests...
python -m pytest tests/api/test_settings.py -v

echo.
echo ========================================
echo Test run complete!
echo ========================================
pause
