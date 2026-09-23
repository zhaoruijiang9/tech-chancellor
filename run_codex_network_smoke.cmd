@echo off
set "PTI_ROOT=%~dp0"
cd /d "%PTI_ROOT%"
set PYTHONUTF8=1
if not exist "%PTI_ROOT%state" mkdir "%PTI_ROOT%state"
echo START=%DATE% %TIME%> "%PTI_ROOT%state\network-smoke.meta.txt"
powershell.exe -NoProfile -NonInteractive -Command "$names='HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy'; foreach($n in $names){$v=[Environment]::GetEnvironmentVariable($n,'Process'); if([string]::IsNullOrWhiteSpace($v)){\"$n=NOT_SET\"}else{try{$u=[Uri]$v;\"$n=SET scheme=$($u.Scheme) host=$($u.Host) port=$($u.Port)\"}catch{\"$n=SET non_url\"}}}" > "%PTI_ROOT%state\network-smoke.env.txt" 2>&1
echo Return exactly {\"status\":\"NETWORK_OK\"}. Do not call tools, inspect files, or access any repository.> "%PTI_ROOT%state\network-smoke.prompt.txt"
set "CODEX_EXE=%PTI_CODEX_EXE%"
if not defined CODEX_EXE set "CODEX_EXE=%USERPROFILE%\AppData\Roaming\npm\node_modules\@openai\codex\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe"
if not exist "%CODEX_EXE%" set "CODEX_EXE=codex.exe"
"%CODEX_EXE%" exec --cd "%PTI_ROOT%" --sandbox read-only --ephemeral --skip-git-repo-check --output-last-message "%PTI_ROOT%state\network-smoke.last.txt" - < "%PTI_ROOT%state\network-smoke.prompt.txt" > "%PTI_ROOT%state\network-smoke.stdout.txt" 2> "%PTI_ROOT%state\network-smoke.stderr.txt"
echo EXITCODE=%ERRORLEVEL%>> "%PTI_ROOT%state\network-smoke.meta.txt"
echo END=%DATE% %TIME%>> "%PTI_ROOT%state\network-smoke.meta.txt"
