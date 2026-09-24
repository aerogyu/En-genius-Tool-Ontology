---
search:
  boost: 5.0
---

# Slot: license_expiry 


_만료 시기 YYYY-MM. 영구면 비움._



<div data-search-exclude markdown="1">



URI: [eg:license_expiry](http://en-genius.local/onto/license_expiry)
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


### Value Constraints

| Property | Value |
| --- | --- |
| Regex Pattern | `^[0-9]{4}-(0[1-9]|1[0-2])$` |












## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_sheet | SW기본정보 |
| form_header | 만료 시기 |
| form_column | P |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:license_expiry |
| native | eg:license_expiry |




## LinkML Source

<details>
```yaml
name: license_expiry
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 만료 시기
  form_column:
    tag: form_column
    value: P
description: 만료 시기 YYYY-MM. 영구면 비움.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: string
pattern: ^[0-9]{4}-(0[1-9]|1[0-2])$

```
</details></div>