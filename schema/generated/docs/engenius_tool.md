# engenius_tool 

연구소 분야별 SW 조사(SW기본정보·SW입출력)를 담아 툴 간 데이터 연결을 계산하기 위한 스키마. 설계 기준은 docs/02_툴온톨로지_설계.md (3·4·7장). 클래스 7종: Field, Tool, ToolUsage, IOSpec, DataCategory, Feed(파생), SurveyLoad. ID 는 의미 없는 일련번호·해시(egid:TOOL-000001 등), 사람이 읽는 이름은 rdfs:label(@ko). 언어 태그(@ko)는 LinkML 이 데이터로 표현하지 못하므로 적재기(M3)가 RDF 를 만들 때 붙인다. 예약(미구현): WbsTask —uses_tool→ ToolUsage/Tool (지멘스 PoC 의 WBS Lv.6 연결).

URI: http://en-genius.local/onto/