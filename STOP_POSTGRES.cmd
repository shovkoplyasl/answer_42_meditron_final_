@echo off
setlocal
cd /d "%~dp0"
docker compose --env-file .env.postgres stop
pause
