#!/usr/bin/env sh
# Fuseki 기동 - DB 는 fuseki-data/engenius (git 제외).
# FUSEKI_HOME : apache-jena-fuseki-5.x 압축을 푼 폴더 (fuseki-server.jar 가 있는 곳)
# JAVA_HOME   : JDK 17 이상 (없으면 PATH 의 java 사용)
set -e
cd "$(dirname "$0")/.."
if [ -z "$FUSEKI_HOME" ]; then
  echo "[NG] FUSEKI_HOME 이 설정되지 않았다" >&2
  exit 1
fi
JAVA_EXE=java
[ -n "$JAVA_HOME" ] && JAVA_EXE="$JAVA_HOME/bin/java"
export FUSEKI_BASE="$PWD/run"
exec "$JAVA_EXE" -Xmx2G -jar "$FUSEKI_HOME/fuseki-server.jar" --localhost --port 3030 --config config/fuseki/engenius.ttl
