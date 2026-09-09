@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
set "PYTHON=python"
if exist "%~dp0.venv\Scripts\python.exe" set "PYTHON=%~dp0.venv\Scripts\python.exe"
%PYTHON% "%~dp0run.py" scan --dry-run >> "%~dp0state\scheduled-scan.log" 2>&1
if errorlevel 1 exit /b %errorlevel%
for /f %%P in ('%PYTHON% "%~dp0run.py" pending-count') do set PTI_PENDING=%%P
if "%PTI_PENDING%"=="0" exit /b 0
schtasks /run /tn "\PersonalTechIntelligence\PTI-Chancellor" >> "%~dp0state\scheduled-scan.log" 2>&1
