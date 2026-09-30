# En-Genius 툴 온톨로지 — 사내(폐쇄망) 설치·실행 안내

연습용 패키지 v0.1 (2026-09-29) + 업데이트(6-1장). **M3.1 판(`1874bc7` 이후)부터 실데이터 적재 가능** — 6장.
그 전 판(`2d6e8c6`·`f3a4f55`)으로는 합성 데이터 연습만 한다 (양식 v1.1 을 못 읽고 인명 보호가 없다).

**받는 곳**: GitHub 비공개 저장소 `aerogyu/En-genius-Ontology` 의 **`import-package` 브랜치** — 파일을 하나씩 열어 `Download`(원본 받기).
큰 zip 은 Git LFS 로 올라가 있어 브랜치 전체 'Download ZIP' 으로는 알맹이가 안 받아진다 — 파일마다 받는다.

## 0. 이 패키지로 할 수 있는 것

- 파이썬 패키지를 인터넷 없이 설치하고 환경 점검(`doctor`)까지
- Fuseki(그래프 DB) 기동, 브라우저에서 SPARQL 화면 보기
- 저장소에 든 **합성 조사 파일 9개**로 적재(`load`) → 산출물 보기 → Fuseki 에 올리기(`push`) → 적재한 그래프를 3D 로 보기(`graph_view`)
- 못 하는 것: 연결 도출·보고서·연결 지도(M4 에서 생김), 실데이터 적재(M3.1 뒤)

## 1. 구성물

| 파일 | 용도 | 비고 |
|---|---|---|
| `En-genius-Ontology-<커밋>.zip` | 저장소(코드·스키마·설정·합성 데이터·이 안내) | 풀면 `engenius-tool-ontology\` |
| `wheels_win_amd64_cp310.zip` | 파이썬 패키지 93개 (runtime 90 + pip·setuptools·wheel), Windows x64 · Python 3.10 용 | **풀지 말고** `engenius-tool-ontology\offline\` 에 그대로 — 설치 스크립트가 푼다 |
| `OpenJDK21U-jdk_x64_windows_hotspot_21.0.12.1_1.zip` | Java 21 (Fuseki 실행용) | 설치 아님 — 압축만 푼다 |
| `apache-jena-fuseki-6.2.0.zip` | 그래프 DB | 압축만 푼다 |
| `maps\preview_map.html` · `maps\preview_map3d.html` | 툴 연결 지도 미리보기 2D·3D (합성 데이터) | 브라우저로 바로 열림, 설치 불필요 |
| `SHA256SUMS.txt` | 위 파일들의 체크섬 | 반입 심사·손상 확인용 |

라이선스·출처·체크섬의 정본은 저장소 `docs\04_반입목록.md`.

## 2. 준비

1. 사내 PC 에 **Python 3.10** 이 있어야 한다: `cmd` 에서 `python --version` → `Python 3.10.x`.
   `py -3.10 --version` 으로만 되면 3장에서 `PYTHON=py -3.10` 으로 잡는다.
2. 아래처럼 푼다 (경로에 한글·공백이 없는 곳을 권장):

```text
C:\EnGenius\
  engenius-tool-ontology\          ← 저장소 zip 을 푼 것
    offline\wheels_win_amd64_cp310.zip   ← wheels zip 을 풀지 말고 여기에
    scripts\env.bat                ← 경로 2개를 여기서 맞춘다
  tools\
    jdk-21.0.12.1+1\               ← JDK zip 을 푼 것 (bin\java.exe 가 있어야 함)
    apache-jena-fuseki-6.2.0\      ← Fuseki zip 을 푼 것 (fuseki-server.jar)
```

3. `scripts\env.bat` 을 메모장으로 열어 `FUSEKI_HOME`·`JAVA_HOME` 이 실제 폴더와 같은지 확인한다. 위 구조 그대로면 고칠 것 없음.

## 3. 설치 (한 번)

`scripts\setup_offline.bat` 을 **더블클릭** (또는 cmd 에서 실행). 하는 일:

0. `offline\wheels\` 가 없으면 `offline\wheels_win_amd64_cp310.zip` 을 파이썬으로 푼다
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

4. **적재한 온톨로지를 3D 로 보기**: `scripts\graph_view.bat` 더블클릭 → 최신 `output\<실행ID>\survey.ttl` 을 읽어 같은 폴더에
   `graph3d.html` 을 만들고 브라우저로 연다. 연결 지도 미리보기(`maps\*.html`, 골든 계산)와 달리 **방금 적재한 그래프 그대로**다 —
   동그라미 = 툴사용(분야 묶음), 파란 네모 = 툴, 선 = 조사표에 '연계 툴'로 신고된 주고받음(주황 = 메일·수기 전달), 점선 = 사용 관계.
   노드를 누르면 그래프에 적힌 속성과 입출력이 나온다. 확장자·데이터명으로 계산한 연결(Feed)은 M4 에서 더해진다.
   **실데이터로 만든 `graph3d.html` 은 적재한 내용이 그대로 들어 있으니 밖으로 가져가지 않는다.**

## 6. 실데이터 적재 (M3.1 판부터 — 저장소 `1874bc7` 이후)

1. **파일 두기**: `data\real\survey\` 에 `Tool조사_<약칭>_<YYYYMMDD>.xlsx` 20개 (약칭 표·규칙: `docs\10` 5장. 날짜 = 적재 폴더에 넣은 날).
   형상설계는 `Tool조사_MD_…` 한 파일 — 행의 Tool ID(MDT-·MDC-)로 두 파트로 나뉜다. 양식 v1.0·v1.1 둘 다 읽는다.
2. **적재**: `scripts\load.bat real` → `output\<실행ID>\` 에
   - `survey.ttl` · `load_log.json` (경고 전체 — 값이 들어 있으니 사내에만)
   - `fix_requests\<파일>_수정요청.xlsx` — **담당자에게 보낼 수정 요청표** (시트·행·Tool ID·열·적힌 값·문제·고치는 법)
   - `diag.txt` — **반출용 진단 요약** (경고 종류·열·파트별 건수만, 값 없음)
3. **드롭다운 대신 직접 적은 값**: 뜻이 분명한 것은 `config\value_aliases.yaml` 에 `열 이름: {적힌 값: 드롭다운 값}` 으로 적고 2번을 다시 한다
   (엑셀은 고치지 않는다). 계산에 쓰이는 열부터: 방향 · 전달 방법 · 조작 방식 · 자동화 인터페이스. 애매한 것만 수정 요청표로 되묻는다.
4. **확인**: `scripts\graph_view.bat` (적재한 그래프 3D) · `scripts\push.bat` (Fuseki).
5. **수정본을 받으면** 새 날짜 파일명으로 넣고 2번부터 — 같은 약칭은 날짜가 가장 늦은 파일만 적재되고, ID 는 그대로 유지된다.

알아 둘 것:
- 규칙에 안 맞는 파일명(인명·`(1)`·`최종` 등)은 `Tool조사_규칙밖_<해시>.xlsx` 로만 기록되고 파트를 모른다 — 이름을 고쳐 다시 적재.
- 읽을 수 없는 파일(암호·DRM·.xls·손상)은 건너뛰고 경고한다. 그 실행은 "안 보인 파트를 폐기" 판정을 하지 않는다.
- 설정만 고치고 코드는 손대지 않는다: `config\parts.yaml`(파트·담당 부서) · `config\rules.yaml`(시트 이름·선택지) · `config\header_map.yaml`(헤더 문구) · `config\value_aliases.yaml`.
- `data\real\`·`output\`·`fuseki-data\` 는 사내에만 둔다. 밖으로는 `diag.txt` 만.

## 6-1. 업데이트 받기 (zip 대신 텍스트 파일, 2026-09-30~)

GitHub `import-package` 브랜치의 `EnGenius_update_<이전>_to_<새>.py.txt` 한 개를 받아 반입 → 확장자를 `.py` 로 바꿔 아무 폴더에 두고:

```text
C:\EnGenius\engenius-tool-ontology\.venv\Scripts\python EnGenius_update_<이전>_to_<새>.py
```

바뀐 파일만 저장소에 쓰고, 원래 파일은 `offline\backup_<이전>_<일시>\` 에 남긴다. 적용 기록은 `offline\applied_updates.txt`.
저장소가 다른 경로면 명령 끝에 그 경로를 붙인다. 끝나면 `scripts\doctor.bat`.

## 7. 문제가 생기면 — 무엇을 밖으로 가져올 수 있나

밖(개발 PC)으로는 **값이 없는 것만**: `[NG]` 줄, `doctor` 출력, 경고의 **종류와 건수**, 파이썬 traceback 의 마지막 몇 줄.
셀 값·툴명·경로·인명·파일명은 옮기지 않는다. 적재마다 생기는 `output\<실행ID>\diag.txt` (또는 `scripts\diag.bat`) 가 딱 그것만 모아 준다.

## 8. 자주 걸리는 것

- `python` 이 3.10 이 아니거나 없음 → `scripts\env.bat` 의 `set PYTHON=py -3.10` 주석을 풀어 맞춘다.
- `.bat` 메시지가 영문인 이유: 한국어 Windows 의 cmd 가 .bat 을 cp949 로 읽어 한글이 깨지기 때문. 파이썬 출력은 한국어다.
- 포트 3030 이 이미 사용 중 → `scripts\fuseki_start.bat` 의 `--port` 를 바꾸고 `config\fuseki.yaml` 도 같이.
- `[NG] FUSEKI_HOME` / Java 없음 → `scripts\env.bat` 경로 확인. JDK 는 설치 프로그램이 아니라 zip 이라 관리자 권한이 필요 없다.
- PowerShell 실행 정책 오류는 `.ps1` 에만 해당 — 여기 스크립트는 전부 `.bat`.
- `.bat` 없이 직접 치고 싶으면 (PowerShell, 저장소 폴더에서): `$env:PYTHONPATH="src"` 한 뒤 `.venv\Scripts\python -m engenius_onto --help`.
  cmd 에서는 `set PYTHONPATH=src`. 이걸 빼먹으면 `No module named engenius_onto` 가 난다.
