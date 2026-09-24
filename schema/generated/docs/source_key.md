---
search:
  boost: 5.0
---

# Slot: source_key 


_SW ID 원문 (분야 약칭이 들어 있어 URI 로 쓰지 않는다 — docs/02 4장)._



<div data-search-exclude markdown="1">



URI: [eg:source_key](http://en-genius.local/onto/source_key)
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
| form_header | SW ID * |
| form_column | A |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:source_key |
| native | eg:source_key |




## LinkML Source

<details>
```yaml
name: source_key
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: SW ID *
  form_column:
    tag: form_column
    value: A
description: SW ID 원문 (분야 약칭이 들어 있어 URI 로 쓰지 않는다 — docs/02 4장).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: string
required: true

```
</details></div>