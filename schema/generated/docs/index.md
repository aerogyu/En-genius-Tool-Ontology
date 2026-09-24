# En-Genius 툴 온톨로지

연구소 분야별 SW 조사(SW기본정보·SW입출력)를 담아 툴 간 데이터 연결을 계산하기 위한 스키마. 설계 기준은 docs/02_툴온톨로지_설계.md (3·4·7장). 클래스 7종: Field, Tool, ToolUsage, IOSpec, DataCategory, Feed(파생), SurveyLoad. ID 는 의미 없는 일련번호·해시(egid:TOOL-000001 등), 사람이 읽는 이름은 rdfs:label(@ko). 언어 태그(@ko)는 LinkML 이 데이터로 표현하지 못하므로 적재기(M3)가 RDF 를 만들 때 붙인다. 예약(미구현): WbsTask —uses_tool→ ToolUsage/Tool (지멘스 PoC 의 WBS Lv.6 연결).

URI: http://en-genius.local/onto/

Name: engenius_tool



## Classes

| Class | Description |
| --- | --- |
| [DataCategory](DataCategory.md) | 데이터 분류 (SW입출력 '분류' 드롭다운 값) |
| [Derived](Derived.md) | 규칙으로 계산한 파생 노드의 provenance 묶음 (docs/02 8장) |
| [Feed](Feed.md) | (파생) 규칙으로 계산한 공급 연결 — 출력 명세 from_io 와 입력 명세 to_io 의 분류가 같고 정규화 확장자가 겹칠 때 (doc... |
| [IOSpec](IOSpec.md) | SW입출력 1행 |
| [ResearchField](ResearchField.md) | 연구소 분야 (조직 노드, RDF 클래스 eg:Field — docs/02 용어) |
| [SurveyLoad](SurveyLoad.md) | 적재 기록 1건 — 원천 조사 파일 1개를 한 번 적재한 것 |
| [Tool](Tool.md) | 제품 단위 툴 (표기 변형을 통합한 것) |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |



## Slots

| Slot | Description |
| --- | --- |
| [airgap_ok](airgap_ok.md) | 폐쇄망 구동 |
| [alt_labels](alt_labels.md) | 조사에서 나온 변형 표기들 (CQ10) |
| [auth_method](auth_method.md) | 인증/로그인 방식 — MCP 연결 시 인증 설계용 |
| [automation_detail](automation_detail.md) | 자동화 상세 — 언어·모듈·예시 — Python API, journal 파일, TCL 등 |
| [automation_if](automation_if.md) | 자동화 인터페이스 (대표 1개) |
| [automation_wish](automation_wish.md) | 자동화 희망 작업 — 반복적이라 AI/에이전트가 대신하면 좋을 일 |
| [batch_capable](batch_capable.md) | 배치/스크립트 실행 — 사람이 클릭하지 않고 실행 가능한가 |
| [certification_use](certification_use.md) | 감항·인증 업무 사용 — 인증 근거 생산에 쓰이는가 |
| [confidence](confidence.md) | 겹친 확장자가 전부 범용(config rules |
| [consumer](consumer.md) | 수요 측 툴사용 (to_io 의 io_owner) |
| [data_name](data_name.md) | 데이터/산출물 명칭 원문 |
| [data_nature](data_nature.md) | 데이터 성격 — 서술형은 문서 RAG, 수치는 DB 적재 대상 |
| [declared](declared.md) | 어느 한쪽의 신고(연계 SW명)와 일치하는지 (docs/02 7 |
| [derived_from](derived_from.md) | 파생의 근거가 된 적재 기록 (provenance) |
| [direction](direction.md) | 방향 — 이 SW 가 받는 것 = 입력(소비), 내놓는 것 = 출력(생산) |
| [excluded_row_count](excluded_row_count.md) | 제외한 행 수 (예시 행·빈 행 등, 사유는 실행 로그) |
| [extensions](extensions.md) | 정규화한 확장자 목록 (소문자, 점·별표 제거, 별칭 적용) |
| [extensions_raw](extensions_raw.md) | 파일 형식/확장자 원문 |
| [feeds](feeds.md) | (파생) 이 툴사용이 데이터를 공급하는 툴사용 — Feed 의 지름길, 경로 질의(eg:feeds+)용 |
| [format_standard](format_standard.md) | 포맷 표준성 |
| [frequency](frequency.md) | 사용 빈도 — 착수 순위 정렬 키 (docs/02 7 |
| [from_io](from_io.md) | 공급 측 출력 명세 |
| [generated_at](generated_at.md) | 파생 노드 생성 일시 (provenance) |
| [grade](grade.md) | 착수 등급 (수기·변환 구간에만 매긴다, docs/02 7 |
| [headless](headless.md) | 헤드리스 실행 — 화면 없이(서버에서) 실행 가능한가 |
| [id](id.md) | 노드 식별자 |
| [inhouse_format](inhouse_format.md) | 확장자 원문에 '(사내)'·'사내' 표기가 있었는지 |
| [io_category](io_category.md) | 분류 |
| [io_owner](io_owner.md) | 이 입출력을 가진 툴사용 (owner_source_key 로 찾은 것) |
| [kind](kind.md) | 구분 — 사용 기록들의 응답 중 다수값 |
| [label](label.md) | 사람이 읽는 이름 |
| [license_count](license_count.md) | 보유 수량 (정수 변환 성공 시) |
| [license_count_raw](license_count_raw.md) | 보유 수량 원문 — 정수 변환에 실패했을 때만 보존 (경고와 함께) |
| [license_expiry](license_expiry.md) | 만료 시기 YYYY-MM |
| [license_type](license_type.md) | 라이선스 형태 |
| [loaded_at](loaded_at.md) | 적재 일시 |
| [loaded_in](loaded_in.md) | 이 노드를 만든 적재 기록 (provenance) |
| [manual](manual.md) | 수기 구간 여부 (전달 방법 기준) |
| [manual_basis](manual_basis.md) | 수기 판정 근거 — 전달방법, 또는 비고 키워드만 있는 보조 신호 |
| [matched_category](matched_category.md) | 양쪽이 일치한 분류 |
| [matched_extensions](matched_extensions.md) | 양쪽이 겹친 정규화 확장자 |
| [merged_into](merged_into.md) | 사람 판정으로 다른 Tool 에 통합된 경우 그 대상 (status=통합됨과 함께) |
| [note](note.md) | 비고 (원문) |
| [operation_mode](operation_mode.md) | 조작 방식 |
| [output_storage](output_storage.md) | 산출물 주 저장 위치 (상세 경로는 SW입출력 시트) |
| [owner_source_key](owner_source_key.md) | SW ID 원문 |
| [pain_points](pain_points.md) | 현재 수작업·애로 구간 — 타 SW 와 데이터를 주고받을 때 수작업 구간 등 |
| [partner_raw](partner_raw.md) | 연계 SW명 원문 — 신고된 연결 |
| [partner_tools](partner_tools.md) | 연계 SW명 중 Tool 로 해석된 것 |
| [partner_unresolved](partner_unresolved.md) | 연계 SW명 중 Tool 로 해석하지 못한 이름 — 조사 누락 후보 (CQ09) |
| [phase](phase.md) | 이 SW 를 주로 쓰는 개발 단계 (걸치면 범위로) |
| [pref_label](pref_label.md) | 대표 이름 |
| [priority_opinion](priority_opinion.md) | 우선순위 의견 — 착수 순위 정렬 키 (docs/02 7 |
| [purpose_class](purpose_class.md) | 용도 대분류 |
| [purpose_detail](purpose_detail.md) | 용도 상세 원문 |
| [reported_kind](reported_kind.md) | 구분 원문 |
| [reported_tool_name](reported_tool_name.md) | SW명(정식) 원문 |
| [reported_vendor](reported_vendor.md) | 제조사/개발주체 원문 |
| [roadmap_note](roadmap_note.md) | 대체/업그레이드 계획 — 단종·버전업·전환 예정 |
| [row_count](row_count.md) | 적재한 행 수 (두 시트 합) |
| [rule_version](rule_version.md) | 이 파생 노드를 만든 규칙 버전 (예 feed_v1) |
| [run_id](run_id.md) | 적재 실행 ID (output/<실행ID> 와 같다) |
| [runtime_env](runtime_env.md) | 실행 환경 (복수면 대표 1개 + 비고) |
| [security_grade](security_grade.md) | 보안등급 — 지금은 속성으로만 적재, 접근 통제는 M6 이후 MCP 게이트웨이 (docs/02 11장) |
| [source_file_name](source_file_name.md) | 원천 파일명 (경로 제외) |
| [source_key](source_key.md) | SW ID 원문 (분야 약칭이 들어 있어 URI 로 쓰지 않는다 — docs/02 4장) |
| [source_row](source_row.md) | 원천 엑셀 시트의 행 번호 (조사 보완 시 원본 행을 찾기 위한 추적 정보) |
| [source_sha256](source_sha256.md) | 원천 파일 SHA-256 (소문자 16진수) |
| [status](status.md) | 수명주기 상태 |
| [storage_path](storage_path.md) | 저장 위치/경로 원문 (공유폴더 경로, PDM 폴더명) |
| [succeeded_by](succeeded_by.md) | 통폐합·분할로 이 분야를 이어받은 분야 |
| [supplier](supplier.md) | 공급 측 툴사용 (from_io 의 io_owner) |
| [task_summary](task_summary.md) | 이 SW 로 실제 수행하는 업무 1~2문장 |
| [to_io](to_io.md) | 수요 측 입력 명세 |
| [transfer](transfer.md) | 양쪽 명세의 전달 방법 |
| [transfer_method](transfer_method.md) | 전달 방법 |
| [usage_field](usage_field.md) | 담당 부서 값으로 만든 Field (문자열이 아니라 노드) |
| [usage_tool](usage_tool.md) | 통합된 Tool (reported_tool_name 을 정규화해 결정) |
| [user_count](user_count.md) | 사용 인원수 (정수 변환 성공 시) |
| [user_count_raw](user_count_raw.md) | 사용 인원수 원문 — 정수 변환에 실패했을 때만 보존 (경고와 함께) |
| [validation_ref](validation_ref.md) | 검증 기준/문서번호 원문 |
| [validation_status](validation_status.md) | 사내 검증 상태 (해석 SW 의 V&V 등) |
| [vendor](vendor.md) | 제조사/개발주체 — 사용 기록들의 응답 중 다수값 (엇갈리면 검토표에 표시) |
| [version](version.md) | 사용 중인 버전 전부 (원문) |
| [warning_count](warning_count.md) | 적재 중 경고 수 (내용은 실행 로그) |


## Enumerations

| Enumeration | Description |
| --- | --- |
| [AirgapSupport](AirgapSupport.md) | 원본 양식 '선택지' 시트의 '폐쇄망구동' 목록 |
| [AuthMethod](AuthMethod.md) | 원본 양식 '선택지' 시트의 '인증방식' 목록 |
| [AutomationInterface](AutomationInterface.md) | 원본 양식 '선택지' 시트의 '자동화IF' 목록 |
| [BatchCapability](BatchCapability.md) | 원본 양식 '선택지' 시트의 '배치실행' 목록 |
| [DataNature](DataNature.md) | 원본 양식 '선택지' 시트의 '데이터성격' 목록 |
| [DevPhase](DevPhase.md) | 원본 양식 '선택지' 시트의 '사용단계' 목록 |
| [EntityStatus](EntityStatus.md) | 수명주기 상태 — 삭제 대신 전이 (상위 스키마 v0 |
| [FeedConfidence](FeedConfidence.md) | 공급 연결 신뢰도 (docs/02 7 |
| [FormatStandard](FormatStandard.md) | 원본 양식 '선택지' 시트의 '포맷표준성' 목록 |
| [HeadlessCapability](HeadlessCapability.md) | 원본 양식 '선택지' 시트의 '가능불가모름' 목록 |
| [IODirection](IODirection.md) | 원본 양식 '선택지' 시트의 '방향' 목록 |
| [LicenseType](LicenseType.md) | 원본 양식 '선택지' 시트의 '라이선스형태' 목록 |
| [ManualBasis](ManualBasis.md) | 수기 구간 판정 근거 (docs/02 7 |
| [OperationMode](OperationMode.md) | 원본 양식 '선택지' 시트의 '조작방식' 목록 |
| [Priority](Priority.md) | 원본 양식 '선택지' 시트의 '우선순위' 목록 |
| [PurposeClass](PurposeClass.md) | 원본 양식 '선택지' 시트의 '용도대분류' 목록 |
| [RuntimeEnv](RuntimeEnv.md) | 원본 양식 '선택지' 시트의 '실행환경' 목록 |
| [SecurityGrade](SecurityGrade.md) | 원본 양식 '선택지' 시트의 '보안등급' 목록 |
| [StartGrade](StartGrade.md) | 착수 등급 (docs/02 7 |
| [StorageLocation](StorageLocation.md) | 원본 양식 '선택지' 시트의 '저장위치' 목록 |
| [ToolKind](ToolKind.md) | 원본 양식 '선택지' 시트의 '구분' 목록 |
| [TransferMethod](TransferMethod.md) | 원본 양식 '선택지' 시트의 '전달방법' 목록 |
| [UsageFrequency](UsageFrequency.md) | 원본 양식 '선택지' 시트의 '사용빈도' 목록 |
| [ValidationStatus](ValidationStatus.md) | 원본 양식 '선택지' 시트의 '검증상태' 목록 |
| [YesNoUnknown](YesNoUnknown.md) | 원본 양식 '선택지' 시트의 '예아니오모름' 목록 |


## Types

| Type | Description |
| --- | --- |


## Subsets

| Subset | Description |
| --- | --- |
