---
search:
  boost: 5.0
---

# Slot: runtime_env 


_실행 환경 (복수면 대표 1개 + 비고)._



<div data-search-exclude markdown="1">



URI: [eg:runtime_env](http://en-genius.local/onto/runtime_env)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [RuntimeEnv](RuntimeEnv.md) |
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
| form_header | 실행 환경 * |
| form_column | Q |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:runtime_env |
| native | eg:runtime_env |




## LinkML Source

<details>
```yaml
name: runtime_env
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 실행 환경 *
  form_column:
    tag: form_column
    value: Q
description: 실행 환경 (복수면 대표 1개 + 비고).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: RuntimeEnv
required: true

```
</details></div>