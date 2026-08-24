@echo off
echo.
echo  Starting TTI Platform Launcher...
echo  Dashboard will open at http://localhost:9001
echo.
cd /d "%~dp0scripts\launcher-ui"
node server.js
