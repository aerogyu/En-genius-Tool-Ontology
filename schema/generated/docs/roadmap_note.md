---
search:
  boost: 5.0
---

# Slot: roadmap_note 


_대체/업그레이드 계획 — 단종·버전업·전환 예정._



<div data-search-exclude markdown="1">



URI: [eg:roadmap_note](http://en-genius.local/onto/roadmap_note)
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
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [ToolUsage](ToolUsage.md) |












## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_sheet | SW기본정보 |
| form_header | 대체/업그레이드 계획 |
| form_column | AF |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:roadmap_note |
| native | eg:roadmap_note |




## LinkML Source

<details>
```yaml
name: roadmap_note
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 대체/업그레이드 계획
  form_column:
    tag: form_column
    value: AF
description: 대체/업그레이드 계획 — 단종·버전업·전환 예정.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: string

```
</details></div>