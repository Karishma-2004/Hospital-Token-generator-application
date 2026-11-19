@echo off
setlocal
cd /d %~dp0
rem Sends the 24-hour and 1-hour appointment reminders. Leave this window open while the app is in use.
python manage.py send_reminders --loop --interval 60
endlocal
