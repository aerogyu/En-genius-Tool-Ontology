@echo off
rem Offline install (closed network). Run once from anywhere; it works in the repo root.
rem Needs: Python 3.10 on this PC, requirements.lock, and either offline\wheels\*.whl
rem or offline\wheels_win_amd64_cp310.zip from the import package (unpacked here with Python's zipfile).
rem This .bat is ASCII-only on purpose: cmd reads .bat files as cp949 on Korean Windows.
setlocal
cd /d "%~dp0.."
call "%~dp0env.bat"

if not exist offline\wheels\ if exist offline\wheels_win_amd64_cp310.zip (
  echo [0/4] unpacking offline\wheels_win_amd64_cp310.zip
  %PYTHON% -m zipfile -e offline\wheels_win_amd64_cp310.zip offline
  if errorlevel 1 (
    echo [NG] could not unpack the wheels zip - is Python 3.10 on PATH? See scripts\env.bat
    pause
    exit /b 1
  )
)
if not exist offline\wheels\ (
  echo [NG] offline\wheels\ not found. Put wheels_win_amd64_cp310.zip into the offline folder first.
  pause
  exit /b 1
)

echo [1/4] creating .venv with: %PYTHON%
%PYTHON% -m venv .venv
if errorlevel 1 (
  echo [NG] venv creation failed. Set PYTHON in scripts\env.bat, e.g. set PYTHON=py -3.10
  pause
  exit /b 1
)

echo [2/4] upgrading pip/setuptools/wheel from offline\wheels
.venv\Scripts\python -m pip install --no-index --find-links offline\wheels --upgrade pip setuptools wheel
if errorlevel 1 (
  echo [NG] pip upgrade failed - see the lines above.
  pause
  exit /b 1
)

echo [3/4] installing runtime packages (requirements.lock, no network)
.venv\Scripts\python -m pip install --no-index --no-deps --find-links offline\wheels -r requirements.lock
if errorlevel 1 (
  echo [NG] package install failed - see the lines above. Is offline\wheels complete for this Python?
  pause
  exit /b 1
)

echo [4/4] doctor  (the project code itself is not installed; scripts set PYTHONPATH=src)
.venv\Scripts\python -m engenius_onto doctor
if errorlevel 1 (
  echo [NG] doctor reported a problem - see the lines above. A missing Fuseki [--] is fine at this point.
) else (
  echo.
  echo Done. Next: scripts\fuseki_start.bat in its own window, then scripts\load.bat synthetic
)
endlocal
pause
