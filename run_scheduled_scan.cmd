@echo off
cd /d D:\personal-tech-intelligence
set PYTHONUTF8=1
D:\python\python.exe D:\personal-tech-intelligence\run.py scan --dry-run >> D:\personal-tech-intelligence\state\scheduled-scan.log 2>&1
if errorlevel 1 exit /b %errorlevel%
for /f %%P in ('D:\python\python.exe D:\personal-tech-intelligence\run.py pending-count') do set PTI_PENDING=%%P
if "%PTI_PENDING%"=="0" exit /b 0
schtasks /run /tn "\PersonalTechIntelligence\PTI-Chancellor" >> D:\personal-tech-intelligence\state\scheduled-scan.log 2>&1
