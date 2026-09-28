# En-Genius 툴 온톨로지 — 사내(폐쇄망) 설치·실행 안내

연습용 패키지 v0 (2026-09-28, M3 코드 기준). **이 판으로는 합성 데이터로 연습만 한다** — 실데이터 적재는 M3.1(적재기 보강)이 끝난
판을 다시 반입한 뒤에 한다 (인명 마스킹·파일 간 병합 수리 전에는 실데이터를 넣지 않는다).

## 0. 이 패키지로 할 수 있는 것

- 파이썬 패키지를 인터넷 없이 설치하고 환경 점검(`doctor`)까지
- Fuseki(그래프 DB) 기동, 브라우저에서 SPARQL 화면 보기
- 저장소에 든 **합성 조사 파일 9개**로 적재(`load`) → 산출물 보기 → Fuseki 에 올리기(`push`)
- 못 하는 것: 연결 도출·보고서·연결 지도(M4 에서 생김), 실데이터 적재(M3.1 뒤)

## 1. 구성물

| 파일 | 용도 | 비고 |
|---|---|---|
| `En-genius-Ontology-<커밋>.zip` | 저장소(코드·스키마·설정·합성 데이터·이 안내) | 풀면 `engenius-tool-ontology\` |
| `offline\wheels\*.whl` | 파이썬 패키지 (runtime 90개 + pip·setuptools·wheel), Windows x64 · Python 3.10 용 | 저장소 폴더 안 `offline\wheels\` 에 둔다 |
| `OpenJDK21U-jdk_x64_windows_hotspot_21.0.12.1_1.zip` | Java 21 (Fuseki 실행용) | 설치 아님 — 압축만 푼다 |
| `apache-jena-fuseki-6.2.0.zip` | 그래프 DB | 압축만 푼다 |
| `SHA256SUMS.txt` | 위 파일들의 체크섬 | 반입 심사·손상 확인용 |

라이선스·출처·체크섬의 정본은 저장소 `docs\04_반입목록.md`.

## 2. 준비

1. 사내 PC 에 **Python 3.10** 이 있어야 한다: `cmd` 에서 `python --version` → `Python 3.10.x`.
   `py -3.10 --version` 으로만 되면 3장에서 `PYTHON=py -3.10` 으로 잡는다.
2. 아래처럼 푼다 (경로에 한글·공백이 없는 곳을 권장):

```text
C:\EnGenius\
  engenius-tool-ontology\          ← 저장소 zip 을 푼 것
    offline\wheels\*.whl           ← wheel 폴더를 여기에
    scripts\env.bat                ← 경로 2개를 여기서 맞춘다
  tools\
    jdk-21.0.12.1+1\               ← JDK zip 을 푼 것 (bin\java.exe 가 있어야 함)
    apache-jena-fuseki-6.2.0\      ← Fuseki zip 을 푼 것 (fuseki-server.jar)
```

3. `scripts\env.bat` 을 메모장으로 열어 `FUSEKI_HOME`·`JAVA_HOME` 이 실제 폴더와 같은지 확인한다. 위 구조 그대로면 고칠 것 없음.

## 3. 설치 (한 번)

`scripts\setup_offline.bat` 을 **더블클릭** (또는 cmd 에서 실행). 하는 일:

1. `.venv` 가상환경 생성 (`python -m venv .venv`)
2. `offline\wheels` 에서 pip·setuptools·wheel 갱신 (인터넷 없음)
3. `requirements.lock` 의 90개 패키지 설치 — `--no-index --no-deps`, 전부 wheel 이라 컴파일 없음.
   우리 코드 자체는 설치하지 않고 저장소 폴더의 `src\` 에서 바로 실행한다 (스크립트가 `PYTHONPATH=src` 를 잡는다 — `config\`·`schema\`·`data\` 를
   저장소 기준으로 찾기 때문).
4. `doctor` 실행 → 아래처럼 `[OK]` 가 줄줄이 나오면 성공. Fuseki 줄은 아직 `[--]` 여도 된다.

```text
[OK] Python 3.10.2 (3.10 이상 필요)
[OK] Java: openjdk version "21.0.12.1" ...
[OK] rdflib 7.6.0
...
[OK] 금지 패키지 없음 (rfc3987 등)
[--] Fuseki http://127.0.0.1:3030 응답 없음 (로컬 백엔드만 사용 가능)
```

`[NG]` 가 나오면 그 줄을 그대로 메모해 둔다 (7장).

## 4. Fuseki 기동

`scripts\fuseki_start.bat` 실행 — 창이 열린 채로 있어야 DB 가 살아 있다 (닫으면 종료). 브라우저에서 `http://127.0.0.1:3030` 을 열면
Fuseki 화면이 뜬다 (데이터셋 `engenius`). 이건 DBMS 관리 콘솔 같은 것 — SPARQL 을 직접 쳐 볼 수 있다.
DB 파일은 저장소 안 `fuseki-data\` 에 생긴다.

## 5. 합성 데이터로 연습

1. `scripts\load.bat synthetic` (더블클릭하면 기본이 synthetic). 끝에 `load finished with rc=…` 와 실행 ID 가 찍힌다.
   - `rc=0` 정상, `rc=1` 경고·행 문제가 있어 파일로 남김(정상 범위 — 합성 데이터에는 일부러 문제 행이 있다), `rc=2` 중단.
2. `output\<실행ID>\` 를 연다 (실행ID 는 `20260928T101500` 같은 일시):
   - `survey.ttl` — 적재 결과 그래프 (텍스트, 메모장으로 열림)
   - `load_log.json` — 파일 목록(이름·sha256)·건수(`counts`)·제외 행(`excluded_rows`)·**경고 목록(`warnings`)**·스키마 위반(`schema_issues`)·
     툴 통합 후보·미해석 연계 툴·레지스트리 요약·SHACL 결과. 합성 데이터에는 일부러 넣은 문제 행이 있어 경고가 스무 건쯤 나오는 게 정상
   - `tool_review.csv` — 툴 통합 검토표 (HITL 입력: 엑셀로 열어 `판정(통합/별개)` 열을 채우면 `apply-review` 가 반영)
3. Fuseki 가 떠 있으면 `scripts\push.bat` → Fuseki 화면 `engenius` 데이터셋 → query 탭에서:

```sparql
SELECT (COUNT(*) AS ?n) WHERE { GRAPH ?g { ?s ?p ?o } }
```

숫자가 나오면 끝까지 연결된 것이다. 이 흐름이 나중에 실데이터에서도 그대로다 (`load.bat real`).

## 6. 실데이터 — 아직 하지 말 것 (M3.1 판에서)

준비만 알아 두면 된다:
- 파일은 `data\real\survey\` 에 `Tool조사_<파트약칭>_<YYYYMMDD>.xlsx` (규칙: `docs\02` 5-1). 레지스트리는 `data\real\registry\` 에 자동 생성.
- `config\parts.yaml` (파트 약칭·정식 이름·담당 부서), `config\rules.yaml` (시트명·선택지 등), `config\header_map.yaml` 만 고치면 되고 코드는 손대지 않는다.
- `data\real\`·`output\`·`fuseki-data\` 는 사내에만 둔다.

## 7. 문제가 생기면 — 무엇을 밖으로 가져올 수 있나

밖(개발 PC)으로는 **값이 없는 것만**: `[NG]` 줄, `doctor` 출력, 경고의 **종류와 건수**, 파이썬 traceback 의 마지막 몇 줄.
셀 값·툴명·경로·인명·파일명은 옮기지 않는다. (M3.1 에서 이것만 모아 주는 `diag` 명령이 생긴다.)

## 8. 자주 걸리는 것

- `python` 이 3.10 이 아니거나 없음 → `scripts\env.bat` 의 `set PYTHON=py -3.10` 주석을 풀어 맞춘다.
- `.bat` 메시지가 영문인 이유: 한국어 Windows 의 cmd 가 .bat 을 cp949 로 읽어 한글이 깨지기 때문. 파이썬 출력은 한국어다.
- 포트 3030 이 이미 사용 중 → `scripts\fuseki_start.bat` 의 `--port` 를 바꾸고 `config\fuseki.yaml` 도 같이.
- `[NG] FUSEKI_HOME` / Java 없음 → `scripts\env.bat` 경로 확인. JDK 는 설치 프로그램이 아니라 zip 이라 관리자 권한이 필요 없다.
- PowerShell 실행 정책 오류는 `.ps1` 에만 해당 — 여기 스크립트는 전부 `.bat`.
- `.bat` 없이 직접 치고 싶으면 (PowerShell, 저장소 폴더에서): `$env:PYTHONPATH="src"` 한 뒤 `.venv\Scripts\python -m engenius_onto --help`.
  cmd 에서는 `set PYTHONPATH=src`. 이걸 빼먹으면 `No module named engenius_onto` 가 난다.
