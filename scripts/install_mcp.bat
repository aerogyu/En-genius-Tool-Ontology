@echo off
rem Install the MCP server packages (M6 v0: mcp 1.30.0 + 16 dependencies, all MIT/BSD/Apache/PSF) into .venv, offline.
rem Needs offline\wheels_mcp_win_amd64_cp310.zip from the import package (unpacked here) or an offline\wheels_mcp\ folder.
rem Existing packages are not upgraded (mcp 1.30.0 works with the pydantic already installed).
rem This .bat is ASCII-only on purpose: cmd reads .bat files as cp949 on Korean Windows.
setlocal
cd /d "%~dp0.."
call "%~dp0env.bat"
if not exist offline\wheels_mcp\ if exist offline\wheels_mcp_win_amd64_cp310.zip (
  echo [1/3] unpacking offline\wheels_mcp_win_amd64_cp310.zip
  .venv\Scripts\python -m zipfile -e offline\wheels_mcp_win_amd64_cp310.zip offline
)
if not exist offline\wheels_mcp\ (
  echo [NG] offline\wheels_mcp\ not found. Put wheels_mcp_win_amd64_cp310.zip into the offline folder first.
  pause
  exit /b 1
)
echo [2/3] pip install mcp from offline\wheels_mcp - no internet
.venv\Scripts\python -m pip install --no-index --find-links offline\wheels_mcp --find-links offline\wheels mcp==1.30.0
if errorlevel 1 (
  echo [NG] pip install failed - read the lines above
  pause
  exit /b 1
)
echo [3/3] self-check: license guard and the 8 MCP tools on the latest load
.venv\Scripts\python -m engenius_onto licenses > offline\licenses_after_mcp.txt
if errorlevel 1 echo [NG] license guard failed - see offline\licenses_after_mcp.txt
.venv\Scripts\python -m engenius_onto mcp --check
echo.
echo [install_mcp] done. Next: scripts\mcp_check.bat any time, and the bridge settings in README_offline.md chapter 9.
endlocal
pause
