# En-Genius 툴 온톨로지 — 반입 패키지 (연습용 v0.1, 2026-09-29, 커밋 `2d6e8c6`)

이 브랜치(`import-package`)는 코드가 아니라 **사내(폐쇄망)로 들여갈 파일 보관용**이다. 코드는 `main` 브랜치.
**합성 데이터 연습 전용** — 실데이터 적재는 M3.1(적재기 보강) 판을 다시 반입한 뒤. 그때는 저장소 zip 만 새로 받으면 된다.

## 받는 법

파일 이름을 눌러 들어가 **Download**(원본 받기). 큰 zip 은 Git LFS 라 브랜치 전체 'Download ZIP' 에는 알맹이가 없다 — 파일마다 받는다.
받은 뒤 체크섬 확인 (PowerShell): `Get-FileHash <파일> -Algorithm SHA256` → `SHA256SUMS.txt` 와 비교. cmd 면 `certutil -hashfile <파일> SHA256`.

| 파일 | 크기 | 용도 | 라이선스 | 출처 |
|---|---|---|---|---|
| `En-genius-Ontology-2d6e8c6.zip` | 0.7 MB | 저장소 — 코드·스키마·설정·합성 데이터·설치 스크립트·안내 | 사내 소유 코드 (의존성은 docs/04) | git archive 2d6e8c6 |
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

## 들여간 뒤

`README_offline.md` 순서대로: 저장소 zip 풀기 → wheels zip 을 `engenius-tool-ontology\offline\` 에 그대로 → JDK·Fuseki zip 을
`C:\EnGenius\tools\` 에 풀기 → `scripts\setup_offline.bat` 더블클릭 → `scripts\load.bat` (합성 데이터 연습).
연결 지도는 `maps\*.html` 을 Edge 로 바로 연다.
