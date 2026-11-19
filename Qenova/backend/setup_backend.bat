@echo off
setlocal
cd /d %~dp0
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
python manage.py makemigrations
if errorlevel 1 exit /b 1
python manage.py migrate
if errorlevel 1 exit /b 1
python manage.py check
if errorlevel 1 exit /b 1
echo.
echo Backend setup completed.
echo Run: python manage.py runserver
endlocal
