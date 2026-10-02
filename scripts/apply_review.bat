@echo off
rem Apply the HITL verdicts in tool_review.csv to tool_aliases.yaml (then run scripts\load.bat again).
rem   Drag and drop output\<run id>\tool_review.csv onto this file, or:
rem   scripts\apply_review.bat output\<run id>\tool_review.csv [--config-dir <dir>] [--with-public-aliases]
rem This .bat is ASCII-only on purpose: cmd reads .bat files as cp949 on Korean Windows.
setlocal
cd /d "%~dp0.."
if "%~1"=="" (
  echo [NG] no csv given -- drag tool_review.csv onto this file, or pass its path as the first argument.
  pause
  exit /b 2
)
call "%~dp0env.bat"
.venv\Scripts\python -m engenius_onto apply-review %*
set RC=%errorlevel%
echo apply-review finished with rc=%RC%  -- 0 ok, 1 refused (see message above), 2 config error
endlocal
pause
