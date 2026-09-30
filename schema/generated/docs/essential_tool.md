---
search:
  boost: 5.0
---

# Slot: essential_tool 


_필수 Tool 구분 (O/X) — 양식 v1.1 에서 추가된 열 (v0.3)._



<div data-search-exclude markdown="1">



URI: [eg:essential_tool](http://en-genius.local/onto/essential_tool)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [EssentialTool](EssentialTool.md) |
| Domain Of | [ToolUsage](ToolUsage.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [ToolUsage](ToolUsage.md) |












## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_sheet | SW기본정보 |
| form_header | 필수 Tool 구분 |
| form_column | O |
| form_list | SW 필수 여부 |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:essential_tool |
| native | eg:essential_tool |




## LinkML Source

<details>
```yaml
name: essential_tool
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 필수 Tool 구분
  form_column:
    tag: form_column
    value: O
  form_list:
    tag: form_list
    value: SW 필수 여부
description: 필수 Tool 구분 (O/X) — 양식 v1.1 에서 추가된 열 (v0.3).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: EssentialTool

```
</details></div>