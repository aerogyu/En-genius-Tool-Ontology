---
search:
  boost: 5.0
---

# Slot: certification_use 


_감항·인증 업무 사용 — 인증 근거 생산에 쓰이는가._



<div data-search-exclude markdown="1">



URI: [eg:certification_use](http://en-genius.local/onto/certification_use)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [YesNoUnknown](YesNoUnknown.md) |
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
| form_header | 감항·인증 업무 사용 * |
| form_column | AB |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:certification_use |
| native | eg:certification_use |




## LinkML Source

<details>
```yaml
name: certification_use
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 감항·인증 업무 사용 *
  form_column:
    tag: form_column
    value: AB
description: 감항·인증 업무 사용 — 인증 근거 생산에 쓰이는가.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: YesNoUnknown
required: true

```
</details></div>