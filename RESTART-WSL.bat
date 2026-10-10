@echo off
title Restart Ubuntu (WSL)
echo This restarts Ubuntu (WSL). It closes any open Ubuntu window and stops the QU-Gate app if it is running.
echo Your files are not changed.
echo.
pause
wsl --shutdown
echo.
echo Waiting 10 seconds...
timeout /t 10 /nobreak >nul
wsl -d Ubuntu -- echo Ubuntu is running again.
echo.
echo Done. Now double-click EVAL (or RUN).
pause
