@echo off
rem Start Fuseki from the repo root. DB lives in fuseki-data\engenius (git-ignored).
rem FUSEKI_HOME : folder of unpacked apache-jena-fuseki-6.x (Java 21) or 5.x (Java 17)
rem JAVA_HOME   : JDK 21 for Fuseki 6.x, 17+ for 5.x (falls back to java on PATH)
rem This .bat is ASCII-only on purpose: cmd reads .bat files as cp949 on Korean Windows.
setlocal
cd /d "%~dp0.."
if exist "%~dp0env.bat" call "%~dp0env.bat"
if "%FUSEKI_HOME%"=="" (
  echo [NG] FUSEKI_HOME is not set. e.g. set FUSEKI_HOME=C:\EnGenius\tools\apache-jena-fuseki-6.2.0
  exit /b 1
)
set JAVA_EXE=java
if not "%JAVA_HOME%"=="" set JAVA_EXE="%JAVA_HOME%\bin\java.exe"
set FUSEKI_BASE=%CD%\run
%JAVA_EXE% -Xmx2G -jar "%FUSEKI_HOME%\fuseki-server.jar" --localhost --port 3030 --config config\fuseki\engenius.ttl
rem Reached only when the server stops (or fails to start: port 3030 busy, java not found). Keep the window open to read why.
echo.
echo [fuseki] server stopped. If it ended at once, read the lines above (port 3030 in use? JAVA_HOME in scripts\env.bat?)
pause
