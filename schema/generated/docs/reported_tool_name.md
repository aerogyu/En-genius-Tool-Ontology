---
search:
  boost: 5.0
---

# Slot: reported_tool_name 


_SW명(정식) 원문. 툴 통합 정규화 키의 입력._



<div data-search-exclude markdown="1">



URI: [eg:reported_tool_name](http://en-genius.local/onto/reported_tool_name)
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
| form_header | SW명(정식) * |
| form_column | B |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:reported_tool_name |
| native | eg:reported_tool_name |




## LinkML Source

<details>
```yaml
name: reported_tool_name
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: SW명(정식) *
  form_column:
    tag: form_column
    value: B
description: SW명(정식) 원문. 툴 통합 정규화 키의 입력.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: string
required: true

```
</details></div>