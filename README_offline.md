# En-Genius 툴 온톨로지 — 사내(폐쇄망) 설치·실행 안내

연습용 패키지 v0.1 (2026-09-29) + 업데이트(6-1장). **M3.1 판(`1874bc7` 이후)부터 실데이터 적재 가능** — 6장.
그 전 판(`2d6e8c6`·`f3a4f55`)으로는 합성 데이터 연습만 한다 (양식 v1.1 을 못 읽고 인명 보호가 없다).

**받는 곳**: GitHub 비공개 저장소 `aerogyu/En-genius-Ontology` 의 **`import-package` 브랜치** — 파일을 하나씩 열어 `Download`(원본 받기).
큰 zip 은 Git LFS 로 올라가 있어 브랜치 전체 'Download ZIP' 으로는 알맹이가 안 받아진다 — 파일마다 받는다.

## 0. 이 패키지로 할 수 있는 것

- 파이썬 패키지를 인터넷 없이 설치하고 환경 점검(`doctor`)까지
- Fuseki(그래프 DB) 기동, 브라우저에서 SPARQL 화면 보기
- 저장소에 든 **합성 조사 파일 9개**로 적재(`load`) → 산출물 보기 → Fuseki 에 올리기(`push`) → 적재한 그래프를 3D 로 보기(`graph_view`)
- 실데이터 적재 (M3.1 판 `1874bc7` 이후 — 6장) → 수정 요청표·반출용 진단 요약(`diag.txt`)
- 업데이트 적용(6-1장)과 자기 점검(`selftest`, 6-2장)
- 못 하는 것: 연결 도출·보고서·연결 지도 (M4 에서 생김)

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

**서버가 필요한 것은 `push` 와 SPARQL 콘솔뿐이다** — `load`·`graph_view`·`diag`·`selftest` 는 서버 없이 된다. 그러니 이 단계는 건너뛰고 5장부터 해도 된다.

`scripts\fuseki_start.bat` 실행 — 창이 열린 채로 있어야 DB 가 살아 있다 (닫으면 종료). 브라우저에서 `http://127.0.0.1:3030` 을 열면
Fuseki 화면이 뜬다 (데이터셋 `engenius`). 이건 DBMS 관리 콘솔 같은 것 — SPARQL 을 직접 쳐 볼 수 있다.
DB 파일은 저장소 안 `fuseki-data\` 에 생긴다. 창이 곧바로 `[fuseki] server stopped` 로 끝나면 그 위 줄을 읽는다 (포트 3030 사용 중·`JAVA_HOME` — 8장).

## 5. 합성 데이터로 연습

1. `scripts\load.bat synthetic` (더블클릭하면 기본이 synthetic). 끝에 `load finished with rc=…` 와 실행 ID 가 찍힌다.
   - `rc=0` 정상, `rc=1` 경고·행 문제가 있어 파일로 남김(정상 범위 — 합성 데이터에는 일부러 문제 행이 있다), `rc=2` 중단.
2. `output\<실행ID>\` 를 연다 (실행ID 는 `20260928T101500` 같은 일시):
   - `survey.ttl` — 적재 결과 그래프 (텍스트, 메모장으로 열림)
   - `load_log.json` — 파일 목록(이름·sha256)·건수(`counts`)·제외 행(`excluded_rows`)·**경고 목록(`warnings`)**·스키마 위반(`schema_issues`)·
     툴 통합 후보·미해석 연계 툴·레지스트리 요약·SHACL 결과. 합성 데이터에는 일부러 넣은 문제 행이 있어 경고가 스무 건쯤 나오는 게 정상
   - `tool_review.csv` — 툴 통합 검토표 (HITL 입력: 엑셀로 열어 `판정(통합/별개)` 열을 채우면 `apply-review` 가 반영).
     **이 업데이트(2차 1묶음, 2026-10-02) 적용 뒤부터 6장 5번대로 돌린다 — 적용 전 판에서는 판정 열만 채워 둔다** (툴 통합 경로 수리, docs\11 3장 2번).
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
   - `diag.txt` — **반출용 진단 요약** (경고 종류·열·파트별 건수만, 값 없음). 첫 줄에 **설치 판**(`offline\installed_commit.txt` 앞 7자)이 같이 찍힌다 (2026-10-02 판부터).
   **2026-10-02 판(2차 1묶음)부터 적재 시작 전에 사내 설정(아래 3번의 `data\real\config\`)을 먼저 검사한다** — 형식이 틀리거나 값 없는 키가 있으면
   `[NG] 설정 오류: <파일> <키>: …` 한 줄만 찍고 멈춘다 (적재는 시작하지 않는다). 그 줄은 밖으로 가져가도 된다 (값 없음).
   **4차 수리(2026-10-02)부터**: YAML 문법이 틀린 파일도 `[NG] 설정 오류: <파일> <행>행 <열>열: YAML 문법 오류` 한 줄(값 없음)로 멈춘다 ·
   `--no-overlay` 와 `--overlay <폴더>` 를 같이 주면 거부한다 · 저장소 밖 오버레이 폴더를 썼으면 `load_log.json` 에 절대 경로로 적힌다 (사내용 파일이라 괜찮다).
   `제조사 접두 흡수` 는 **별개 판정 쌍이 든 그룹**이나 **기존 툴(활성 레지스트리)이 둘 이상 든 그룹**은 자동으로 합치지 않고 경고 + `tool_review.csv` 후보로 올린다 — 사람이 5번에서 판정한다(HITL).
   같은 판부터 새로 나오는 경고 종류: `툴 이름 범용/비어 있음`(자체개발·매크로처럼 툴 이름이 아닌 것 — 행별 `미상:<파트>/<Tool ID>` 툴로 두고 수정 요청표에 '툴 이름을 지어 주세요' 행) ·
   `제조사 접두 흡수`(`ANSYS Fluent` = `Fluent`) · `빈 값 표기 정수 칸`(`-`·`없음` 을 빈칸으로 봄) · `레지스트리 CSV 를 cp949 로 읽음` · `툴 별칭 순환` · `툴 별칭과 별개 판정이 충돌` ·
   `손으로 고친 merge_pairs`. 수정 요청표에도 두 종류가 는다: `툴 이름 범용/비어 있음` 과 **`입출력 없음`** — 뒤의 것은 **확인 요청**이다 (입출력이 정말 없는 툴이면 정상).
   담당자에게 보내기 전에 '확인 요청' 행을 같이 보낼지 빼고 보낼지는 Leo 가 정한다.
   **2026-10-12 판(2차 잔여)부터 확장자 칸**: `Excel(.xlsx)`·`Parasolid (.x_t)` 처럼 괄호 안에 `.확장자` 가 있으면 그 확장자를 쓰고(형식 이름은 버림), `Excel`·`Word`·`PowerPoint` 는 xlsx·docx·pptx 로 읽는다.
   `or`·`file`·`ascii`·`Parasolid`(단독)·`AP214`·숫자만 있는 말(`214`) 같은 확장자가 아닌 말은 `확장자 매핑 실패` 경고 · `model.stp` 처럼 파일 이름을 적은 칸은 새 경고 `확장자 다중 점 확인`(값은 그대로 씀).
   둘 다 수정 요청표에 `확장자 확인` 행으로 오른다. 칸이 인명처럼 보이면 경고에 값 대신 `[인명 유사 — 값 생략]` 이 찍힌다.
3. **드롭다운 대신 직접 적은 값**: 뜻이 분명한 것은 **`data\real\config\value_aliases.yaml`** 에 `열 이름: {적힌 값: 드롭다운 값}` 으로 적고 2번을 다시 한다
   (엑셀은 고치지 않는다). 계산에 쓰이는 열부터: 방향 · 전달 방법 · 조작 방식 · 자동화 인터페이스. 애매한 것만 수정 요청표로 되묻는다.
   **`data\real\config\` 는 사내 설정 오버레이** (2026-10-02 판부터, git 밖) — `load.bat real` 이 저장소 `config\` 위에 자동으로 덮어 읽는다. 파일 이름은 저장소와 같게
   (`value_aliases.yaml` · `tool_aliases.yaml` · `rules.yaml`). 합치는 법: `value_aliases` 는 열별로 더하고, `tool_aliases` 는 `aliases`·`distinct`·`merge_pairs` 를
   합집합으로, `rules` 는 키 단위로 덮는다 — 저장소 `config\` 는 손대지 않아도 되고, 업데이트가 `config\` 를 덮어도 사내 설정은 남는다.
   (합성 데이터나 `--input` 적재에서 쓰려면 `--overlay <폴더>` 를 붙이고, 끄려면 `--no-overlay`.)
4. **확인**: `scripts\graph_view.bat` (적재한 그래프 3D — 활성 툴만 그리고 통합·폐기 툴 수는 `(통합·폐기 N 제외)` 로 표시, 적재가 쓴 오버레이 `rules.yaml` 로 판정하면 '설정 오버레이 적용' 이 붙는다; 점을 드래그한 뒤 창 크기를 바꿔도 자리가 유지된다) ·
   `scripts\push.bat` (Fuseki — 그 실행에 `derived.ttl` 이 없으면 Fuseki 의 derived 그래프를 비운다. 옛 도출 결과가 남지 않게 하는 것이니 정상).
5. **툴 통합·별개 판정 (HITL)**: `output\<실행ID>\tool_review.csv` 의 '판정' 열에 `통합`/`별개` 를 적고(엑셀에서 그냥 Ctrl+S; '다른 이름으로 저장' 이면 CSV UTF-8 — cp949 로 저장돼도 읽는다)
   **`scripts\apply_review.bat` 에 `tool_review.csv` 를 끌어다 놓는다** (또는 cmd: `scripts\apply_review.bat output\<실행ID>\tool_review.csv`) → 2번을 다시 한다.
   (직접 치려면 먼저 `call scripts\env.bat` — 코드를 설치하지 않았으므로 PYTHONPATH 가 필요하다: `.venv\Scripts\python -m engenius_onto apply-review output\<실행ID>\tool_review.csv`)
   **이 업데이트(2차 1묶음, 2026-10-02) 적용 뒤부터 가능 — 적용 전 판에서는 돌리지 않는다** (판정 열만 채워 두면 된다).
   - 검토표가 실데이터 실행에서 나왔으면 판정은 **`data\real\config\tool_aliases.yaml`** 에 쌓인다 (저장소 `config\` 가 아니다 — 실 툴명이 들어가므로 사내 전용).
     다른 폴더에 쓰려면 `--config-dir <폴더>`; 그 폴더가 `data\real\config` 면 저장소의 공개 별칭(Excel=엑셀 등)과의 사슬 검사가 자동이고, 다른 폴더면 `--with-public-aliases` 를 붙여야 섞인다 (load 의 `--overlay <폴더>` 와는 다른 옵션).
   - 파일 안에서 **`merge_pairs: [[A 키, B 키], …]`** 가 판정 이력이다 (A 가 살아남고 A 의 TOOL ID 가 유지된다). `merge_keys` 는 apply-review 가 저장할 때마다 다시 계산하니
     손으로 고치려면 `merge_pairs` 를 고친다 (적재기도 `merge_pairs` 가 있으면 그것으로 계산하고 파일의 `merge_keys` 와 다르면 `손으로 고친 merge_pairs` 경고). `merge_keys` 만 있는 옛 파일은 그대로 읽힌다.
   - **`별개`** 는 이미 통합한 쌍이면 **직접 쌍만** 되돌린다. A–C 처럼 다른 키(B)를 거쳐 이어진 쌍은 `[NG]` 로 멈추고 **어느 파일의 `merge_pairs`/`aliases` 를 고칠지** 알려 준다 — 그 줄을 손으로 고친 뒤 다시.
   - '대표 이름' 은 판정 당시의 키에 라벨로 붙고, 그룹의 표시 이름은 적재기가 고른다 (키는 옮기지 않는다).
6. **수정본을 받으면** 새 날짜 파일명으로 넣고 2번부터 — 같은 약칭은 날짜가 가장 늦은 파일만 적재되고, ID 는 그대로 유지된다.
   **이 업데이트 뒤 첫 재적재에서 한 번만 바뀌는 것 (정상)**: 연도 토큰(`Excel 2016` = `Excel`)·토큰 치환(`C++`→`cpp`)·범용 제조사 접두 제외로 **키가 바뀐 툴은 TOOL ID 가 새로 나오고 옛 행은 폐기**된다;
   범용 이름(자체개발 등) 행이 있으면 툴 수가 **는다**(행별 `미상:` 툴); 입출력 없는 툴사용마다 수정 요청표에 '입출력 없음' 확인 행이 하나씩 붙는다. 두 번째 재적재부터는 안정된다.
   **2026-10-12 판 적용 뒤 첫 재적재**: `Excel(.xlsx)`·`Word` 같은 표기의 정규화 확장자가 바뀐다 (입출력 IO ID 는 원문 기준이라 그대로) · `확장자 매핑 실패` 가 늘 수 있고 `확장자 다중 점 확인` 이 새로 나온다 (정상).
   폴더에 `(1)` 사본·같은 내용 파일이 있었다면 이제 하나만 적재되어 툴사용 수가 줄 수 있다 · diag 첫 줄에 '같은 내용 N' 이 붙는다 (정상).

알아 둘 것:
- 규칙에 안 맞는 파일명(인명·`- 복사본`·`(최종)` 등)은 `Tool조사_규칙밖_<해시>.xlsx` 로만 기록되고 파트를 모른다 — 이름을 고쳐 다시 적재.
  load_log.json `files[].index` 가 입력 폴더 정렬 순번이라 해시 이름이 어느 파일인지 찾을 수 있다 (같은 내용 사본이 둘이면 둘째는 `…-2.xlsx`).
- **2026-10-12 판부터** 브라우저가 붙인 `(1)`·` (2)` 꼬리는 규칙 안 이름이다 — 사본 번호로 읽어 **같은 날짜면 번호가 큰 파일이 최신** (나머지는 '재발송으로 대체';
  내용이 같으면 끝에 '(내용 같음)'). 내용이 똑같은 파일이 둘이면 한 번만 적재한다 ('같은 내용 파일: X = Y (한 번만 적재)' — diag 의 '같은 내용 N').
  (사내 `data\real\config\rules.yaml` 에 `file_name_regex` 를 따로 적어 두었다면 사본 꼬리가 적용되지 않는다 — 그 키를 지우거나 저장소 `config\rules.yaml` 의 새 값을 옮긴다.)
- 경고 **'파일 간 같은 (파트, Tool ID)'**: 같은 파트의 같은 Tool ID 가 두 파일에 있다 (예: 묶음 파일 `MD` 와 따로 받은 `MDT` 파일, 규칙 밖 사본끼리). 둘 다 적재하되
  전용 파일(약칭 = 파트)이 아닌 쪽 행은 구분 키(`@MD`·`@file-<해시>`)로 따로 센다 — 같은 응답이 두 번 들어간 것이면 **옛 파일(묶음 파일·사본)을 폴더에서 빼고 다시 적재**.
  경고 **'규칙 밖 파일의 Tool ID 가 다른 파일과 겹침'**: 이름만 틀린 재발송·사본으로 보인다 — 파일명을 규칙대로 고치면 재발송 판정으로 하나만 적재된다.
- 읽을 수 없는 파일(암호·DRM·.xls·손상)은 건너뛰고 경고한다. 그 실행은 "안 보인 파트를 폐기" 판정을 하지 않는다.
- 설정만 고치고 코드는 손대지 않는다: `config\parts.yaml`(파트·담당 부서) · `config\rules.yaml`(시트 이름·선택지) · `config\header_map.yaml`(헤더 문구) ·
  사내 값은 `data\real\config\value_aliases.yaml`·`tool_aliases.yaml`(3·5번). `rules.yaml` 에 2026-10-02 판부터 새 키 세 개: `tool_token_map`(`C++`→`cpp` 등 토큰 치환) ·
  `generic_tool_names`(툴 이름으로 안 보는 말 — 자체개발·사내툴·매크로 등) · `candidate_min_contain_len`(포함으로 통합 후보를 올리는 최소 글자 수, 3). 사내에서 바꾸려면 `data\real\config\rules.yaml` 에 그 키만 적는다.
- **확장자 규칙을 사내에서 조정**하려면 `data\real\config\extensions.yaml` (2026-10-12 판부터 키 두 개 추가: `non_extension_tokens` 확장자가 아닌 말 · `compound_extensions` 묶음 확장자).
  `aliases` 는 키별로 합쳐진다 (예: `aliases: {parasolid: x_t}` 를 적으면 `Parasolid` 가 경고 대신 x_t — 별칭이 비확장자 목록보다 먼저).
  **목록 키(`non_extension_tokens`·`compound_extensions`·`inhouse_tokens`)는 통째로 바뀐다** — 저장소 `config\extensions.yaml` 의 기본 목록을 복사해 더한다.
  사내 형식명이 들어가므로 **사내 전용** (아래 '밖으로 가져가도 되는 설정' 에 넣지 않는다). 저장소 `config\extensions.yaml` 을 직접 고쳤다면 업데이트가 `.new` 로 남기니 오버레이로 옮긴다.
- **밖으로 가져가도 되는 설정은 `parts`·`rules`·`header_map`·`fuseki` 네 가지만** (값 없음). `tool_aliases.yaml`·`value_aliases.yaml`(오버레이)은 실 툴명·셀 값이 들어 있어 **사내 전용**.
- `data\real\`·`output\`·`fuseki-data\` 는 사내에만 둔다. 밖으로는 `diag.txt` 만.

## 6-1. 업데이트 받기 (zip 대신 텍스트 파일, 2026-09-30~)

GitHub `import-package` 브랜치의 `EnGenius_update_<이전>_to_<새>.py.txt` 한 개를 받아 반입 → 확장자를 `.py` 로 바꿔 아무 폴더에 두고:

```text
C:\EnGenius\engenius-tool-ontology\.venv\Scripts\python EnGenius_update_<이전>_to_<새>.py
```

바뀐 파일만 저장소에 쓰고, 원래 파일은 `offline\backup_<이전>_<일시>\` 에 남긴다. 적용 기록은 `offline\applied_updates.txt`.
저장소가 다른 경로면 명령 끝에 그 경로를 붙인다. 끝나면 **`scripts\selftest.bat`** (6-2장).

**2026-10-02 판부터 (`87881eb` 이후 업데이트 파일)** — 적용 스크립트가 하는 일이 늘었다:

- **설치 판 표식** `offline\installed_commit.txt` — 1행 설치된 커밋(전체 해시), 2행 커밋 번호. 업데이트가 끝에 쓰고, `selftest`·지원 요청(7장)이 읽는다.
  `doctor` 의 `[--] 설치 판 …` 줄과 `diag.txt` 첫 줄에도 앞 7자로 찍힌다 — 이 둘이 받은 업데이트의 `<새>` 와 같으면 적용된 것.
  파일이 없으면 첫 적용으로 본다 (`87881eb` 까지는 이 파일이 없었다 — 다음 업데이트가 만들어 준다).
- 사내 판정·값은 안전하다 — `data\real\config\`(6장 3·5번) 는 업데이트 파일에 들어 있지 않으니 덮이지 않는다. 저장소 `config\` 를 사내에서 고쳤다면 아래 '덮지 않는다' 규칙으로 `.new` 가 생긴다.
- **순서 검사** — 설치 판 번호가 업데이트 파일의 `<이전>` 보다 앞이면 `[주의] 중간 업데이트 누락`, `<새>` 보다 뒤면 `[주의] 역행` 을 묻는다 (`y/N`, 엔터 = N = 아무것도 안 바꿈).
  사이에 있으면 진행한다 (업데이트 파일은 누적이라 중간 판 위에도 적용된다) — 설치 판이 `<이전>` 과 다르면 `[..] 기준 판이 다르지만 사이 판 — 그대로 진행` 한 줄만 찍는다.
  묻지 않고 진행하려면 명령 끝에 `--yes`. 표식 1행은 메모장이 BOM 을 붙이거나 앞 7자리만 적혀 있어도 읽힌다.
- **사내에서 고친 파일은 덮지 않는다** — 업데이트 파일은 `<이전>`..`<새>` 사이 **모든 판**의 파일 내용(해시)을 알고 있다. 사내 파일이 그중 어느 판과 같으면 그냥 덮어쓰고(원본은 백업),
  어느 판과도 다르면(= 진짜 사내 수정, 예: `config\value_aliases.yaml`·`rules.yaml` 을 손본 경우) 그대로 두고 새 판을 **`<파일>.new`** 로 옆에 쓴 뒤
  `[주의] 로컬 수정이 있어 덮지 않음: <경로>` 를 찍는다. 두 파일을 비교해 손으로 합치고 **`.new` 는 지운다** (메모장·엑셀 비교 아무거나) — 지우지 않으면
  다음 업데이트가 그 `.new` 를 덮지 않고 `<파일>.new.<일시>` 를 하나 더 만든다(`기존 .new 보존`). 합치기 전까지는 옛 설정으로 돈다는 뜻이니 `[주의]` 줄은 꼭 처리한다.
  끝에 `[주의] 보존된 로컬 수정 N건` 으로 다시 알리고, 설치 판 표식은 그래도 `<새>` 로 올라간다 (코드 판은 올라갔으므로) — K 목록은 `MANIFEST.txt`·`applied_updates.txt` 에 남는다.
- **백업 폴더의 `MANIFEST.txt`** — 무엇을 어떻게 바꿨나: `A` 추가 · `M` 변경(원본은 그 폴더에) · `D` 삭제(그 폴더로 옮김) · `K` 로컬 수정 보존(`.new` 만 씀), 그리고 `<이전> -> <새>`·일시.
- **되돌리기** — `offline\backup_<이전>_<일시>\` 안의 파일을 저장소 같은 자리에 덮어쓰고, `MANIFEST.txt` 의 `A` 줄 파일은 지운다. 또는 개발 PC 에
  **역방향 업데이트**(`<새>_to_<이전>`)를 요청한다 — 같은 스크립트가 반대로 적용해 주고 표식도 되돌린다. `installed_commit.txt` 는 손으로 되돌린 경우 직접 고친다.
- 끝에 바뀐 파일 목록이 그대로 찍힌다 (어느 파일을 덮었는지 모르는 일이 없게).

## 6-2. 자기 점검 — `scripts\selftest.bat` (업데이트 뒤·문제가 생겼을 때)

더블클릭 → `doctor` → 합성 데이터 테스트 전체(`pytest`, 1~2분, Fuseki·Java 가 없으면 그 테스트만 건너뜀) → 결과를 두 파일에:

- `offline\selftest_<커밋>.txt` — **밖으로 가져가도 되는 것**: `PASS`/`FAIL`, 설치 판, `doctor` 줄, 통과·건너뜀 건수, **실패한 테스트 이름만** (값 없음)
- `offline\selftest_<커밋>.log` — 전체 출력 (사내에만 — 값이 섞일 수 있다)

`<커밋>` 은 `installed_commit.txt` 1행 앞 7자리 (없으면 `unknown`). 실데이터는 읽지 않는다 (저장소의 합성 파일만).

## 7. 문제가 생기면 — 무엇을 밖으로 가져올 수 있나

밖(개발 PC)으로는 **값이 없는 것만**: `[NG]` 줄, `doctor` 출력, 경고의 **종류와 건수**, 파이썬 traceback 의 마지막 몇 줄.
셀 값·툴명·경로·인명·파일명은 옮기지 않는다. 적재마다 생기는 `output\<실행ID>\diag.txt` (또는 `scripts\diag.bat`) 가 딱 그것만 모아 준다.

**외부 지원 요청의 표준 입력 (세 가지, 2026-10-02~)**: ① 설치 판 = `offline\installed_commit.txt` 1행 (앞 7자리면 충분) ② `offline\selftest_<커밋>.txt`
③ 가장 최근 `output\<실행ID>\diag.txt`. 이 셋이면 어느 판에서 무엇이 깨졌는지 값 없이 판단할 수 있다. 업데이트 적용 중 문제는 그 출력의 `[주의]`·`[NG]` 줄도 함께.
적재가 시작도 못 하고 `[NG] 설정 오류: <파일> <키>: …` 로 멈춘 경우는 그 한 줄이 곧 진단이다 (파일·키 이름만 있고 값은 없다). YAML 문법 오류의 `[NG] 설정 오류: <파일> <행>행 <열>열: YAML 문법 오류` 줄도 같다 — 파일 경로·행·열만 있고 값은 없다 (4차 수리, 2026-10-02).
`apply-review` 가 `[NG]` 로 멈춘 줄(간접 사슬·검토표 파일 형식 오류 등)도 키 이름만 있으니 가져와도 된다 —
단 실 툴명으로 된 키라면 이름은 지우고 "사슬 오류 1건" 처럼 종류만.

## 8. 자주 걸리는 것

- `python` 이 3.10 이 아니거나 없음 → `scripts\env.bat` 의 `set PYTHON=py -3.10` 주석을 풀어 맞춘다.
- `.bat` 메시지가 영문인 이유: 한국어 Windows 의 cmd 가 .bat 을 cp949 로 읽어 한글이 깨지기 때문. 파이썬 출력은 한국어다.
- 포트 3030 이 이미 사용 중 → `scripts\fuseki_start.bat` 의 `--port` 를 바꾸고 `config\fuseki.yaml` 도 같이. (기동 창은 서버가 멈추면
  `[fuseki] server stopped` 를 찍고 열린 채로 기다리므로 이유를 읽을 수 있다.)
- `[NG] FUSEKI_HOME` / Java 없음 → `scripts\env.bat` 경로 확인. JDK 는 설치 프로그램이 아니라 zip 이라 관리자 권한이 필요 없다.
- PowerShell 실행 정책 오류는 `.ps1` 에만 해당 — 여기 스크립트는 전부 `.bat`.
- `.bat` 없이 직접 치고 싶으면 (PowerShell, 저장소 폴더에서): `$env:PYTHONPATH="src"` 한 뒤 `.venv\Scripts\python -m engenius_onto --help`.
  cmd 에서는 `set PYTHONPATH=src`. 이걸 빼먹으면 `No module named engenius_onto` 가 난다.
  **그리고 `set PYTHONUTF8=1`** — 한국어 Windows 에서 이것이 없으면 파이썬이 한국어 YAML(스키마·설정)을 cp949 로 읽어 `UnicodeDecodeError` 가 나고
  selftest 3건(test_lint_clean·test_generated_files_up_to_date·test_help_subprocess)이 실패한다 (사내 2026-10-03). `.bat` 는 `env.bat` 이 알아서 켠다; `doctor` 가 `Python UTF-8 모드` 로 보여 준다.

## 9. 사내 AI 플랫폼에 붙이기 — Tool Ontology MCP 서버 (M6 v0, 2026-10-09)

플랫폼 에이전트가 이 온톨로지를 **도구**로 쓰게 하는 읽기 전용 MCP 서버. 플랫폼의 **En-genius MCP**(Office·CATIA 를 붙이는 로컬 프로그램)에
서버 하나를 더 등록하는 방식이다 — Leo PC 가 플랫폼에 먼저 접속하는 구조(아웃바운드)라 포트·방화벽 설정은 필요 없다 (docs/12).

**① 설치 (한 번)** — MCP 패키지 wheel 들을 `offline\` 아래에 두고 `scripts\install_mcp.bat` 더블클릭. wheel 은 **사내 whl 묶음에서 모은 것**이어도 된다
(Leo 2026-10-09: 사내 묶음 188개에 다 있음 — mcp 1.28.1 등 판이 조금 달라도 됨, mcp 1.x 면 동작). 둘 중 하나로 둔다:
`offline\wheels_mcp\` 폴더(안에 폴더가 한 겹 더 있어도 됨) 또는 `offline\wheels_mcp…zip` (bat 이 `offline\wheels_mcp\` 로 푼다).
bat 은 `mcp-1*.whl` 이 있는 폴더를 알아서 찾고, pydantic 처럼 이미 설치된 패키지는 `requirements.lock` 의 판으로 묶어 **올리지 않는다**.
`mcp` 와 의존 16개(전부 MIT/BSD/Apache/PSF)를 인터넷 없이 설치하고, 라이선스 점검과 도구 자기 점검까지 한다. 기존 패키지는 바꾸지 않는다.
끝에 `[OK] 도구 8/8 동작` 이 나오면 된다.

**② 언제든 점검** — `scripts\mcp_check.bat` (최신 실데이터 적재로 도구 8개를 한 번씩 부른다). 결과의 `[OK]/[NG]` 줄만 밖으로 가져올 수 있다.

**③ 브리지에 등록** — En-genius MCP 설정에 아래 한 묶음을 더한다 (형식은 플랫폼 개발자 답에 맞춘다 — 보통 `mcpServers` JSON):
```
이름     : engenius-tool-ontology
command  : C:\EnGenius\engenius-tool-ontology\.venv\Scripts\python.exe
args     : ["-X", "utf8", "C:\EnGenius\engenius-tool-ontology\scripts\mcp_server.py"]
전송     : stdio
```
JSON 이면 경로의 `\` 를 `\\` 로 두 번 쓴다 (예 `"C:\\EnGenius\\engenius-tool-ontology\\.venv\\Scripts\\python.exe"`). PYTHONPATH·env.bat 은 필요 없다 (`mcp_server.py` 가 알아서 찾는다).

**④ 에이전트 만들기** — 플랫폼에서 도구 `engenius-tool-ontology` 를 선택. 프롬프트 예:
"너는 연구소 툴 연결 분석 도우미다. 먼저 overview 로 파트 목록을 보고, 질문에 맞는 도구로 조사 결과를 찾아 표로 답한다.
조사표에 없는 내용은 지어내지 않고, 순위·후보는 잠정이며 판정은 엔지니어가 한다고 밝힌다."

**도구 8개** (전부 읽기 전용 — 쓰기·삭제 없음)

| 도구 | 하는 일 |
|---|---|
| `overview` | 규모(툴·툴사용·입출력)와 파트 목록 — 에이전트가 먼저 부른다 |
| `find_tool` | 이름 일부로 툴 찾기 (다른 표기·별칭 포함, 예 '엑셀' → Excel) |
| `tool_info` | 툴 하나 — 쓰는 파트별 용도·빈도·인원·조작 방식·자동화 IF·애로 구간·자동화 희망 |
| `part_tools` | 파트가 쓰는 툴 목록 |
| `tool_io` | 툴의 입력·출력 데이터 (분류·확장자·전달 방법·연계 툴) |
| `tool_partners` | 데이터를 주고받는다고 조사표에 **신고된** 상대 툴 (보냄/받음, 자기 신고/상대 언급) |
| `manual_handoffs` | 사람 손으로 옮기는 구간 원자료 (메일·수기 전달, 비고의 수기 신호) |
| `hub_candidates` | 툴 기준 에이전트 후보 순위 (잠정 — 3D 지도와 같은 순서) |

- 데이터는 **최신 실데이터 적재**(`output\<실행ID>\survey.ttl`)를 읽는다. 재적재하면 다음 호출부터 새 것을 읽는다 — 서버를 다시 켤 필요 없다. Fuseki 는 필요 없다.
- 답에는 실제 툴명·데이터명이 들어가 사내 LLM 으로 간다 (Leo 승인 2026-10-09). 자유 텍스트의 인명처럼 보이는 표기는 `[인명 추정 가림]` 으로 가린다.
- 확장자·분류로 계산한 연결과 착수 등급·순위는 M4 뒤 같은 서버에 도구로 더한다 — 도구를 늘려도 브리지 설정은 그대로다.
