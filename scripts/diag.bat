@echo off
rem Diagnostic summary of the latest load: warning kinds and counts per column and per part - NO cell values.
rem This is what may be taken outside (docs\08 chapter 8). Also written to output\<run id>\diag.txt by every load.
rem This .bat is ASCII-only on purpose: cmd reads .bat files as cp949 on Korean Windows.
setlocal
cd /d "%~dp0.."
call "%~dp0env.bat"
.venv\Scripts\python -m engenius_onto diag %*
endlocal
pause
