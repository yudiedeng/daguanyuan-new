@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js is required. Install Node.js, then run this file again.
  pause
  exit /b 1
)
if not exist "%~dp0daguanyuan\index.html" (
  echo Please extract the complete ZIP before starting the game.
  pause
  exit /b 1
)
set "PORT=8000"
echo Daguanyuan v4 Release - 2026-10-20
echo Open http://127.0.0.1:8000/ after the server starts.
echo Keep this window open while playing. Press Ctrl+C to stop.
echo.
node "%~dp0serve.cjs"
pause
