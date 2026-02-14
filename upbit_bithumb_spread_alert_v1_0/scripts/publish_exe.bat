@echo off
setlocal
cd /d %~dp0\..

echo [Spread Alert v1.0] publish_exe.bat
if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

pyinstaller --noconfirm --clean --onefile --name "SpreadAlert_v1.0" --add-data "config;config" src/main.py

echo EXE created: dist\SpreadAlert_v1.0.exe
pause
