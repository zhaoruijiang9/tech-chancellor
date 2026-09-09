@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
set "PYTHON=python"
if exist "%~dp0.venv\Scripts\python.exe" set "PYTHON=%~dp0.venv\Scripts\python.exe"
%PYTHON% "%~dp0run.py" stage-b >> "%~dp0state\chancellor.log" 2>&1
