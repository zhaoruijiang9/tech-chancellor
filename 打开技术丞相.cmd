@echo off
setlocal
chcp 65001 >nul
set "PTI_ROOT=%~dp0"
set "PYTHONUTF8=1"
set "PTI_PYTHON=python"
if exist "%PTI_ROOT%.venv\Scripts\python.exe" set "PTI_PYTHON=%PTI_ROOT%.venv\Scripts\python.exe"
if exist "%PTI_ROOT%.venv\Scripts\pythonw.exe" set "PTI_PYTHON=%PTI_ROOT%.venv\Scripts\pythonw.exe"
cd /d "%PTI_ROOT%"
start "" /b "%PTI_PYTHON%" "%PTI_ROOT%run.py" dashboard
endlocal
