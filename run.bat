@echo off
cd /d %~dp0
set PORT=8787
where python >nul 2>nul
if %errorlevel%==0 (
  start http://localhost:%PORT%
  python -m http.server %PORT%
  goto :eof
)
where py >nul 2>nul
if %errorlevel%==0 (
  start http://localhost:%PORT%
  py -m http.server %PORT%
  goto :eof
)
where npx >nul 2>nul
if %errorlevel%==0 (
  start http://localhost:%PORT%
  npx --yes serve -l %PORT% .
  goto :eof
)
echo Python or npx is required to run local server.
pause
