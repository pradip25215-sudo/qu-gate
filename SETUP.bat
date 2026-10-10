@echo off
title QU-Gate setup
cd /d "%~dp0"
set DISTRO=-d Ubuntu
wsl %DISTRO% -- true >nul 2>&1 || set DISTRO=
echo Running setup inside Ubuntu. This takes 3 to 10 minutes. Do not close this window.
echo.
wsl %DISTRO% -- bash setup.sh
echo.
echo If you see "SETUP DONE." above, double-click RUN.bat next.
pause
