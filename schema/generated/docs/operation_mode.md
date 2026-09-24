---
search:
  boost: 5.0
---

# Slot: operation_mode 


_조작 방식. 착수 등급 규칙의 입력 (docs/02 7.4)._



<div data-search-exclude markdown="1">



URI: [eg:operation_mode](http://en-genius.local/onto/operation_mode)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [OperationMode](OperationMode.md) |
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
| form_header | 조작 방식 * |
| form_column | S |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:operation_mode |
| native | eg:operation_mode |




## LinkML Source

<details>
```yaml
name: operation_mode
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 조작 방식 *
  form_column:
    tag: form_column
    value: S
description: 조작 방식. 착수 등급 규칙의 입력 (docs/02 7.4).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: OperationMode
required: true

```
</details></div>