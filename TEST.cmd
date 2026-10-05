@echo off
setlocal
cd /d "%~dp0"
"runtime\python.exe" -X utf8 verify.py
pause
