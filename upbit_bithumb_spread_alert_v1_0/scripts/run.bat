@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d %~dp0\..

echo [Spread Alert v1.0] Starting run.bat
if not exist .venv (
  echo Creating virtual environment...
  py -3 -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

python -m src.main

echo.
echo Process ended. Press any key to close.
pause >nul
