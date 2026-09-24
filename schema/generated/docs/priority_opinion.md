---
search:
  boost: 5.0
---

# Slot: priority_opinion 


_우선순위 의견 — 착수 순위 정렬 키 (docs/02 7.4)._



<div data-search-exclude markdown="1">



URI: [eg:priority_opinion](http://en-genius.local/onto/priority_opinion)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Priority](Priority.md) |
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
| form_header | 우선순위 의견 |
| form_column | AE |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:priority_opinion |
| native | eg:priority_opinion |




## LinkML Source

<details>
```yaml
name: priority_opinion
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 우선순위 의견
  form_column:
    tag: form_column
    value: AE
description: 우선순위 의견 — 착수 순위 정렬 키 (docs/02 7.4).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: Priority

```
</details></div>