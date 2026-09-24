---
search:
  boost: 5.0
---

# Slot: batch_capable 


_배치/스크립트 실행 — 사람이 클릭하지 않고 실행 가능한가._



<div data-search-exclude markdown="1">



URI: [eg:batch_capable](http://en-genius.local/onto/batch_capable)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [BatchCapability](BatchCapability.md) |
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
| form_header | 배치/스크립트 실행 * |
| form_column | T |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:batch_capable |
| native | eg:batch_capable |




## LinkML Source

<details>
```yaml
name: batch_capable
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 배치/스크립트 실행 *
  form_column:
    tag: form_column
    value: T
description: 배치/스크립트 실행 — 사람이 클릭하지 않고 실행 가능한가.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: BatchCapability
required: true

```
</details></div>