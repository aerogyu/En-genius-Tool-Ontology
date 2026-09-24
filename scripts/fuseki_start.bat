@echo off
rem Start Fuseki from the repo root. DB lives in fuseki-data\engenius (git-ignored).
rem FUSEKI_HOME : folder of unpacked apache-jena-fuseki-6.x (Java 21) or 5.x (Java 17)
rem JAVA_HOME   : JDK 21 for Fuseki 6.x, 17+ for 5.x (falls back to java on PATH)
rem This .bat is ASCII-only on purpose: cmd reads .bat files as cp949 on Korean Windows.
setlocal
cd /d "%~dp0.."
if "%FUSEKI_HOME%"=="" (
  echo [NG] FUSEKI_HOME is not set. e.g. set FUSEKI_HOME=C:\EnGenius\tools\apache-jena-fuseki-6.2.0
  exit /b 1
)
set JAVA_EXE=java
if not "%JAVA_HOME%"=="" set JAVA_EXE="%JAVA_HOME%\bin\java.exe"
set FUSEKI_BASE=%CD%\run
%JAVA_EXE% -Xmx2G -jar "%FUSEKI_HOME%\fuseki-server.jar" --localhost --port 3030 --config config\fuseki\engenius.ttl
