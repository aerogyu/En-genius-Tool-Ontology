---
search:
  boost: 5.0
---

# Slot: id 


_노드 식별자. 의미 없는 일련번호 또는 결정적 해시 (docs/02 4장). 예 egid:TOOL-000001_



<div data-search-exclude markdown="1">



URI: [eg:id](http://en-genius.local/onto/id)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ResearchField](ResearchField.md) | 연구소 분야 (조직 노드, RDF 클래스 eg:Field — docs/02 용어) |  yes  |
| [Tool](Tool.md) | 제품 단위 툴 (표기 변형을 통합한 것) |  yes  |
| [DataCategory](DataCategory.md) | 데이터 분류 (SW입출력 '분류' 드롭다운 값) |  yes  |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  yes  |
| [IOSpec](IOSpec.md) | SW입출력 1행 |  yes  |
| [Feed](Feed.md) | (파생) 규칙으로 계산한 공급 연결 — 출력 명세 from_io 와 입력 명세 to_io 의 분류가 같고 정규화 확장자가 겹칠 때 (doc... |  yes  |
| [SurveyLoad](SurveyLoad.md) | 적재 기록 1건 — 원천 조사 파일 1개를 한 번 적재한 것 |  yes  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [xsd:anyURI](http://www.w3.org/2001/XMLSchema#anyURI) |
| Domain Of | [ResearchField](ResearchField.md), [Tool](Tool.md), [DataCategory](DataCategory.md), [ToolUsage](ToolUsage.md), [IOSpec](IOSpec.md), [Feed](Feed.md), [SurveyLoad](SurveyLoad.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Identifier | Yes |












## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:id |
| native | eg:id |




## LinkML Source

<details>
```yaml
name: id
description: 노드 식별자. 의미 없는 일련번호 또는 결정적 해시 (docs/02 4장). 예 egid:TOOL-000001
from_schema: http://en-genius.local/onto/
rank: 1000
identifier: true
domain_of:
- ResearchField
- Tool
- DataCategory
- ToolUsage
- IOSpec
- Feed
- SurveyLoad
range: uriorcurie
required: true

```
</details></div>