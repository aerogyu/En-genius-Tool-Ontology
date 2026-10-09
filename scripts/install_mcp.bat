@echo off
rem Install the MCP server packages (mcp + dependencies) into .venv, offline, from whatever wheel folder holds mcp-*.whl.
rem Put the wheels under offline\ in any layout: offline\wheels_mcp\*.whl, a nested folder, or a zip named offline\wheels_mcp*.zip
rem (the zip is unpacked into offline\wheels_mcp\). Any mcp 1.x version works (tested 1.28.1 and 1.30.0).
rem Packages already in requirements.lock (pydantic etc.) are held at their locked versions (-c requirements.lock): nothing gets upgraded.
rem This .bat is ASCII-only on purpose: cmd reads .bat files as cp949 on Korean Windows.
setlocal
cd /d "%~dp0.."
call "%~dp0env.bat"
if not exist offline\wheels_mcp\ for %%z in (offline\wheels_mcp*.zip) do (
  echo [1/3] unpacking %%z into offline\wheels_mcp
  .venv\Scripts\python -m zipfile -e "%%z" offline\wheels_mcp
)
set MCPDIR=
for /r offline %%f in (mcp-1*.whl) do set MCPDIR=%%~dpf
if "%MCPDIR%"=="" (
  echo [NG] no mcp-1.x wheel found under offline\ - put the wheel folder or zip into offline\ first
  pause
  exit /b 1
)
rem %%~dpf ends with a backslash; "...\" would escape the closing quote, so drop it.
set MCPDIR=%MCPDIR:~0,-1%
echo [2/3] pip install mcp from %MCPDIR% - no internet, locked packages kept
.venv\Scripts\python -m pip install --no-index --find-links "%MCPDIR%" --find-links offline\wheels -c requirements.lock "mcp>=1.10,<2"
if errorlevel 1 (
  echo [NG] pip install failed - read the lines above. A missing dependency wheel is named there.
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
