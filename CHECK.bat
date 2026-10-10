@echo off
title QU-Gate model check
cd /d "%~dp0"
set DISTRO=-d Ubuntu
wsl %DISTRO% -- true >nul 2>&1 || set DISTRO=
echo Testing your API key and looking for a working model. This takes about 1 minute.
echo.
wsl %DISTRO% -- bash -c "$HOME/.venvs/qu-gate/bin/python check_model.py"
echo.
echo Finished. The result is saved in logs\check.txt
pause
