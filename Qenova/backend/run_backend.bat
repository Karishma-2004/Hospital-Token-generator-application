@echo off
setlocal
cd /d %~dp0
rem Starts the API WITH WebSocket support (needed for the live queue). Use this instead of "manage.py runserver".
python manage.py migrate
if errorlevel 1 exit /b 1
python -m uvicorn config.asgi:application --reload --port 8000
endlocal
