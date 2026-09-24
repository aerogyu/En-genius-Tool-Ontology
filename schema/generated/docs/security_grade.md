---
search:
  boost: 5.0
---

# Slot: security_grade 


_보안등급 — 지금은 속성으로만 적재, 접근 통제는 M6 이후 MCP 게이트웨이 (docs/02 11장)._



<div data-search-exclude markdown="1">



URI: [eg:security_grade](http://en-genius.local/onto/security_grade)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [IOSpec](IOSpec.md) | SW입출력 1행 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [SecurityGrade](SecurityGrade.md) |
| Domain Of | [IOSpec](IOSpec.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [IOSpec](IOSpec.md) |












## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_sheet | SW입출력 |
| form_header | 보안등급 |
| form_column | L |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:security_grade |
| native | eg:security_grade |




## LinkML Source

<details>
```yaml
name: security_grade
annotations:
  form_sheet:
    tag: form_sheet
    value: SW입출력
  form_header:
    tag: form_header
    value: 보안등급
  form_column:
    tag: form_column
    value: L
description: 보안등급 — 지금은 속성으로만 적재, 접근 통제는 M6 이후 MCP 게이트웨이 (docs/02 11장).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: IOSpec
domain_of:
- IOSpec
range: SecurityGrade

```
</details></div>