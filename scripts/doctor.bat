@echo off
rem Environment check: Python, packages, forbidden packages, Java, Fuseki.
rem This .bat is ASCII-only on purpose: cmd reads .bat files as cp949 on Korean Windows.
setlocal
cd /d "%~dp0.."
call "%~dp0env.bat"
.venv\Scripts\python -m engenius_onto doctor
endlocal
pause
