@echo off
setlocal
cd /d "%~dp0"
py -3.11 -c "import struct; assert struct.calcsize('P') == 8, 'Python x64 required'"
if errorlevel 1 goto failed
if not exist ".venv\Scripts\python.exe" (
  py -3.11 -m venv ".venv"
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install --no-index --find-links "%~dp0wheelhouse" --upgrade atof-intelligent-token-optimizer
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto failed
echo ATOF installed. Run run_atof.cmd.
exit /b 0
:failed
echo Installation failed. Verify approved Python 3.11 x64 and the extracted wheelhouse.
exit /b 1
