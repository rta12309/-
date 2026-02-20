@echo off
setlocal
cd /d "%~dp0"

set "PY_CMD="
where py >nul 2>nul && set "PY_CMD=py"
if not defined PY_CMD where python >nul 2>nul && set "PY_CMD=python"
if not defined PY_CMD where python3 >nul 2>nul && set "PY_CMD=python3"

if not defined PY_CMD goto no_python

start "" http://localhost:4173
%PY_CMD% -m http.server 4173
goto :eof

:no_python
echo Python is not installed. Please install Python and run this file again.
pause
exit /b 1
