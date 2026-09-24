---
search:
  boost: 5.0
---

# Slot: source_sha256 


_원천 파일 SHA-256 (소문자 16진수)._



<div data-search-exclude markdown="1">



URI: [eg:source_sha256](http://en-genius.local/onto/source_sha256)
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
| Regex Pattern | `^[0-9a-f]{64}$` |












## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:source_sha256 |
| native | eg:source_sha256 |




## LinkML Source

<details>
```yaml
name: source_sha256
description: 원천 파일 SHA-256 (소문자 16진수).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: SurveyLoad
domain_of:
- SurveyLoad
range: string
required: true
pattern: ^[0-9a-f]{64}$

```
</details></div>