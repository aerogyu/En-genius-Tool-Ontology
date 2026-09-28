@echo off
rem Local paths for this PC. Edit the two lines below once; every other script calls this file.
rem This .bat is ASCII-only on purpose: cmd reads .bat files as cp949 on Korean Windows.
rem FUSEKI_HOME : folder of the unpacked apache-jena-fuseki-6.2.0 zip
rem JAVA_HOME   : folder of the unpacked JDK 21 zip (contains bin\java.exe)
if "%FUSEKI_HOME%"=="" set FUSEKI_HOME=C:\EnGenius\tools\apache-jena-fuseki-6.2.0
if "%JAVA_HOME%"=="" set JAVA_HOME=C:\EnGenius\tools\jdk-21.0.12.1+1
rem PYTHON : interpreter used to create .venv (default: python on PATH). e.g. set PYTHON=py -3.10
if "%PYTHON%"=="" set PYTHON=python
rem The code is run from the repo folder (src\), not installed as a package: config\, schema\, data\ are found relative to it.
set PYTHONPATH=%~dp0..\src
