---
search:
  boost: 5.0
---

# Slot: run_id 


_적재 실행 ID (output/<실행ID> 와 같다)._



<div data-search-exclude markdown="1">



URI: [eg:run_id](http://en-genius.local/onto/run_id)
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












## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:run_id |
| native | eg:run_id |




## LinkML Source

<details>
```yaml
name: run_id
description: 적재 실행 ID (output/<실행ID> 와 같다).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: SurveyLoad
domain_of:
- SurveyLoad
range: string
required: true

```
</details></div>