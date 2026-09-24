---
search:
  boost: 5.0
---

# Slot: label 


_사람이 읽는 이름. RDF 에서는 @ko 언어 태그를 붙인다._



<div data-search-exclude markdown="1">



URI: [rdfs:label](http://www.w3.org/2000/01/rdf-schema#label)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ResearchField](ResearchField.md) | 연구소 분야 (조직 노드, RDF 클래스 eg:Field — docs/02 용어) |  no  |
| [Tool](Tool.md) | 제품 단위 툴 (표기 변형을 통합한 것) |  no  |
| [DataCategory](DataCategory.md) | 데이터 분류 (SW입출력 '분류' 드롭다운 값) |  no  |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |
| [IOSpec](IOSpec.md) | SW입출력 1행 |  yes  |
| [Feed](Feed.md) | (파생) 규칙으로 계산한 공급 연결 — 출력 명세 from_io 와 입력 명세 to_io 의 분류가 같고 정규화 확장자가 겹칠 때 (doc... |  no  |
| [SurveyLoad](SurveyLoad.md) | 적재 기록 1건 — 원천 조사 파일 1개를 한 번 적재한 것 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [xsd:string](http://www.w3.org/2001/XMLSchema#string) |
| Domain Of | [ResearchField](ResearchField.md), [Tool](Tool.md), [DataCategory](DataCategory.md), [ToolUsage](ToolUsage.md), [IOSpec](IOSpec.md), [Feed](Feed.md), [SurveyLoad](SurveyLoad.md) |
| Slot URI | [rdfs:label](http://www.w3.org/2000/01/rdf-schema#label) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |










## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | rdfs:label |
| native | eg:label |




## LinkML Source

<details>
```yaml
name: label
description: 사람이 읽는 이름. RDF 에서는 @ko 언어 태그를 붙인다.
from_schema: http://en-genius.local/onto/
rank: 1000
slot_uri: rdfs:label
domain_of:
- ResearchField
- Tool
- DataCategory
- ToolUsage
- IOSpec
- Feed
- SurveyLoad
range: string
required: true

```
</details></div>