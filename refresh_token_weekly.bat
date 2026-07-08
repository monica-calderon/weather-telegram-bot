@echo off
setlocal

set "PROJECT_DIR=C:\Users\Moni\MisCosas\Proyectos\github\weather-telegram-bot"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_DIR%\refresh_token_weekly.ps1" -WriteEnv

if errorlevel 1 (
    echo.
    echo Refresh token weekly script failed.
    pause
    exit /b %errorlevel%
)

echo.
echo Done.
pause
