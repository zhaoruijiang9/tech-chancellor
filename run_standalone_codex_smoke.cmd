@echo off
cd /d D:\personal-tech-intelligence
"C:\Users\25654\AppData\Roaming\npm\node_modules\@openai\codex\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe" --version > D:\personal-tech-intelligence\state\standalone-codex.stdout.txt 2> D:\personal-tech-intelligence\state\standalone-codex.stderr.txt
exit /b %ERRORLEVEL%
