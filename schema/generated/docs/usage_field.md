---
search:
  boost: 5.0
---

# Slot: usage_field 


_담당 부서 값으로 만든 Field (문자열이 아니라 노드)._



<div data-search-exclude markdown="1">



URI: [eg:usage_field](http://en-genius.local/onto/usage_field)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [ResearchField](ResearchField.md) |
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
| form_header | 담당 부서 * |
| form_column | J |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:usage_field |
| native | eg:usage_field |




## LinkML Source

<details>
```yaml
name: usage_field
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 담당 부서 *
  form_column:
    tag: form_column
    value: J
description: 담당 부서 값으로 만든 Field (문자열이 아니라 노드).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: ResearchField
required: true

```
</details></div>