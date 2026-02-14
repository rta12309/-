@echo off
cd /d %~dp0

echo [1/4] Python 확인...
python --version >nul 2>nul
if errorlevel 1 (
  echo Python이 설치되어 있지 않습니다.
  echo https://www.python.org/downloads/ 에서 Python 3.10+ 설치 후 다시 실행하세요.
  pause
  exit /b 1
)

echo [2/4] 가상환경 준비...
if not exist .venv (
  python -m venv .venv
)

echo [3/4] 패키지 설치...
call .venv\Scripts\python -m pip install --upgrade pip
call .venv\Scripts\python -m pip install -r requirements.txt

echo [4/4] 웹 실행...
start http://127.0.0.1:5000
call .venv\Scripts\python app.py
pause
