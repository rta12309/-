@echo off
setlocal
cd /d %~dp0\..

echo [Spread Alert v1.0] build_release.bat
if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

python -m compileall src

echo Build checks completed.
pause
