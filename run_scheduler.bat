@echo off
setlocal
cd /d "%~dp0"
title Job Searcher V2 Scheduler

py -3.12 -m app.cli schedule

endlocal
