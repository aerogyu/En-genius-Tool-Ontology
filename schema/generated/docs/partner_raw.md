---
search:
  boost: 5.0
---

# Slot: partner_raw 


_연계 SW명 원문 — 신고된 연결._



<div data-search-exclude markdown="1">



URI: [eg:partner_raw](http://en-genius.local/onto/partner_raw)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [IOSpec](IOSpec.md) | SW입출력 1행 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [xsd:string](http://www.w3.org/2001/XMLSchema#string) |
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
| form_header | 연계 SW명 |
| form_column | J |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:partner_raw |
| native | eg:partner_raw |




## LinkML Source

<details>
```yaml
name: partner_raw
annotations:
  form_sheet:
    tag: form_sheet
    value: SW입출력
  form_header:
    tag: form_header
    value: 연계 SW명
  form_column:
    tag: form_column
    value: J
description: 연계 SW명 원문 — 신고된 연결.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: IOSpec
domain_of:
- IOSpec
range: string

```
</details></div>