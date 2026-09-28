@echo off
rem Load survey xlsx files into a survey graph (TTL) + warnings + tool_review.csv.
rem   scripts\load.bat synthetic   -> data\synthetic\survey  (practice data shipped with the repo)
rem   scripts\load.bat real        -> data\real\survey       (in-house files; registry in data\real\registry)
rem Output goes to output\<run id>\ ; the run id is printed at the end.
rem This .bat is ASCII-only on purpose: cmd reads .bat files as cp949 on Korean Windows.
setlocal
cd /d "%~dp0.."
call "%~dp0env.bat"
set DATASET=%1
if "%DATASET%"=="" set DATASET=synthetic
if not "%DATASET%"=="synthetic" if not "%DATASET%"=="real" (
  echo [NG] usage: load.bat synthetic ^| real
  exit /b 1
)
if "%DATASET%"=="real" if not exist data\real\survey\ (
  echo [NG] data\real\survey\ not found. Put the survey xlsx files there first. File name rule: README_offline.md
  exit /b 1
)
.venv\Scripts\python -m engenius_onto load --data %DATASET% %2 %3 %4
set RC=%errorlevel%
echo.
echo load finished with rc=%RC%  -- 0 ok, 1 warnings/issues written, 2 stopped
endlocal
pause
