@echo off
cd /d "%~dp0"
if not exist node_modules (
  echo Installing frontend dependencies...
  npm install
  if errorlevel 1 (
    echo Dependency installation failed. Check internet access and Node.js/npm.
    pause
    exit /b 1
  )
)
npm run dev
pause
