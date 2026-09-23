@echo off
set "PTI_ROOT=%~dp0"
cd /d "%PTI_ROOT%"
if not exist "%PTI_ROOT%state" mkdir "%PTI_ROOT%state"
set "CODEX_EXE=%PTI_CODEX_EXE%"
if not defined CODEX_EXE set "CODEX_EXE=%USERPROFILE%\AppData\Roaming\npm\node_modules\@openai\codex\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe"
if not exist "%CODEX_EXE%" set "CODEX_EXE=codex.exe"
"%CODEX_EXE%" --version > "%PTI_ROOT%state\standalone-codex.stdout.txt" 2> "%PTI_ROOT%state\standalone-codex.stderr.txt"
exit /b %ERRORLEVEL%
