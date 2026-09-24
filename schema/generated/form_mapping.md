<!-- 자동 생성 — 직접 고치지 말 것. 원본: schema/engenius_tool.yaml, 명령: python -m engenius_onto schema -->
# 양식 열 ↔ 스키마 슬롯 매핑표

스키마 v0.1.0 · 원본 양식 `SW조사양식_EnGenius_v1.0.xlsx` 기준. 열 문자는 **원본** 양식의 위치다 — 사내 배포본은 위치가 다를 수 있어 적재기는 헤더 이름으로 매핑한다 (docs/02 5장).

## SW기본정보 (32열 적재)

| 열 | 헤더 | 클래스.슬롯 | 범위 | 필수 |
|---|---|---|---|---|
| A | SW ID * | `ToolUsage.source_key` | string | 예 |
| B | SW명(정식) * | `ToolUsage.reported_tool_name` | string | 예 |
| C | 버전 * | `ToolUsage.version` | string | 예 |
| D | 제조사 / 개발주체 * | `ToolUsage.reported_vendor` | string | 예 |
| E | 구분 * | `ToolUsage.reported_kind` | ToolKind | 예 |
| F | 용도 대분류 * | `ToolUsage.purpose_class` | PurposeClass | 예 |
| G | 용도 상세 * | `ToolUsage.purpose_detail` | string | 예 |
| H | 주 사용 단계 * | `ToolUsage.phase` | DevPhase | 예 |
| I | 주요 사용 업무 요약 * | `ToolUsage.task_summary` | string | 예 |
| J | 담당 부서 * | `ToolUsage.usage_field` | ResearchField | 예 |
| L | 사용 인원수 | `ToolUsage.user_count` | integer |  |
| M | 사용 빈도 | `ToolUsage.frequency` | UsageFrequency |  |
| N | 라이선스 형태 | `ToolUsage.license_type` | LicenseType |  |
| O | 보유 수량 | `ToolUsage.license_count` | integer |  |
| P | 만료 시기 | `ToolUsage.license_expiry` | string |  |
| Q | 실행 환경 * | `ToolUsage.runtime_env` | RuntimeEnv | 예 |
| R | 폐쇄망 구동 * | `ToolUsage.airgap_ok` | AirgapSupport | 예 |
| S | 조작 방식 * | `ToolUsage.operation_mode` | OperationMode | 예 |
| T | 배치/스크립트 실행 * | `ToolUsage.batch_capable` | BatchCapability | 예 |
| U | 자동화 인터페이스 * | `ToolUsage.automation_if` | AutomationInterface | 예 |
| V | 자동화 상세 | `ToolUsage.automation_detail` | string |  |
| W | 헤드리스 실행 | `ToolUsage.headless` | HeadlessCapability |  |
| X | 인증/로그인 방식 | `ToolUsage.auth_method` | AuthMethod |  |
| Y | 산출물 주 저장 위치 | `ToolUsage.output_storage` | StorageLocation |  |
| Z | 사내 검증 상태 * | `ToolUsage.validation_status` | ValidationStatus | 예 |
| AA | 검증 기준/문서번호 | `ToolUsage.validation_ref` | string |  |
| AB | 감항·인증 업무 사용 * | `ToolUsage.certification_use` | YesNoUnknown | 예 |
| AC | 자동화 희망 작업 * | `ToolUsage.automation_wish` | string | 예 |
| AD | 현재 수작업·애로 구간 | `ToolUsage.pain_points` | string |  |
| AE | 우선순위 의견 | `ToolUsage.priority_opinion` | Priority |  |
| AF | 대체/업그레이드 계획 | `ToolUsage.roadmap_note` | string |  |
| AG | 비고 | `ToolUsage.note` | string |  |

## SW입출력 (12열 적재)

| 열 | 헤더 | 클래스.슬롯 | 범위 | 필수 |
|---|---|---|---|---|
| A | SW ID * | `IOSpec.owner_source_key` | string | 예 |
| C | 방향 * | `IOSpec.direction` | IODirection | 예 |
| D | 데이터/산출물 명칭 * | `IOSpec.data_name` | string | 예 |
| E | 분류 * | `IOSpec.io_category` | DataCategory | 예 |
| F | 파일 형식/확장자 * | `IOSpec.extensions_raw` | string | 예 |
| G | 포맷 표준성 | `IOSpec.format_standard` | FormatStandard |  |
| H | 데이터 성격 * | `IOSpec.data_nature` | DataNature | 예 |
| I | 전달 방법 * | `IOSpec.transfer_method` | TransferMethod | 예 |
| J | 연계 SW명 | `IOSpec.partner_raw` | string |  |
| K | 저장 위치/경로 | `IOSpec.storage_path` | string |  |
| L | 보안등급 | `IOSpec.security_grade` | SecurityGrade |  |
| M | 비고 | `IOSpec.note` | string |  |

## 의도적으로 적재하지 않는 열

| 시트 | 헤더 | 이유 |
|---|---|---|
| SW기본정보 | 실무 문의처(선택) | 인명 — 읽지도 저장하지도 않는다 (CLAUDE.md 절대 규칙 5) |
| SW입출력 | SW명(자동) | VLOOKUP 수식 열 — SW명은 SW ID 로 SW기본정보에서 찾는다 |

## 양식에서 직접 오지 않는 슬롯 (파생·해석·provenance)

| 클래스 | 슬롯 | 범위 | 설명 |
|---|---|---|---|
| ResearchField | `label` | string | 사람이 읽는 이름. RDF 에서는 @ko 언어 태그를 붙인다. |
| ResearchField | `status` | EntityStatus | 수명주기 상태. 삭제하지 않고 상태를 바꾼다 (상위 스키마 v0.2 §6). |
| ResearchField | `succeeded_by` | ResearchField | 통폐합·분할로 이 분야를 이어받은 분야. |
| Tool | `label` | string | 사람이 읽는 이름. RDF 에서는 @ko 언어 태그를 붙인다. |
| Tool | `status` | EntityStatus | 수명주기 상태. 삭제하지 않고 상태를 바꾼다 (상위 스키마 v0.2 §6). |
| Tool | `pref_label` | string | 대표 이름. |
| Tool | `alt_labels` | string | 조사에서 나온 변형 표기들 (CQ10). |
| Tool | `vendor` | string | 제조사/개발주체 — 사용 기록들의 응답 중 다수값 (엇갈리면 검토표에 표시). |
| Tool | `kind` | ToolKind | 구분 — 사용 기록들의 응답 중 다수값. |
| Tool | `merged_into` | Tool | 사람 판정으로 다른 Tool 에 통합된 경우 그 대상 (status=통합됨과 함께). |
| DataCategory | `label` | string | 사람이 읽는 이름. RDF 에서는 @ko 언어 태그를 붙인다. |
| ToolUsage | `label` | string | 사람이 읽는 이름. RDF 에서는 @ko 언어 태그를 붙인다. |
| ToolUsage | `source_row` | integer | 원천 엑셀 시트의 행 번호 (조사 보완 시 원본 행을 찾기 위한 추적 정보). |
| ToolUsage | `loaded_in` | SurveyLoad | 이 노드를 만든 적재 기록 (provenance). |
| ToolUsage | `usage_tool` | Tool | 통합된 Tool (reported_tool_name 을 정규화해 결정). |
| ToolUsage | `user_count_raw` | string | 사용 인원수 원문 — 정수 변환에 실패했을 때만 보존 (경고와 함께). |
| ToolUsage | `license_count_raw` | string | 보유 수량 원문 — 정수 변환에 실패했을 때만 보존 (경고와 함께). |
| ToolUsage | `feeds` | ToolUsage | (파생) 이 툴사용이 데이터를 공급하는 툴사용 — Feed 의 지름길, 경로 질의(eg:feeds+)용. derived 그래프에만 있다. |
| IOSpec | `label` | string | 데이터/산출물 명칭 (data_name 과 같게 둔다). |
| IOSpec | `source_row` | integer | 원천 엑셀 시트의 행 번호 (조사 보완 시 원본 행을 찾기 위한 추적 정보). |
| IOSpec | `loaded_in` | SurveyLoad | 이 노드를 만든 적재 기록 (provenance). |
| IOSpec | `io_owner` | ToolUsage | 이 입출력을 가진 툴사용 (owner_source_key 로 찾은 것). |
| IOSpec | `extensions` | string | 정규화한 확장자 목록 (소문자, 점·별표 제거, 별칭 적용). 연결 계산 키 ② (docs/02 6.2). |
| IOSpec | `inhouse_format` | boolean | 확장자 원문에 '(사내)'·'사내' 표기가 있었는지. |
| IOSpec | `partner_tools` | Tool | 연계 SW명 중 Tool 로 해석된 것. |
| IOSpec | `partner_unresolved` | string | 연계 SW명 중 Tool 로 해석하지 못한 이름 — 조사 누락 후보 (CQ09). |
| Feed | `label` | string | 사람이 읽는 이름. RDF 에서는 @ko 언어 태그를 붙인다. |
| Feed | `from_io` | IOSpec | 공급 측 출력 명세. |
| Feed | `to_io` | IOSpec | 수요 측 입력 명세. |
| Feed | `supplier` | ToolUsage | 공급 측 툴사용 (from_io 의 io_owner). |
| Feed | `consumer` | ToolUsage | 수요 측 툴사용 (to_io 의 io_owner). |
| Feed | `matched_category` | DataCategory | 양쪽이 일치한 분류. |
| Feed | `matched_extensions` | string | 양쪽이 겹친 정규화 확장자. |
| Feed | `confidence` | FeedConfidence | 겹친 확장자가 전부 범용(config rules.yaml generic_extensions)이면 낮음. |
| Feed | `declared` | boolean | 어느 한쪽의 신고(연계 SW명)와 일치하는지 (docs/02 7.2). |
| Feed | `transfer` | TransferMethod | 양쪽 명세의 전달 방법. |
| Feed | `manual` | boolean | 수기 구간 여부 (전달 방법 기준). |
| Feed | `manual_basis` | ManualBasis | 수기 판정 근거 — 전달방법, 또는 비고 키워드만 있는 보조 신호. |
| Feed | `grade` | StartGrade | 착수 등급 (수기·변환 구간에만 매긴다, docs/02 7.4). |
| Feed | `rule_version` | string | 이 파생 노드를 만든 규칙 버전 (예 feed_v1). |
| Feed | `derived_from` | SurveyLoad | 파생의 근거가 된 적재 기록 (provenance). |
| Feed | `generated_at` | datetime | 파생 노드 생성 일시 (provenance). |
| SurveyLoad | `label` | string | 사람이 읽는 이름. RDF 에서는 @ko 언어 태그를 붙인다. |
| SurveyLoad | `run_id` | string | 적재 실행 ID (output/<실행ID> 와 같다). |
| SurveyLoad | `source_file_name` | string | 원천 파일명 (경로 제외). |
| SurveyLoad | `source_sha256` | string | 원천 파일 SHA-256 (소문자 16진수). |
| SurveyLoad | `loaded_at` | datetime | 적재 일시. |
| SurveyLoad | `row_count` | integer | 적재한 행 수 (두 시트 합). |
| SurveyLoad | `excluded_row_count` | integer | 제외한 행 수 (예시 행·빈 행 등, 사유는 실행 로그). |
| SurveyLoad | `warning_count` | integer | 적재 중 경고 수 (내용은 실행 로그). |
