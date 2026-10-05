@echo off
setlocal
cd /d "%~dp0"
"runtime\python.exe" -X utf8 prepare_postgres.py
if errorlevel 1 goto failed
docker compose --env-file .env.postgres up -d --wait
if errorlevel 1 goto failed
"runtime\python.exe" -X utf8 launch.py --postgres %*
if errorlevel 1 goto failed
exit /b 0
:failed
echo PostgreSQL start failed. Check that Docker Desktop is running.
pause
exit /b 1
