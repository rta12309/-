@echo off
cd /d %~dp0
where py >nul 2>nul
if %errorlevel%==0 (
  start "" http://localhost:4173
  py -m http.server 4173
  goto :eof
)
where python >nul 2>nul
if %errorlevel%==0 (
  start "" http://localhost:4173
  python -m http.server 4173
  goto :eof
)
where python3 >nul 2>nul
if %errorlevel%==0 (
  start "" http://localhost:4173
  python3 -m http.server 4173
  goto :eof
)
echo Python이 설치되어 있지 않습니다. Python 설치 후 다시 실행해주세요.
pause
