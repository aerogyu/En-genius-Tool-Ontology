@echo off
rem 3D view of the loaded ontology: reads the latest output\<run id>\survey.ttl, writes graph3d.html next to it, opens the browser.
rem   scripts\graph_view.bat                         -> latest run
rem   scripts\graph_view.bat --run output\<run id>   -> that run
rem The HTML contains the loaded data. When built from real data, keep it in-house.
rem This .bat is ASCII-only on purpose: cmd reads .bat files as cp949 on Korean Windows.
setlocal
cd /d "%~dp0.."
call "%~dp0env.bat"
.venv\Scripts\python scripts\graph_view3d.py --open %*
endlocal
pause
