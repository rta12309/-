@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d %~dp0\..

echo [Spread Alert v1.0] publish_exe.bat

set "PY_LAUNCHER="
set "PYTHON_EXE=.venv\Scripts\python.exe"

if not exist .venv\Scripts\python.exe (
  echo [INFO] .venv not found. Creating virtual environment...

  py -3.12 -m venv .venv >nul 2>&1
  if %errorlevel%==0 (
    set "PY_LAUNCHER=py -3.12"
    goto :venv_created
  )

  py -3.11 -m venv .venv >nul 2>&1
  if %errorlevel%==0 (
    set "PY_LAUNCHER=py -3.11"
    goto :venv_created
  )

  python -m venv .venv >nul 2>&1
  if %errorlevel%==0 (
    set "PY_LAUNCHER=python"
    goto :venv_created
  )

  echo [ERROR] Failed to create .venv. Install Python 3.11 or 3.12 and retry.
  exit /b 1
)

:venv_created
if not exist "%PYTHON_EXE%" (
  echo [ERROR] Virtual environment python not found: %PYTHON_EXE%
  exit /b 1
)

echo [INFO] Using venv python: %PYTHON_EXE%
"%PYTHON_EXE%" -V
if errorlevel 1 (
  echo [ERROR] Cannot run venv python.
  exit /b 1
)

echo [STEP] Upgrade pip
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 (
  echo [ERROR] pip upgrade failed.
  exit /b 1
)

echo [STEP] Install requirements
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] requirements install failed.
  exit /b 1
)

echo [STEP] Ensure PyInstaller is installed
"%PYTHON_EXE%" -m pip install pyinstaller
if errorlevel 1 (
  echo [ERROR] PyInstaller install failed.
  exit /b 1
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [STEP] Build onefile EXE
"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean --onefile --name "SpreadAlert_v1.0" --add-data "config;config" src/main.py
if errorlevel 1 (
  echo [ERROR] PyInstaller build failed.
  exit /b 1
)

if not exist "dist\SpreadAlert_v1.0.exe" (
  echo [ERROR] Build finished but output file not found: dist\SpreadAlert_v1.0.exe
  exit /b 1
)

echo [SUCCESS] EXE created: dist\SpreadAlert_v1.0.exe
pause
exit /b 0
