@echo off
cd /d "%~dp0"
echo Starting AICTE Validation Assistant...
py app.py
if errorlevel 1 (
  echo.
  echo Could not start with the Python launcher. Try: python app.py
  pause
)
