@echo off
rem Push the latest output\<run id>\ graphs to the local Fuseki (scripts\fuseki_start.bat must be running).
rem   scripts\push.bat                    -> latest run
rem   scripts\push.bat --run <run id>     -> that run
rem This .bat is ASCII-only on purpose: cmd reads .bat files as cp949 on Korean Windows.
setlocal
cd /d "%~dp0.."
call "%~dp0env.bat"
.venv\Scripts\python -m engenius_onto push %*
endlocal
pause
