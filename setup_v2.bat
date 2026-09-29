@echo off
setlocal
cd /d "%~dp0"
title Job Searcher V2 Setup

py -3.12 -m pip install -e ".[dev]"
if errorlevel 1 exit /b 1

pushd frontend
call npm.cmd install
if errorlevel 1 exit /b 1
popd

py -3.12 -m app.cli init-db
if errorlevel 1 exit /b 1

echo Job Searcher V2 preparado correctamente.
echo Para importar datos de V1: py -3.12 -m app.cli migrate-v1 RUTA_AL_CSV
endlocal
