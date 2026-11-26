@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run install_atof.cmd first.
  exit /b 1
)
set "ATOF_ANALYTICS_ENABLED=1"
echo ATOF dashboard: http://127.0.0.1:8081/dashboard
echo Stop with Ctrl+C. If port 8081 is occupied, stop your own previous ATOF server first.
".venv\Scripts\python.exe" -I -m uvicorn atof.api:app --host 127.0.0.1 --port 8081
exit /b %errorlevel%
