# engenius_tool 

연구소 분야별 SW 조사(SW기본정보·SW입출력)를 담아 툴 간 데이터 연결을 계산하기 위한 스키마. 설계 기준은 docs/02_툴온톨로지_설계.md (3·4·7장). 클래스 10종: Field, Tool, ToolUsage, IOSpec, DataCategory, SurveyLoad (survey 그래프) + Feed, Reconciliation, IsolationFinding, Handoff (파생 — derived 그래프, v0.2 에서 뒤의 셋 추가: docs/05 D1). ID 는 의미 없는 일련번호·해시(egid:TOOL-000001 등), 사람이 읽는 이름은 rdfs:label(@ko). 언어 태그(@ko)는 LinkML 이 데이터로 표현하지 못하므로 적재기(M3)가 RDF 를 만들 때 이름 속성(rdfs:label·skos:prefLabel·skos:altLabel)에만 붙인다 — 선택지 값은 태그 없는 문자열. 식별자는 노드 IRI 자체다(eg:id 트리플 없음). ID 규칙은 SHACL 노드 모양이 IRI 패턴으로 검사한다. 네임스페이스 정본은 이 파일의 prefixes (eg·egid) — 코드는 여기서 읽는다 (config.namespaces()). 예약(미구현): WbsTask —uses_tool→ ToolUsage/Tool (지멘스 PoC 의 WBS Lv.6 연결).

URI: http://en-genius.local/onto/