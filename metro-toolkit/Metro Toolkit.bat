@echo off
rem Double-click to open the metro-toolkit dashboard. No cd or terminal needed.
rem Put this file (or a shortcut to it) anywhere; it finds the project from its own location.
setlocal
cd /d "%~dp0"
title metro-toolkit dashboard

set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo Could not find %~dp0%PY%
    echo Do the one-time setup first ^(see docs\SETUP_WINDOWS.md^):
    echo     python -m venv .venv
    echo     .venv\Scripts\python.exe -m pip install -e ".[dashboard]"
    echo.
    pause
    exit /b 1
)

"%PY%" -m metro_toolkit.launch %*
if errorlevel 1 (
    echo.
    echo The dashboard stopped with an error ^(see above^).
    pause
)
endlocal
