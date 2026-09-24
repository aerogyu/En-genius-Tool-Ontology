---
search:
  boost: 5.0
---

# Slot: pain_points 


_현재 수작업·애로 구간 — 타 SW 와 데이터를 주고받을 때 수작업 구간 등._



<div data-search-exclude markdown="1">



URI: [eg:pain_points](http://en-genius.local/onto/pain_points)
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
| form_header | 현재 수작업·애로 구간 |
| form_column | AD |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:pain_points |
| native | eg:pain_points |




## LinkML Source

<details>
```yaml
name: pain_points
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 현재 수작업·애로 구간
  form_column:
    tag: form_column
    value: AD
description: 현재 수작업·애로 구간 — 타 SW 와 데이터를 주고받을 때 수작업 구간 등.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: string

```
</details></div>