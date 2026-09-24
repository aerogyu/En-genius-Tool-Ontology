---
search:
  boost: 5.0
---

# Slot: purpose_detail 


_용도 상세 원문. 예) 이차유로 1D 유동 네트워크 해석_



<div data-search-exclude markdown="1">



URI: [eg:purpose_detail](http://en-genius.local/onto/purpose_detail)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [xsd:string](http://www.w3.org/2001/XMLSchema#string) |
| Domain Of | [ToolUsage](ToolUsage.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [ToolUsage](ToolUsage.md) |












## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_sheet | SW기본정보 |
| form_header | 용도 상세 * |
| form_column | G |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:purpose_detail |
| native | eg:purpose_detail |




## LinkML Source

<details>
```yaml
name: purpose_detail
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 용도 상세 *
  form_column:
    tag: form_column
    value: G
description: 용도 상세 원문. 예) 이차유로 1D 유동 네트워크 해석
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: string
required: true

```
</details></div>