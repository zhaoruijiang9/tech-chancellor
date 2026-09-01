@echo off
cd /d D:\personal-tech-intelligence
set PYTHONUTF8=1
echo START=%DATE% %TIME%> D:\personal-tech-intelligence\state\network-smoke.meta.txt
powershell.exe -NoProfile -NonInteractive -Command "$names='HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy'; foreach($n in $names){$v=[Environment]::GetEnvironmentVariable($n,'Process'); if([string]::IsNullOrWhiteSpace($v)){\"$n=NOT_SET\"}else{try{$u=[Uri]$v;\"$n=SET scheme=$($u.Scheme) host=$($u.Host) port=$($u.Port)\"}catch{\"$n=SET non_url\"}}}" > D:\personal-tech-intelligence\state\network-smoke.env.txt 2>&1
echo Return exactly {\"status\":\"NETWORK_OK\"}. Do not call tools, inspect files, or access any repository.> D:\personal-tech-intelligence\state\network-smoke.prompt.txt
"C:\Users\25654\AppData\Roaming\npm\node_modules\@openai\codex\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe" exec --cd D:\personal-tech-intelligence --sandbox read-only --ephemeral --skip-git-repo-check --output-last-message D:\personal-tech-intelligence\state\network-smoke.last.txt - < D:\personal-tech-intelligence\state\network-smoke.prompt.txt > D:\personal-tech-intelligence\state\network-smoke.stdout.txt 2> D:\personal-tech-intelligence\state\network-smoke.stderr.txt
echo EXITCODE=%ERRORLEVEL%>> D:\personal-tech-intelligence\state\network-smoke.meta.txt
echo END=%DATE% %TIME%>> D:\personal-tech-intelligence\state\network-smoke.meta.txt
