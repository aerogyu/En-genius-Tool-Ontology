@echo off
rem Self-check of the Tool Ontology MCP server without the AI platform: calls each of the 8 tools once on the latest load.
rem   scripts\mcp_check.bat                 -> latest real-data load
rem   scripts\mcp_check.bat --data synthetic
rem The results contain real tool names - in-house only. Only the [OK]/[NG] lines may go outside.
rem This .bat is ASCII-only on purpose: cmd reads .bat files as cp949 on Korean Windows.
setlocal
cd /d "%~dp0.."
call "%~dp0env.bat"
.venv\Scripts\python -m engenius_onto mcp --check %*
endlocal
pause
