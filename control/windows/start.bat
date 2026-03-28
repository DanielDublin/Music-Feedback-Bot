@echo off
setlocal EnableDelayedExpansion

:: ============================================================
:: Music Feedback Bot - Windows Start Script
:: Resolves project root (two levels up from this script)
:: ============================================================
set "ROOT=%~dp0..\.."
pushd "%ROOT%"
set "ROOT=%CD%"
popd

set "PID_FILE=%ROOT%\.bot_pids"

:: Check if already running
if exist "%PID_FILE%" (
    echo [WARN] .bot_pids file found - Bot may already be running.
    echo        Run stop.bat first, or delete .bot_pids and try again.
    pause
    exit /b 1
)

echo ============================================================
echo  Starting Music Feedback Bot
echo ============================================================

:: ----------------------------------------------------------
:: 1. Auto-install requirements
:: ----------------------------------------------------------
if exist "%ROOT%\requirements.txt" (
    echo Checking/Installing dependencies from requirements.txt...
    python -m pip install --upgrade pip >nul
    python -m pip install -r "%ROOT%\requirements.txt"
) else (
    echo [SKIP] No requirements.txt found.
)

:: ----------------------------------------------------------
:: 2. Start Backend - watchdog.py
:: ----------------------------------------------------------
echo Starting bot watchdog...

:: Start in a new window with a specific title for easy tracking
start "MF_Bot_Backend" cmd /k "title MF_Bot_Backend && cd /d "%ROOT%" && python watchdog.py" 

:: Save window title to marker file for stop.bat
echo MF_Bot_Backend > "%PID_FILE%"

echo.
echo ============================================================
echo  Bot is starting up in a separate window.
echo  Run stop.bat to shut it down.
echo ============================================================
echo.
timeout /t 3