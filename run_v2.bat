@echo off
setlocal
cd /d "%~dp0"
title Job Searcher V2 Launcher

if not exist "data\job_searcher_v2.sqlite3" (
  py -3.12 -m app.cli init-db
  if errorlevel 1 exit /b 1
)

start "Job Searcher V2 API" /min py -3.12 -m app.cli serve
timeout /t 2 /nobreak >nul

cd /d "%~dp0frontend"
if not exist "node_modules" call npm.cmd install
start "Job Searcher V2 Frontend" /min npm.cmd run dev

echo.
echo Job Searcher V2 iniciado:
echo   Dashboard: http://localhost:5173
echo   API:       http://localhost:8765
echo   API docs:  http://localhost:8765/docs
echo.
endlocal
