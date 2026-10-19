@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js is required. Install Node.js, then run this file again.
  pause
  exit /b 1
)
echo Open http://127.0.0.1:8000/ in your browser after the server starts.
echo Keep this window open while playing. Press Ctrl+C to stop.
echo.
node "%~dp0serve.cjs"
pause
