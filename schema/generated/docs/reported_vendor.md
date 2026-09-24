---
search:
  boost: 5.0
---

# Slot: reported_vendor 


_제조사/개발주체 원문. Tool.vendor(다수값)의 입력._



<div data-search-exclude markdown="1">



URI: [eg:reported_vendor](http://en-genius.local/onto/reported_vendor)
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
| form_header | 제조사 / 개발주체 * |
| form_column | D |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:reported_vendor |
| native | eg:reported_vendor |




## LinkML Source

<details>
```yaml
name: reported_vendor
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 제조사 / 개발주체 *
  form_column:
    tag: form_column
    value: D
description: 제조사/개발주체 원문. Tool.vendor(다수값)의 입력.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: string
required: true

```
</details></div>