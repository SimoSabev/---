@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >/dev/null 2>nul
if %errorlevel%==0 (
    py -3 main.py
) else (
    python main.py
)
pause
