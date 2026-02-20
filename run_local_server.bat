@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if not errorlevel 1 goto run_py

where python >nul 2>nul
if not errorlevel 1 goto run_python

where python3 >nul 2>nul
if not errorlevel 1 goto run_python3

echo Python이 설치되어 있지 않습니다. Python 설치 후 다시 실행해주세요.
pause
exit /b 1

:run_py
start "" http://localhost:4173
py -m http.server 4173
goto :eof

:run_python
start "" http://localhost:4173
python -m http.server 4173
goto :eof

:run_python3
start "" http://localhost:4173
python3 -m http.server 4173
goto :eof
