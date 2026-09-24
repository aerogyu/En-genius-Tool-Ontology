---
search:
  boost: 5.0
---

# Slot: source_file_name 


_원천 파일명 (경로 제외 — 경로 구분자·드라이브 문자를 허용하지 않는다)._



<div data-search-exclude markdown="1">



URI: [eg:source_file_name](http://en-genius.local/onto/source_file_name)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [SurveyLoad](SurveyLoad.md) | 적재 기록 1건 — 원천 조사 파일 1개를 한 번 적재한 것 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [xsd:string](http://www.w3.org/2001/XMLSchema#string) |
| Domain Of | [SurveyLoad](SurveyLoad.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [SurveyLoad](SurveyLoad.md) |


### Value Constraints

| Property | Value |
| --- | --- |
| Regex Pattern | `^[^/\\:]+$` |












## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:source_file_name |
| native | eg:source_file_name |




## LinkML Source

<details>
```yaml
name: source_file_name
description: 원천 파일명 (경로 제외 — 경로 구분자·드라이브 문자를 허용하지 않는다).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: SurveyLoad
domain_of:
- SurveyLoad
range: string
required: true
pattern: ^[^/\\:]+$

```
</details></div>