@echo off
title QU-Gate evaluation
cd /d "%~dp0"
set DISTRO=-d Ubuntu
wsl %DISTRO% -- true >nul 2>&1 || set DISTRO=
echo Running the evaluation on all 27 documents. Results go to eval\results.md
echo.
wsl %DISTRO% -- bash eval.sh
echo.
pause
