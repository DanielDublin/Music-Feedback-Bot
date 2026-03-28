@echo off
setlocal EnableDelayedExpansion

:: ============================================================
:: Music Feedback Bot - Windows Stop Script
:: ============================================================
set "ROOT=%~dp0..\.."
pushd "%ROOT%"
set "ROOT=%CD%"
popd

set "PID_FILE=%ROOT%\.bot_pids"

echo ============================================================
echo  Stopping Music Feedback Bot
echo ============================================================

:: ----------------------------------------------------------
:: 1. Close the CMD window by title
:: We use a wildcard (*) to ensure we catch the window even if 
:: the title was slightly altered by the shell.
:: ----------------------------------------------------------
echo [1/3] Closing Bot window...
taskkill /F /T /FI "WINDOWTITLE eq MF_Bot_Backend*" >nul 2>&1

:: ----------------------------------------------------------
:: 2. Cleanup surviving watchdog.py AND bot.py processes
:: The watchdog starts bot.py as a separate process; we must 
:: kill both to stop the loop.
:: ----------------------------------------------------------
echo [2/3] Cleaning up any remaining python processes...

powershell -NoProfile -Command ^
    "Get-CimInstance Win32_Process | " ^
    "Where-Object { $_.CommandLine -like '*watchdog.py*' -or $_.CommandLine -like '*bot.py*' } | " ^
    "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" ^
    >nul 2>&1

:: ----------------------------------------------------------
:: 3. Remove the PID marker file
:: ----------------------------------------------------------
echo [3/3] Cleaning up session files...
if exist "%PID_FILE%" del "%PID_FILE%"

echo.
echo  Music Feedback Bot stopped.
echo ============================================================
echo.