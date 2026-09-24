---
search:
  boost: 5.0
---

# Slot: row_count 


_적재한 행 수 (두 시트 합)._



<div data-search-exclude markdown="1">



URI: [eg:row_count](http://en-genius.local/onto/row_count)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [SurveyLoad](SurveyLoad.md) | 적재 기록 1건 — 원천 조사 파일 1개를 한 번 적재한 것 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [xsd:integer](http://www.w3.org/2001/XMLSchema#integer) |
| Domain Of | [SurveyLoad](SurveyLoad.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [SurveyLoad](SurveyLoad.md) |


### Value Constraints

| Property | Value |
| --- | --- |
| Minimum Value | 0 |












## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:row_count |
| native | eg:row_count |




## LinkML Source

<details>
```yaml
name: row_count
description: 적재한 행 수 (두 시트 합).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: SurveyLoad
domain_of:
- SurveyLoad
range: integer
minimum_value: 0

```
</details></div>