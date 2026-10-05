@echo off
setlocal
cd /d "%~dp0"
"runtime\python.exe" -X utf8 launch.py %*
if errorlevel 1 pause
