@echo off
setlocal
cd /d "%~dp0"
if not exist node_modules (
  echo Installing frontend dependencies...
  call npm install
  if errorlevel 1 goto :error
)
echo Starting React/Vite frontend...
call npm run dev
exit /b 0
:error
echo Frontend setup failed.
pause
exit /b 1
