@echo off
rem Self-check after an update: doctor -> pytest -q -> offline\selftest_<commit>.txt (PASS/FAIL + failed test names only, no data values).
rem Tests that need Fuseki or Java skip themselves. Takes about 1-2 minutes. The .txt may be taken outside; the .log stays in-house.
rem The commit is the first line of offline\installed_commit.txt (written by the update script / the import package).
rem This .bat is ASCII-only on purpose: cmd reads .bat files as cp949 on Korean Windows.
setlocal
cd /d "%~dp0.."
call "%~dp0env.bat"
rem env.bat turns on PYTHONUTF8, so the redirected log is UTF-8; switch this console to UTF-8 too so "type" shows Korean correctly.
chcp 65001 >nul
rem Read the commit with python (utf-8-sig): Notepad may save the marker with a BOM, and "set /p" would keep those 3 bytes in the file name.
set COMMIT=unknown
for /f "usebackq delims=" %%c in (`.venv\Scripts\python -c "import pathlib; p = pathlib.Path('offline/installed_commit.txt'); print((p.read_text(encoding='utf-8-sig').split() or ['unknown'])[0][:7] if p.is_file() else 'unknown')"`) do set COMMIT=%%c
if not exist offline\ mkdir offline
set OUT=offline\selftest_%COMMIT%.txt
set LOG=offline\selftest_%COMMIT%.log
echo [selftest] installed commit %COMMIT%
echo [selftest] 1/2 doctor
.venv\Scripts\python -m engenius_onto doctor > "%LOG%" 2>&1
set DOCTOR_RC=%errorlevel%
type "%LOG%"
echo [selftest] 2/2 pytest -q  (about 1-2 minutes; tests needing Fuseki or Java are skipped)
.venv\Scripts\python -m pytest -q --tb=no -rfE -p no:cacheprovider tests >> "%LOG%" 2>&1
set RC=%errorlevel%
if "%RC%"=="0" (set VERDICT=PASS) else (set VERDICT=FAIL)
> "%OUT%" echo selftest %VERDICT%  commit %COMMIT%  %DATE% %TIME%  doctor rc=%DOCTOR_RC%  pytest rc=%RC%
>> "%OUT%" findstr /B /C:"[OK]" /C:"[NG]" /C:"[--]" "%LOG%"
>> "%OUT%" findstr /R /B /C:"[0-9][0-9]* passed" /C:"[0-9][0-9]* failed" /C:"[0-9][0-9]* error" /C:"no tests ran" "%LOG%"
rem Failed/errored test names only: the whole "FAILED nodeid" part (nodeids may contain spaces), cut before " - message" (values may be there).
.venv\Scripts\python -c "import sys; [print(l.split(' - ')[0].rstrip()) for l in open(sys.argv[1], encoding='utf-8', errors='replace') if l.startswith(('FAILED ', 'ERROR '))]" "%LOG%" >> "%OUT%"
echo.
type "%OUT%"
echo.
echo [selftest] %VERDICT%  -- result file (may go outside): %OUT%
echo [selftest] full log (in-house only, may contain values): %LOG%
endlocal
pause
