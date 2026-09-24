---
search:
  boost: 5.0
---

# Slot: reported_kind 


_구분 원문. Tool.kind(다수값)의 입력._



<div data-search-exclude markdown="1">



URI: [eg:reported_kind](http://en-genius.local/onto/reported_kind)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [ToolKind](ToolKind.md) |
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
| form_header | 구분 * |
| form_column | E |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:reported_kind |
| native | eg:reported_kind |




## LinkML Source

<details>
```yaml
name: reported_kind
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 구분 *
  form_column:
    tag: form_column
    value: E
description: 구분 원문. Tool.kind(다수값)의 입력.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: ToolKind
required: true

```
</details></div>