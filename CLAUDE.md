# En-Genius 툴 온톨로지 (오픈소스 트랙)

한화에어로스페이스 엔진 개발 AI 플랫폼 En-Genius의 첫 온톨로지 구축 저장소.
연구소 24개 분야의 툴 조사(274건)로 **툴 간 데이터 연결을 계산**하고, **사람 손으로 이어진 구간**을 찾아 Tool Agent 개발 대상을 데이터로 고른다.
최종 산출물은 사내 폐쇄망에 반입해 실제 데이터로 돌릴 **스키마·코드·질의 묶음**이다. 이 PC에서는 합성 데이터로 만들고 검증만 한다.

## 절대 규칙

1. **실제 조사 데이터·사내 문서·사내 툴 상세는 이 PC에 두지 않는다.** 개발과 테스트는 전부 합성 데이터로 한다. 실데이터로 보이는 내용이 들어오면 작업 전에 멈추고 확인한다.
2. 합성 데이터에는 공개 상용 툴 이름(CATIA, ANSYS Fluent 등)이나 가상의 이름만 쓴다. 사내 툴명·경로·문서번호·인명을 지어내지 않는다.
3. 실행 환경은 **인터넷이 없는 폐쇄망**이다. 런타임에 외부 네트워크·클라우드·CDN·원격 모델을 호출하지 않는다. 모든 의존성은 오프라인 wheel로 설치 가능해야 한다.
4. 의존성은 최소로, **허용형 라이선스(Apache·MIT·BSD 계열)만** 쓴다. AGPL·GPL 라이브러리 금지. 새 패키지는 `docs/04_반입목록.md`에 라이선스와 함께 추가한다 (반입 심사 비용이 크다).
5. 인명은 저장하지 않는다. 양식의 '실무 문의처' 열은 적재하지 않는다.
6. 에이전트는 판정하지 않는다. 최종 판단은 엔지니어(HITL).
7. `data/real/`은 git에 올리지 않는다 (`.gitignore`에 등록돼 있음).

## 확정된 결정 (재논의하지 않음 — 근거는 `docs/01_배경과_결정사항.md`)

- 스키마: **LinkML** (마스터, Git 형상관리). Protégé는 생성된 OWL을 보는 검토용 뷰어.
  **사내에도 반입한다** (사내에서 스키마 수정·생성 — Leo 2026-09-24). 단 전이 의존 `rfc3987`(GPLv3+)
  은 설치하지 않는다 — jsonschema 가 `rfc3986-validator`(MIT)로 대체하며 결과 동일 실측
  (`docs/04` 부록 C). `python -m engenius_onto licenses` / `tests/test_license_guard.py` 가 감시한다.
- 그래프 저장소: **Apache Jena Fuseki** (TDB2). 6.2.0 은 Java 21, 5.6.0 은 Java 17 — 사내 Java 에 맞춰
  고른다 (둘 다 같은 설정으로 M0 테스트 통과, `docs/04`). 개발 PC: `C:\EnGenius\tools\` (git 밖).
- 로컬 처리: rdflib (LinkML 의존성으로 설치됨), 엑셀: openpyxl·pandas.
- 에이전트 단계(M6부터): **LangGraph + MCP 공식 Python SDK + langchain-mcp-adapters**. LLM은 사내 제공(OpenAI 호환 API 가정, 설정으로 교체).
- W3C 표준(RDF·SPARQL·OWL·SHACL)만 사용 — 저장소 교체 가능성을 유지한다.
- 지멘스 Graph Studio PoC는 별도로 진행 중이다. 이 저장소는 벤더와 무관한 플랜 B이며, PoC 산출물(OWL/TTL)도 받을 수 있어야 한다.

## 문서 안내 (필요할 때 읽는다)

- **`docs/08_인수인계.md` — 새 세션은 이것부터** (지금 어디까지 왔나, 환경 살리기, 다음 작업, 함정 기록)
- `docs/01_배경과_결정사항.md` — 왜 이렇게 정했나, 무엇을 검토 후 제외했나
- `docs/02_툴온톨로지_설계.md` — 클래스·연결 규칙·질의·보고서 명세 **← 구현 전 필독**
- `docs/03_작업계획.md` — 마일스톤 M0~M6과 완료 기준
- `docs/04_반입목록.md` — 반입 SW·라이선스·오프라인 설치 절차
- `docs/05_스키마_v0.1_검토.md` — M1 검토 기록, 결정 D1~D8 (전부 승인)
- `docs/06_합성데이터_골든.md` — M2 합성 데이터·골든 기대값. **규칙 세부의 정본은 `tests/golden/expected.yaml` interpretations I1~I33** (docs/02 13장)
- `docs/07_적재_M3.md` — M3 적재 파이프라인: 명령·산출물·모듈·설정·스키마 v0.2·검증 기록
- `docs/09_M3_검토_수리계획.md` — M3 독립 검토 28건(반박 0)·수리 계획·작업 순서·Leo 결정 질문 **← M3.1 정본**
- `docs/10_파트_단위_조직.md` — 조직 단위 = 파트 설계 (승인, **파일 20·파트 21 확정** — 숫자 정본 3-1, 목록 `config/parts.yaml`, 파일명 약속 5장)
- `docs/12_플랫폼_MCP_등록_문의.md` — 사내 AI 플랫폼에 온톨로지 MCP 서버를 등록하기 위한 문의 초안(A~E 15문항)·답에 따른 설계 갈래·답 기입란 **← M6 입력**
- `docs/11_검토_지도_구축현황_2026-10-01.md` — 1차 실데이터 적재 뒤 6관점 독립 검토(반박 검증 통과 21건)·개선안 14건·Leo 결정 질문 Q1~Q8 **← M3.1 2차·M4 착수 전 참고**
- `README_offline.md` — **사내(폐쇄망) 설치·실행 안내** (연습용 패키지 v0; 더블클릭 `scripts\*.bat`, 산출물 읽는 법, 밖으로 가져올 수 있는 것). 패키지 조립·검증 기록은 `docs/04` 6장
- `schema/engenius_tool.yaml` — 스키마 마스터. 고친 뒤 `python -m engenius_onto schema` (생성물 드리프트는 `--check`·테스트가 잡음)
- `reference/양식_명세.md` — 조사 양식의 모든 열·안내·드롭다운 (원본 양식에서 자동 추출)
- `reference/SW조사양식_EnGenius_v1.0.xlsx` — 원본 양식 (합성 데이터 생성의 틀)
- `reference/엔진개발_지식스키마_v0.2.md` — 상위 스키마 원칙 (URI 정책, 조직 노드, provenance, 보안)

## 관련 저장소 (2026-10-23) — 각 작업은 그 폴더를 연 세션에서

| 저장소 | 무엇 | 상태 |
|---|---|---|
| `C:\EnGenius\engenius-workflow-ontology` (GitHub `aerogyu/En-genius-Workflow-Ontology`) | 개념설계 워크플로 온톨로지 — 분야별 YAML 을 손으로 쓰고 build 가 TTL·계약 JSON Schema·그림. 이 저장소의 툴을 TOOL ID 로 참조(읽기만, 4술어) | W0·W1 완료, ★Leo 확인 ① 중 |
| `C:\EnGenius\engenius-data-inventory` (GitHub `aerogyu/En-genius-Data-Inventory`) | 조직 자료 보유 현황 1차 조사(파트 21) — 양식 생성기·취합 검사기. 이 저장소의 `config/parts.yaml` 을 읽는다(같은 부모 폴더) | 양식 v0.2 초안 게시, Leo 확인 대기 |
| `C:\EnGenius\HAS-En-Genius-MCP-Factory` (org 저장소, 브랜치 dev/4) | 플랫폼 MCP 서버 모음 — 이 저장소의 MCP 서버를 얇은 어댑터로 붙일 곳 | 별도 세션 |

**이 저장소는 2026-10-19 부터 잠시 쉼** (Leo — 워크플로 온톨로지·자료 조사 먼저). 다시 시작하면: 사내 `a3e4e0f_to_d50da9e` 적용·재적재 diag 확인 → **M4** (설계는 Fable 권장).
이 저장소의 `config/parts.yaml` 은 자료 조사 저장소가 읽으므로 약칭을 바꾸면 그쪽도 확인한다.

## 현재 상태

- [x] M0 환경·골격 (2026-09-24 — help 동작 / Fuseki 6.2.0·5.6.0 에 engenius 데이터셋 기동 / pytest 21 통과·skip 0)
- [x] M1 스키마 v0.1 (Leo 확인 ① 2026-09-24) — lint 0·매핑 누락 0·HermiT 일관·Jena SHACL 실행 테스트, pytest 67. 결정 D1~D8 권장안 승인 (`docs/05`)
- [x] M2 합성 데이터·골든 (2026-09-24 — 분야별 xlsx 8 + 재발송 이전 파일 1·골든 I1~I33·독립 참조 계산, 독립 재계산 불일치 0, Leo 결정 3건 반영 후 pytest 157. `docs/06`)
- [x] M3 적재 파이프라인 (2026-09-24 — 스키마 v0.2(파생 3종), `load`·`push`·`apply-review`·`template-examples`, 골든 적재 층 전부 일치·입출력 77/툴사용 34 참조 계산과 건별 일치, Pydantic=SHACL 5건, 재적재 ID 불변, rdflib·Fuseki 일치, pytest 180. `docs/07`)
- [~] **M3.1 적재기 보강** — **1차 완료 (2026-09-30, `1874bc7`)**: 양식 v1.1·파트 단위(MD 묶음)·스키마 v0.3·안전장치(#4~#9·#11·#13·#18~#24)·
  value_aliases·수정 요청표·diag → **실데이터 적재 가능**. 사내 반입은 텍스트 업데이트 파일(`scripts/build_update.py`, README_offline 6-1) —
  **`EnGenius_update_f3a4f55_to_4423d92.py.txt` (Leo 적용 확인) → `EnGenius_update_4423d92_to_62114a9.py.txt` (3D 뷰어 v4) 를 import-package 에 올림 (2026-09-30). 이어서 `EnGenius_update_62114a9_to_630ec66.py.txt` (3D 뷰어 v6, import-package 9df9fdb). 이어서 `…630ec66_to_f1a2a08` (검토용 diag 확장 + 뷰어 v7, import-package 79194c4). → `…f1a2a08_to_9bc1ac6` (실데이터 실행 우선, import-package e08dc8b). → `…f1a2a08_to_1cbd4ee` (파트 약칭만, 9bc1ac6 포함). → `…f1a2a08_to_94403db` (뷰어 v10, **테스트 1건 실패 상태로 올림 — 쓰지 말 것**) → `…f1a2a08_to_87881eb` (v10 + 연도 표기 통합 수리, import-package be3caec). 87881eb 사내 적용 확인 (Leo 2026-10-02) → `…87881eb_to_a3e4e0f` (M3.1 2차 1묶음, import-package 62a0025) → **a3e4e0f 사내 적용 확인 (Leo 2026-10-08, selftest 3건 실패 = UTF-8 모드)** →
  `…a3e4e0f_to_dd6a94a` (UTF-8 모드 수리, import-package 8db6731) → **`…a3e4e0f_to_7a092e1` + `wheels_mcp_win_amd64_cp310.zip`(LFS) (M6 v0 MCP 서버 + ID 이어받기, import-package 982d764) 올림 2026-10-09**
  — Leo 적용 확인되면 다음은 `--from 7a092e1`. 사내 흉내 리허설(a3e4e0f 복사본 + mcp 없는 새 venv, PYTHONUTF8 없음): 적용 → install_mcp 17개 → 합성 적재 → mcp_check 8/8 → 브리지식 stdio 왕복 통과.
  업데이트 파일은 이제 사이 판 sha 집합(KNOWN)을 품어 어느 사이 판에든 적용되고, 사내 로컬 수정은 `.new` 로 보존한다 (build_update.py, pytest 게이트 내장). 업데이트는 파일을 통째로 쓰므로 옛 기준에서 만든 것도 새 기준 위에 적용 가능 (삭제 파일 없을 때).
  **1차 적재 검토 (2026-10-01~02, `docs/11`)**: diag 는 반출 불가 → 6관점 독립 검토(반박 검증 통과 21건)·개선안 14건·Leo 결정 Q1~Q4 (docs/11 8장).
  분야별 툴사용 합 277 vs 적재 282 → Leo 가 diag 파트별 표와 대조해 차이 나는 파트만 알려 주기로 (답 대기).
  **2차 1묶음 완료 (2026-10-02, `a3e4e0f`)** — docs/11 3장 1·2·3·6·8·9·10·13·14 + 지도 v11: 설정 오버레이 `data/real/config/`(C15)·apply-review 수리(#2·#14·#15·#16·C2,
  merge_pairs 정본·제조사 접두 흡수 Q3(a)·범용 이름 행별 Q3(b))·#21 2단·'입출력 없음' 수정 요청·push derived 비움·설치 판 표식·selftest.bat·apply_review.bat·KNOWN 업데이트.
  독립 검토 4라운드(적대적 재검토) 뒤 pytest 285·skip 3(Fuseki 미기동). 골든 aggregates 불변. **적용 뒤 첫 재적재에서 TOOL ID·툴 수가 1회성으로 바뀔 수 있음(정상)**.
  **2차 잔여 완료 (2026-10-12, Leo "잔여 전부", 작은 결정 전부 권장안 — docs/09 0장·각 # '수리 결과 (2026-10-12)')**: 6묶음 `f6ca669`(#10 확장자 + 공통 인명 가림 `Loader._q`)·
  `f855acb`(#1 잔여: '(n)' 사본·같은 내용 한 번만·파일 간 같은 (파트, Tool ID) 구분 키 I36)·`2f650fe`(#3 예시 유사 행)·`d8be811`(#21 만료 시기·'영구'·자동화 판정 통일·header_map 오버레이·엑셀 층 신호 I37)·
  `430b398`(#17 연계SW 미해석 검토 행·partner_missing·#25d·별칭 미적용·#15(4) 레지스트리 엑셀 손상 복원)·`5e92e97`(#25b `parts.yaml renamed_from`·동시 적재 잠금 `.load.lock`·같은 초 두 실행)
  → 5관점 적대적 검토 17건 수리 `450beeb` → 재검토 9건 `3f668cd` → 재검토 6건 `d50da9e` (17→9→6, 마지막은 드문 입력뿐이라 멈춤). pytest 581·skip 3, 골든 aggregates 불변.
  **#25c(LOAD ID 패턴)는 M4 스키마 v0.4 로**. **사내 반입**: `EnGenius_update_a3e4e0f_to_d50da9e.py.txt` (import-package `93057bb`, a3e4e0f 이후 어느 판에든 —
  a3e4e0f·988405d 복사본 리허설 통과: 적용 → TO 와 파일 일치 → selftest 581 → 합성 적재·diag·지도·mcp_check 8/8). **Leo 적용 확인되면 다음은 `--from d50da9e`**.
  남은 것(작음·Leo 결정 필요): C8·N1 — 인명 유사 값이 Tool ID·노드 키 칸에 들어가면 load_log·survey.ttl·레지스트리에 원문이 남는다(diag 엔 없음) ·
  점 없는 형식명 앞 확장자('x_t(.x_b)')를 남길지 · 한셀/LibreOffice 저장본 수용 시험(사내) · MD 묶음+분할 파일 동시 수신 시 대체할지.
  M4 설계 반영 사항은 docs/11 3장 4·7·11번 + 5장 Q1·Q4~Q7 (Handoff declared/confidence·automatable 슬롯·ToolCandidate·part_code·'모름' 미확인 표시·폐쇄망 폐지 커밋 범위에 스키마 enum 포함).
  이전 문구: (`docs/09` — 독립 검토 28건 수리, 결정 13건 전부 권장안 승인 2026-09-28; 수리 전 실데이터 적재 금지)
  + **묶음 T: 양식 v1.1 + 파트 단위 조직 반영** (`reference/양식_v1.1_변경분.md` 5장 — 시트명 설정화(#13)·header_map·스키마 v0.3·예시 행 갱신·v1.1 합성 파일 추가;
    `docs/10` — FLD = 파일명 약칭(`config/parts.yaml`)·'담당 부서' 는 분류 속성 domain('기타' 허용)·분할은 succeeded_by;
    `diag` 명령 — 셀 값 없이 경고 종류별 건수만 담은 반출용 진단 요약, docs/08 8장)
- [ ] M4 연결 도출·질의·보고서 (Leo 확인 ②) — M3.1 뒤 (보고서에 툴 연결 지도 HTML 포함 — Leo 요청 2026-09-24)
- [ ] M5 반입 패키지 — **연습용 v0 만듦 (2026-09-28, Leo 요청 "먼저 반입해 직접 해보겠다")**: `requirements.lock`(90) · `offline/wheels`(93, win_amd64·cp310, 55MB, antlr4 는 sdist 로 빌드) ·
  더블클릭 `scripts\setup_offline.bat`·`doctor.bat`·`load.bat`·`push.bat`·`env.bat` · `README_offline.md`. 검증: 깨끗한 복사본에서 .bat 흐름(설치→doctor→합성 적재 34/77) +
  옛 pip 21.2.4(사내 3.10.2 동봉판) 에뮬레이션 오프라인 설치 통과. 코드는 설치하지 않고 `PYTHONPATH=src` 로 실행(설치하면 `config/` 를 못 찾음 — config.py REPO_ROOT).
  정식 M5 는 M4 뒤 (M3.1·M4 코드로 저장소 zip 만 재반입; wheel·JDK·Fuseki 는 그대로).
  **v0.1 (2026-09-29)**: GitHub **`import-package` 고아 브랜치**(zip 4개 Git LFS, 314 MB)에 올림 — Leo 가 거기서 파일마다 받는다. 조립 `scripts/build_package.py`,
  wheels 는 zip 한 개로(setup 이 자동 해제), 연결 지도 2개 동봉. 패키지에서 푼 그대로 설치·합성 적재 검증 (docs/04 6장).
  **사내 반입·설치 성공 (Leo 2026-09-30)** — 1~6단계(설치·Fuseki·합성 적재·push·SPARQL) 통과. 같은 날 적재 그래프 3D 뷰어
  `scripts\graph_view.bat` 추가, 저장소 zip `f3a4f55` 를 브랜치에 더함 (사내 갱신 = 풀어서 덮어쓰기)
- [~] **M6 에이전트 준비 — v0 MCP 서버 완료 (2026-10-09, Leo 승인 "그 정도로 시작")**: 사내 AI 플랫폼(자체 에이전트·LLM, En-genius MCP 브리지)에 붙일
  **stdio MCP 서버** `scripts/mcp_server.py` = `python -m engenius_onto mcp` (`mcp==1.30.0` FastMCP, 읽기 전용 도구 8개: overview·find_tool·tool_info·part_tools·
  tool_io·tool_partners·manual_handoffs·hub_candidates). 질의 층 `onto_store.py` 는 3D 뷰어와 같은 정의(순위 행 단위 일치 테스트), 최신 실데이터 survey.ttl 을 rdflib 로
  (Fuseki 불필요·재적재 자동 반영), 모든 칸 인명 유사 표기 가림. 반입 = `wheels_mcp_win_amd64_cp310.zip`(새 wheel 17, 11.4 MB, 전부 허용형, pydantic 그대로) + `install_mcp.bat`·`mcp_check.bat`.
  **Windows 함정**: stdio 의 stdin 동기 읽기 중 도구 스레드의 C 확장 첫 import(numpy) 영구 대기 → 시작 때 warm_up. LangGraph·langchain 은 보류(플랫폼이 에이전트를 가짐).
  **사내 설치 (Leo 2026-10-09)**: .whl 반입 대신 **사내 whl 묶음(188개)** 사용 — mcp 1.28.1 (판 조금 다름, 1.28.1 로 테스트 통과). install_mcp.bat 을 판·폴더 구조 무관하게 고침,
  MCP 의존은 lock 에서 뺌(선택 설치, `-c requirements.lock` 으로 기존 패키지 고정). 표준 라이브러리 서버는 보관 브랜치 `mcp-stdlib` (82b48e3) — SDK 를 못 쓰게 되면 대안.
  Leo 가 심사 우회('편하다')를 말했으나 바이너리를 텍스트로 감싸는 반입은 하지 않기로 함.
  **실제 연결 성공 (Leo 2026-10-09)**: 플랫폼(LocalLLM Studio)에 '로컬 명령' 방식(실행 명령 = .venv python, 인자 한 줄씩 `-X`/`utf8`/scripts\mcp_server.py)으로
  MCP 서버 연결 → 프롬프트 에이전트가 실데이터로 질문에 잘 답함. 다음: 답 품질 점검(도구 결과와 대조), 여럿 공유는 HTTP/SSE 방식(같은 SDK, 인바운드 확인 필요).
  **후속 업데이트 (2026-10-09)**: `…7a092e1_to_7145c76` (install_mcp.bat 사내 묶음 대응, import-package e66bbf9) → `…7145c76_to_988405d`
  (hub_candidates 를 툴로 묶은 순위로 — LLM 이 툴사용 행을 다시 매겨 지도와 순위가 달랐음, import-package 947bc90). **Leo 적용 확인되면 다음은 `--from 988405d`**.
  설계 원칙: 순위·합계 같은 집계는 서버가 끝내 주고 LLM 은 전달만 (도구 설명에 '다시 매기지 말 것').
  **다음 세션 할 일**: ① Leo 확인 — 988405d 적용·재연결 뒤 '툴 기준 후보 상위 10' 이 지도 순서와 같은지, 개인 PC 점검표(답 대조·지어내기·도구 선택·인명·재적재 반영·속도·**실제 묻고 싶은 질문 목록**)
  ② 미회신 3 파트 회신 → 재적재 → diag 숫자 (이어받기로 'SW ID 없는 내용 행 50' 감소 확인, 277 vs 282) ③ ~~M3.1 2차 잔여~~ (2026-10-12 완료 — 사내 반입 `a3e4e0f_to_d50da9e`; 적용 뒤 재적재 diag 로 새 경고 종류·수정 요청 행 증가 확인, 자동화 IF 'NA' 반영으로 MCP·지도 순위 변화 확인) → **M4**(멈추고 Leo 확인 ②)
  ④ M4 뒤 HTTP/SSE 공유 서버(띄울 곳·인바운드·토큰) — 플랫폼은 'HTTP/SSE 주소' · '로컬 명령(인자 한 줄씩)' 두 방식 지원 확인됨.
  **플랫폼 MCP 서버 모음 저장소 (2026-10-12)**: Leo 가 org 저장소에 초대됨 — 작업 브랜치 dev/4(Leo 개발용, Tool Ontology·SANTA·AutoCAD MCP 등을 거기서 개발해 main 에 합칠 계획),
  clone `C:\EnGenius\HAS-En-Genius-MCP-Factory` (Python 3.13 venv). 온톨로지 MCP 는 그쪽 `mcp_server/servers/ontology/` 에 **얇은 어댑터**(fastmcp + 그 저장소 net.run_server)로 붙이고
  본체(onto_store·도구 로직)는 이 저장소가 정본. 그 작업은 **그 폴더의 별도 세션**에서 (훅·스킬·폴더 CLAUDE.md 가 세션 폴더 기준) — 인계는 그 프로젝트의 Claude 메모리.
  주의: Leo 가 채팅에 사내 툴명을 적은 적 있음 — 저장소·메모리에 기록하지 않는다.
  남은 것: M4 뒤 계산 연결·착수 순위·경로 도구 추가. README_offline 9장 · docs/12 5장.

마일스톤을 끝낼 때마다 이 체크리스트와 아래 '미확정 사항'을 갱신한다.

## 저장소 구조 (계획)

```
schema/          LinkML 스키마와 생성물(OWL·SHACL·문서)
src/engenius_onto/  적재·정규화·도출·보고서 코드 (python -m engenius_onto ...)
rules/           도출 규칙 SPARQL CONSTRUCT (버전 붙임: feed_v1.rq)
queries/         역량 질의 SPARQL SELECT (cq01~)
config/          헤더 매핑, 규칙 값, 확장자 사전, 툴 별칭, Fuseki 설정
data/synthetic/  합성 조사 파일과 그 레지스트리
data/real/       (git 제외) 사내에서만 사용
output/          실행 결과 (TTL, 보고서 xlsx, 실행 로그)
tests/           pytest, 합성 데이터 골든 결과
offline/         반입 패키지 (wheels 등)
```

## 코드 규칙

- Python 3.10+. 표준 라이브러리 우선 (HTTP는 `urllib`, 유사도는 `difflib`).
- 엑셀은 **열 위치가 아니라 헤더 이름**으로 매핑한다 (`config/header_map.yaml`). 실제 사내 양식은 분야 24개, 분류 추가 등으로 원본과 다르다.
- 규칙에 쓰이는 값(수기 전달 값, GUI 전용 값, 범용 확장자 등)은 `config/rules.yaml`에 둔다. 사내에서 코드 수정 없이 조정할 수 있어야 한다.
- ID는 의미 없는 일련번호나 해시다 (`TOOL-000001`, `USE-000001`). 사람이 읽는 이름은 `rdfs:label`/`skos:prefLabel`에 `@ko`로 둔다.
- 파생 결과는 derived named graph에 따로 두고, 매번 전체 재계산하며, provenance(규칙 버전, 원천 적재 ID, 생성일)를 남긴다.
- 모든 기능은 **로컬 백엔드(rdflib)와 Fuseki 백엔드 양쪽**에서 같은 결과를 내야 한다. SPARQL은 표준 1.1 문법만 쓴다.
- 스크립트는 Windows·Linux 양쪽에서 돈다 (pathlib, `python -m` 진입점, 필요하면 .bat/.sh 모두 제공).
- 테스트는 pytest + 합성 데이터 골든 결과. 외부 네트워크 없이 통과해야 한다.
- 코드 식별자는 영문, 주석·문서·레이블은 한국어.

## Leo와 일하는 방식

- 한국어로 소통한다.
- **구조 먼저.** 큰 구현 전에 설계를 짧게 제안하고 확인받는다. 특히 M1(스키마)·M4(결과)·M6 착수 전에는 반드시 멈춘다.
- 주장은 보수적으로 한다. 불확실한 것은 불확실하다고 적는다.
- Leo는 SAS(2차유로) 도메인 엔지니어로 파이썬에 능숙하고, 시맨틱웹은 입문 단계다. 개념은 DB 비유로 설명한다 (스키마=ERD, Fuseki=DBMS, 적재=ETL, SPARQL=SQL, 에이전트=앱).
- 변경은 버전(v0.1, v0.2 …)으로 쌓는다.

## 미확정 사항 (Leo에게 확인)

- ~~사내 PC/서버의 OS~~ → **Windows 11 64비트 확정** (2026-09-28; wheel 은 win_amd64 · cp310). ~~파이썬 버전~~ → **3.10.2 확정**
  (2026-09-24; 개발 venv 는 3.10.11). 사내 라이브러리는 요청하면 대부분 추가된다.
- ~~실제 양식의 헤더·드롭다운 변경분~~ → **양식 v1.1 받음** (2026-09-28, `reference/Tool조사양식_EnGenius_v1.1.xlsx` ·
  변경분 `reference/양식_v1.1_변경분.md`). 시트명 전부 변경·열 2개 삭제·1개 추가·선택지 4개 변경 → **M3.1 묶음 T 로 반영**.
  ~~실제 24개 분야(담당부서) 목록은 아직 안 받음~~ → 파트 단위로 대체 (docs/10, 파일 20·파트 21).
- ~~Fuseki를 띄울 위치~~ → **우선 개인 PC** (2026-09-28; 서버 없음, 나중에 이전 가능 — 설정만 바꾸면 됨)
- ~~사내 Java 버전~~ → Leo 로컬 PC 에 Java 없음 → **JDK 21 zip 반입 + Fuseki 6.2.0 확정** (2026-09-24, docs/04)
- 사내 LLM API 형식 (M6 전). **사내 AI 플랫폼 활용 (Leo 2026-10-03)**: 플랫폼에서 LLM 을 골라 쓰고 **프롬프트로 에이전트를 직접 만들 수 있다** →
  이 온톨로지를 거기에 연결하고 싶어 함. **이번 적재(수정 요청 회신 → 재적재) 마무리 뒤에 논의** (Leo). 그때 물을 것: 플랫폼 에이전트가 도구(함수 호출·MCP·HTTP)를 부를 수
  있는가 · Leo PC 의 Fuseki(127.0.0.1:3030)에 닿을 수 있는가(아니면 서버 이전) · 파일/표 첨부로 지식을 넣는 방식인가 · 프롬프트 길이 제한. 방향 후보: ① 플랫폼이 도구를 지원하면
  M6 의 MCP 함수(docs/02 CQ 템플릿)를 그대로 노출 ② 도구 없으면 M4 보고서·질의 결과를 **플랫폼에 넣을 텍스트/표로 내보내는 명령**(`export`)을 M4 산출물에 추가. M6 의 LangGraph 계획은 플랫폼 능력을 본 뒤 조정.
- ~~다음 세션 시작 때 Leo 에게 받을 것~~ → **Leo 답 (2026-10-08)**: ① selftest 실패 3건 = `test_lint_clean`·`test_generated_files_up_to_date`·`test_help_subprocess`
  → 원인 **Python UTF-8 모드 꺼짐**(개발 PC 는 사용자 env `PYTHONUTF8=1`, 사내 cp949) — env.bat `set PYTHONUTF8=1`·doctor 줄·tests/conftest.py 로 수리 (docs/08 6장).
  ② a3e4e0f 적용·재적재 rc 0, **툴 183 → 186** ③ 툴 이름 범용/비어 있음 **6**, 제조사 접두 흡수 0, 보류 0 ④ 지도 v11·실데이터 확인 ⑤ 277 vs 282 는 모름(재적재 뒤)
  ⑥ **'입출력 없음' 툴사용 74건** — 수정 요청에 포함해 담당자들에게 보냄, 회신 취합 뒤 재적재 ⑦ 재적재 뒤 diag 숫자 알려 주기로.
  **회신 반영 재적재 (Leo 2026-10-09, 회신 안 온 2 파트 제외)**: 툴사용 272 · 입출력 430(고아 41) · 툴 180 · 파트 20 · 제외 행 166 · 경고 316 · 범용 이름 0.
  apply-review rc 0 이나 통합·별개 0건(판정 열 미기입 추정). 확인할 것: 빠진 2 파트 파일을 폴더에서 뺐는지(→ 그 파트 폐기) · 고아 41·제외 행 166 의 경고 종류별 건수.
  Leo 질문 'A → 엑셀(공용 템플릿) → B' 는 연결이 끊기나 → 답: 파일 형식(xlsx)은 노드가 아니라 Feed 의 근거, A→B 로 이어짐(분류+확장자 일치, 범용 확장자는 신뢰도 낮음, 연계 Tool명이 있으면 신고).
  사람이 엑셀 앱에서 손으로 옮기면 A→Excel→B 로 Excel 툴사용이 끼며 그 구간이 수기 착수 후보 — M4 에서 경로 질의로 2단 연결도 찾는다.
  **재적재 (Leo 2026-10-09 오후)**: 회신 1건이 '수정사항만 적은 엑셀'이라 재요청, 그 파트는 예전 파일로 → 툴사용 284 · 입출력 442(고아 41) · 툴 183 · **파트 21** · 제외 행 202 · 경고 354.
  수정 요청 파트별 건수: 회신 준 파트 대부분 1~2건, **미회신 3 파트가 220·41·68건** (남은 문제는 거의 이 3 파일). 파트 20 이었던 것은 그 엑셀에 양식 시트가 없어서('시트 없음 2').
  경고 상위: 선택지 밖 120(→ value_aliases) · SW ID 없는 내용 행 50(→ 'ID 이어받기' 제안, Leo 결정 대기) · 고아 41.
  **M6 v0 설계 제안함 (2026-10-09)**: stdio `python -m engenius_onto mcp` + mcp_server.bat, 기본 rdflib 로 최신 실데이터 survey.ttl, 읽기 전용 도구 7개
  (find_tool·tool_info·part_tools·tool_io·tool_partners·manual_handoffs·hub_candidates; 자유 SPARQL 제외) — Leo 확인 3가지 대기(도구 목록·실 툴명이 사내 LLM 으로 가도 되는지·ID 이어받기).
  **사내 AI 플랫폼 (Leo 2026-10-08)**: 플랫폼 에이전트가 **도구를 부를 수 있고 Leo 개인 PC 의 도구도 부를 수 있다 — 단 MCP 서버 연결 필요**, Fuseki 에 닿는다.
  → M6 = **온톨로지 MCP 서버**(공식 `mcp` Python SDK, 읽기 전용 도구 = docs/02 CQ 템플릿; Fuseki 또는 rdflib 로컬) — "Fuseki MCP" 범용이 아니라 우리 질의 함수를 도구로. 확인할 것:
  플랫폼이 요구하는 전송(stdio 로컬 프로세스 / HTTP(streamable·SSE) URL)·인증·등록 방법, 서버를 Leo PC 에서 상시 띄울지.
  **플랫폼 구조 (Leo 2026-10-08)**: 웹 플랫폼(개발자 개인 PC 가 서버, 사내 IP — 저장소에 적지 않음)에서 프롬프트 + 도구 선택으로 에이전트 생성, 에이전트끼리 연결 가능.
  각 사용자 PC 에서 **'En-genius MCP' 라는 로컬 프로그램**을 켜면 Office·CATIA 등 로컬 도구가 플랫폼 에이전트에 붙는다(플랫폼 개발자가 묶어 둔 MCP 서버들); 논문 검색(RAG)은 서버 쪽 도구.
  → 제안: **온톨로지 MCP 서버는 '한 곳'(플랫폼 서버 또는 Leo PC)에 HTTP 로 띄우고 모두가 공유** — 사용자는 Fuseki 를 깔지 않는다. 데이터는 그 서버의 Fuseki 하나(또는 TTL 파일 + rdflib).
  플랫폼 개발자에게 물을 것: 원격(URL) MCP 서버 등록 가능 여부 / 아니면 En-genius MCP 묶음에 우리 서버를 포함하는 방법 / 서버 쪽 도구로 올릴 수 있는지.
  **접속 방향 확인 (Leo netstat, 2026-10-08): 아웃바운드** — 브리지가 플랫폼에 접속해 유지(LISTENING 없음). 1차 M6 형태 = **stdio MCP 서버를 En-genius MCP 묶음에**, 데이터는 Leo PC(처음엔 Leo 혼자). 플랫폼 '서버' 는 아직 개발자 개인 PC — 서버 배치 질문은 정식 서버가 생길 때. 문의 핵심 = 브리지 설정 형식 (docs/12 4장). `mcp` 와 전이 의존(anyio·httpx·httpx-sse·pydantic-settings·sse-starlette·starlette·uvicorn 등, MIT/BSD)
  wheel 반입은 docs/04 에 추가 (M6 착수 때). **적재 마무리(회신 → 재적재) 뒤 M4 와 함께 설계.**
- D1 구체화 — 착수 등급을 Reconciliation 이 아니라 착수 구간 클래스 `Handoff` 에 둠 (docs/07 3장, M4 확인 때)
- ~~M3.1 결정 질문 묶음~~ → **13건 전부 권장안 승인** (2026-09-28, `docs/09` 3장 머리). L1~L4 착수 가능.
- ~~조직 단위 = 파트 설계~~ → **승인** (Leo 2026-09-28, `docs/10` Q1~Q5: 설계 예 · 정식 이름·담당 부서 매핑 기입(`config/parts.yaml`) ·
  실제 파일 '담당 부서' 열은 드롭다운 10개 + 목록 밖 파트는 '기타' (**데이터는 고치지 않는다** — 분류는 parts.yaml) · 조직 코드 GitHub 보관 OK ·
  CD·FEM 분할 파일 받은 뒤 첫 적재). 2026-09-30: 연료윤활기어박스 = **GBLB**, 형상설계(CD)는 **파일 하나 안에서 Tool ID 로 MDT-1~9·MDC-1~8 로 나뉘어** 옴 →
  파일명 약칭은 **MD** (묶음) → M3.1 T: `parts.yaml file_bundles` — 한 파일의 행을 Tool ID 접두어로 파트(FLD) 배정 (파일은 손대지 않음). **파일명 약속 확정표 = `docs/10` 5장**. Tool ID 숫자 앞 0(MDC-1 = MDC-01)은
  #18 에서 같은 ID 로 보고 경고.
  **드롭다운 대신 직접 적은 값** (Leo 2026-09-30 — 실제 파일에 많음, '기타+비고' 안내를 안 따름): 원문은 그대로 두고(D4) '선택지 밖' 경고 →
  M3.1 T 에 **`config/value_aliases.yaml`(열별 '적힌 값 → 드롭다운 값')** 추가 제안 — 사내에서 엔지니어가 채우고 재적재. 규칙에 쓰이는 열
  (방향·전달 방법·조작 방식·자동화 인터페이스)은 매핑 전엔 연결·등급 계산에서 빠질 수 있으니 경고를 열별로 모아 보여 준다.
  Leo 계획: 첫 적재 후 담당자들에게 일괄 수정 요청 → 제안: 적재 때 **파트별 수정 요청표**(`output/<실행>/fix_requests/<약칭>.xlsx` — 시트·행·열·문제·안내,
  사내에서만 씀)를 같이 만든다 (M3.1 T) MDT=터빈·MDC=압축기 확인, FEM 은 분할 없이 한 단위(담당자 2명, Leo 2026-09-30). 전기전자제어 = **CSD**, FEM 정식 이름 기입 — **약칭 전부 확정** (파일 20 · 파트 21)
- ~~스키마 미결 D1~D8~~ → 전부 권장안 승인 (2026-09-24). ~~제출 형식~~ → 분야별 파일, 파일명에 분야명만(인명 없음). SW ID 는 분야별 `약칭-번호` 통일 재요청 예정
- ~~툴 기준 후보 Q1~Q3~~ → **결정 (Leo 2026-09-30, docs/02 7.5 머리)**: 단위 = 툴사용(파트×툴, 합산 안 함) · 정렬 1순위 = 연결 상대 수 ·
  연결 수 두 열(전체 / 신고된 것만). M4 착수 (Leo "바로 M4로 가자"). 3D 뷰어 간격을 데이터 수에 맞춰 자동으로 넓히기 (Leo "너무 촘촘")
- (기록) **툴 기준 에이전트 후보 (허브)** — Leo 요청 2026-09-29 "수기 전달 말고도 연결 많은 툴 위주로도 선정". 제안: `docs/02` 7.5 — 수기 구간 착수 순위는
  그대로 두고 **툴 단위 두 번째 목록** 추가 (정렬: 자동화 가능 → 연결 상대 툴 수 → 걸린 수기·비고 구간 수 → 닿는 분야 → 빈도 → 인원). 확인할 것:
  Q1 단위(툴 합산) · Q2 정렬 순서 · Q3 범용 확장자 연결 처리('신고된 연결만' 열). 시안 = 3D 지도 '툴 기준 후보' 버튼. 확인되면 M4 에서 구현·골든 추가
- ~~폐쇄망 구동 불가 → 착수 등급 '제외'~~ → **폐지** (Leo 2026-09-29: "대부분의 툴은 폐쇄망 구동이라 제외하면 안 된다"). v1.1 에 열도 없다.
  **M4 에서 반영**: `rules.yaml airgap_excluded: []`, oracle·골든 재등급 — 제외 2행(STR-04→STR-02, STR-03→STR-04)이 **A** 로 바뀌어
  착수 순위 A 9·B 3·C 1·제외 2 → **A 11·B 3·C 1** (스크래치 계산), 사례 P12·GRADE-SUPPLIER-X 를 '폐쇄망 값은 등급에 영향 없음' 으로 개정,
  expected_head decisions 에 기록. 폐쇄망 값은 v1.0 파일에 있으면 속성으로만 보존(지도 점선 표시는 선택)
- ~~M2 골든 확인 질문 3건~~ → 결정 (2026-09-24, `expected_head.yaml` decisions): Q-R1 최신 파일만 적재 (I33), Q-D2 연계 SW 를 적은 수기 행은 적힌 상대에게만 (I32 — '우선 그렇게 해보자', 운영 중 재검토), Q-I3 비고 신호 구간도 착수 순위에 종류 '비고' (I3 개정)
- ~~docs/11 검토 결정 질문 Q1~Q8~~ → **Leo 결정 (2026-10-02)**: Q1 권장(범용 확장자+연계 SW 공란 추정 수기 구간은 같은 등급 안에서 뒤로, 착수 순위 시트에
  신고 여부·신뢰도 열) · Q2 87881eb 적용됨, **apply-review 미실행·value_aliases 미기입** (함정 ①② 아직 안 밟음 — 다음 업데이트에 수리) · Q3 제조사 접두 흡수 **예**,
  '자체개발' 류 범용 이름은 **그룹 규칙 없이 파트에 이름 짓기를 요청** (수정 요청표 행으로; 그때까지 행별로 별개 툴) · Q4 권장((a) 원문 열 + (b) '미확인' 표시) ·
  Q5~Q8 은 권장안 그대로. **분야별 툴사용 수(Leo 제공, 값 아님)**: 4·7·6·12·3·26·15·25·41·10·9·8·3·10·19·32·8·12·9·8·10 = **277** — 적재 282 와 5 차이
  (원인 확인 중: diag 파트별 표의 '툴사용' 열과 대조). 합성 재현(지도·규모 테스트)은 이 분포를 쓴다.
- **실행 GUI 여부** (Leo 질문 2026-09-28 "CLI 말고 GUI 로 만들 수 있나") — **M4 보고서·연결 지도를 본 뒤 결정** (Leo 동의 2026-09-28,
  **로컬 웹 UI 선호**). CLI 는 엔진으로 유지하고 얇은 GUI 를 위에 얹는 방향. 후보: ① 표준 라이브러리 `http.server` 로컬 웹 UI(127.0.0.1,
  연결 지도 HTML 과 같은 기술, 반입 추가 0) ② Tkinter 창. Streamlit·Gradio·PySide 등 외부 프레임워크는 반입 부담·런타임 외부 호출 위험으로 제외.
  Leo 는 CLI 적재에 부담을 느낀다 — GUI 와 별개로 M5 에 **더블클릭 .bat(doctor·load·report) + 한국어 설치·실행 안내**를 넣는다.
  **추가 요청 (2026-09-30)**: GUI 에서 트리플을 **만들고 고치기** (조사 엑셀 밖의 지식 — 나중에라도). 방향 제안(미확정): 적재 원본(survey 그래프)은
  건드리지 않고 사람이 넣은 것은 별도 named graph `manual` 에 쌓는다 (재적재해도 안 지워짐, 도출은 survey ∪ manual 로 재계산) · 저장 전 SHACL 검증 ·
  provenance 는 일시·사유만 (인명 저장 금지, 규칙 5) · 폼은 스키마(LinkML) 슬롯에서 생성. GUI 결정 때 같이 설계
