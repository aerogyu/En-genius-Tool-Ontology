---
search:
  boost: 5.0
---

# Slot: validation_status 


_사내 검증 상태 (해석 SW 의 V&V 등)._



<div data-search-exclude markdown="1">



URI: [eg:validation_status](http://en-genius.local/onto/validation_status)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [ValidationStatus](ValidationStatus.md) |
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
| form_header | 사내 검증 상태 * |
| form_column | Z |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:validation_status |
| native | eg:validation_status |




## LinkML Source

<details>
```yaml
name: validation_status
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 사내 검증 상태 *
  form_column:
    tag: form_column
    value: Z
description: 사내 검증 상태 (해석 SW 의 V&V 등).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: ValidationStatus
required: true

```
</details></div>