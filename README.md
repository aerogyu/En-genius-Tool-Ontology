# En-Genius 툴 온톨로지 — 반입 패키지 (연습용 v0.1, 2026-09-29, 커밋 `2d6e8c6`)

이 브랜치(`import-package`)는 코드가 아니라 **사내(폐쇄망)로 들여갈 파일 보관용**이다. 코드는 `main` 브랜치.
**합성 데이터 연습 전용** — 실데이터 적재는 M3.1(적재기 보강) 판을 다시 반입한 뒤. 그때는 저장소 zip 만 새로 받으면 된다.

## 받는 법

파일 이름을 눌러 들어가 **Download**(원본 받기). 큰 zip 은 Git LFS 라 브랜치 전체 'Download ZIP' 에는 알맹이가 없다 — 파일마다 받는다.
받은 뒤 체크섬 확인 (PowerShell): `Get-FileHash <파일> -Algorithm SHA256` → `SHA256SUMS.txt` 와 비교. cmd 면 `certutil -hashfile <파일> SHA256`.

| 파일 | 크기 | 용도 | 라이선스 | 출처 |
|---|---|---|---|---|
| `En-genius-Ontology-2d6e8c6.zip` | 0.7 MB | 저장소 — 코드·스키마·설정·합성 데이터·설치 스크립트·안내 (첫 반입본) | 사내 소유 코드 (의존성은 docs/04) | git archive 2d6e8c6 |
| `En-genius-Ontology-f3a4f55.zip` | 0.7 MB | 저장소 — 위 + 적재한 온톨로지 3D 뷰어(`scripts\graph_view.bat`) · doctor Java 확인 수정 (2026-09-30 추가) | 사내 소유 코드 | git archive f3a4f55 |
| `EnGenius_update_f3a4f55_to_4423d92.py.txt` | 1.3 MB | **업데이트 (최신, M3.1 1차 — 실데이터 적재 가능)**. f3a4f55 가 설치된 사내 PC 용. 확장자를 `.py` 로 바꿔 실행 → 바뀐 47개 파일만 씀, 원래 파일은 `offline\backup_…` 에 남김 | 사내 소유 코드 | git f3a4f55..4423d92 |
| `wheels_win_amd64_cp310.zip` | 56.9 MB | 파이썬 패키지 wheel 93개 (Windows x64 · Python 3.10) — 풀지 말고 저장소의 offline\ 에 | Apache·MIT·BSD 계열 (docs/04 부록 A) | PyPI (antlr4 4.9.3 은 sdist 를 빌드) |
| `OpenJDK21U-jdk_x64_windows_hotspot_21.0.12.1_1.zip` | 205.1 MB | Java 21 (Temurin JDK) — Fuseki 실행용 런타임 | GPLv2 + Classpath Exception | https://github.com/adoptium/temurin21-binaries/releases |
| `apache-jena-fuseki-6.2.0.zip` | 51.4 MB | Apache Jena Fuseki 6.2.0 — 그래프 DB | Apache 2.0 | https://dlcdn.apache.org/jena/binaries/ |
| `maps/preview_map.html` | 41 KB | 툴 연결 지도 2D (합성 데이터) — 브라우저로 바로 열림 | — | scripts/preview_map.py |
| `maps/preview_map3d.html` | 39 KB | 툴 연결 지도 3D (합성 데이터) — 드래그 회전·휠 줌 (**3D v1**, 회의용) | — | scripts/preview_map3d.py |
| `maps/preview_map3d_v2.html` | 47 KB | 툴 연결 지도 3D **v2** — v1 + '툴 기준 후보' 순위표·'연결 수로 크기' (2026-09-29 추가) | — | scripts/preview_map3d.py (main `9136272`) |
| `README_offline.md` | 8 KB | 사내 설치·실행 안내 (저장소 zip 안에도 있음) | — | — |

JDK·Fuseki 는 공급자 원본 그대로다 — 반입 심사에서 원 출처에서 직접 받기를 요구하면 위 출처에서 같은 파일을 받아 체크섬이 같은지 보면 된다
(공급자 체크섬: 저장소 `docs/04_반입목록.md` 1장).

## 판 기록 (덮어쓰지 않는다)

이 브랜치의 산출물은 **덮어쓰지 않는다** (Leo 2026-09-29). 새 판은 판 번호나 커밋이 붙은 **새 파일**로 더하고, 이 표와 파일 표에 한 줄씩 추가한다.
`SHA256SUMS.txt` 는 산출물 줄을 지우지 않고 더한다 (안내문인 README.md 줄만 새 값으로 바뀐다). 지나간 판도 git 이력에 그대로 남는다.

| 날짜 | 판 | 더한 파일 | 내용 |
|---|---|---|---|
| 2026-09-29 | 패키지 v0.1 | 저장소 zip `2d6e8c6` · wheels · JDK · Fuseki · 지도 2D v1 · 3D v1 | 연습용 첫 판 (합성 데이터) |
| 2026-09-29 | 지도 3D v2 | `maps/preview_map3d_v2.html` | '툴 기준 후보' 버튼 — 연결 많은 툴 순위표(행 클릭 = 그 툴의 모든 사용처·연결 강조), '연결 수로 크기' 토글. 제안 시안 (docs/02 7.5, Leo 확인 대기) |
| 2026-09-30 | 저장소 `f3a4f55` | `En-genius-Ontology-f3a4f55.zip` | **적재한 온톨로지 3D 뷰어** `scripts\graph_view.bat` (최신 `output\<실행ID>\survey.ttl` → `graph3d.html`, 골든 계산이 아니라 적재 그래프 그대로) · doctor 가 JAVA_HOME 의 Java 를 찾음. **사내 갱신: 풀어서 기존 `engenius-tool-ontology` 에 덮어쓰기** (`.venv`·`output`·`fuseki-data` 는 zip 에 없어 그대로 남는다 — 재설치 불필요) |

| 2026-09-30 | 업데이트 `f3a4f55 → 4423d92` | `EnGenius_update_f3a4f55_to_4423d92.py.txt` | **M3.1 1차** — 양식 v1.1 읽기 · 파트 단위(MD = MDT+MDC 분할) · 스키마 v0.3 · 인명 보호 · 병합 셀·깨진 파일·빈 행 안전장치 · 드롭다운 대응표(`config\value_aliases.yaml`) · 파일별 수정 요청표 · 반출용 `diag.txt`. **zip 대신 텍스트 한 개** (Leo 요청). 적용법은 아래 '업데이트 적용' |

| 2026-09-30 | 업데이트 `4423d92 → 62114a9` | `EnGenius_update_4423d92_to_62114a9.py.txt` | **3D 뷰어 v4** (`scripts\graph_view.bat`) — 파트 층·툴 층 2층 배치, 데이터 수에 맞춘 간격, 파트별 색·구슬·빛. 4423d92 적용한 곳용 (파일 4개) |

## 업데이트 적용 (zip 대신 텍스트, 2026-09-30~)

1. `EnGenius_update_<이전>_to_<새>.py.txt` 를 받아 반입 → 확장자를 `.py` 로 바꿔 **아무 폴더**에 둔다.
2. cmd: `C:\EnGenius\engenius-tool-ontology\.venv\Scripts\python EnGenius_update_<이전>_to_<새>.py` (저장소가 다른 곳이면 끝에 그 경로)
3. `[OK] 업데이트 … 추가 7 · 변경 40` 이 나오면 끝. 원래 파일은 `offline\backup_<이전>_<일시>\`, 기록은 `offline\applied_updates.txt`. 이어서 `scripts\doctor.bat`.
   `<이전>` 은 지금 사내에 설치된 판이다 — 이번 파일은 `f3a4f55` 가 설치된 곳용 (두 번 돌려도 '이미 같음' 으로 끝난다).

## 들여간 뒤

`README_offline.md` 순서대로: 저장소 zip 풀기 → wheels zip 을 `engenius-tool-ontology\offline\` 에 그대로 → JDK·Fuseki zip 을
`C:\EnGenius\tools\` 에 풀기 → `scripts\setup_offline.bat` 더블클릭 → `scripts\load.bat` (합성 데이터 연습).
연결 지도는 `maps\*.html` 을 Edge 로 바로 연다.
