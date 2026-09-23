@echo off
set "PTI_ROOT=%~dp0"
cd /d "%PTI_ROOT%"
set "PYTHONUTF8=1"
set "PYTHON=python"
if exist "%PTI_ROOT%.venv\Scripts\python.exe" set "PYTHON=%PTI_ROOT%.venv\Scripts\python.exe"
"%PYTHON%" "%PTI_ROOT%run.py" dashboard
