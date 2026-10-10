@echo off
title QU-Gate app
cd /d "%~dp0"
set DISTRO=-d Ubuntu
wsl %DISTRO% -- true >nul 2>&1 || set DISTRO=
echo Starting QU-Gate. Your browser opens in about 10 seconds: http://localhost:8501
echo To stop the app, close this window.
echo.
start "" /min cmd /c "timeout /t 10 /nobreak >nul & start http://localhost:8501"
wsl %DISTRO% -- bash run.sh
echo.
pause
