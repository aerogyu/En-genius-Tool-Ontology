---
search:
  boost: 5.0
---

# Slot: owner_source_key 


_SW ID 원문. SW기본정보에 없으면 고아 입출력 — io_owner 없이 적재하고 경고._



<div data-search-exclude markdown="1">



URI: [eg:owner_source_key](http://en-genius.local/onto/owner_source_key)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [IOSpec](IOSpec.md) | SW입출력 1행 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [xsd:string](http://www.w3.org/2001/XMLSchema#string) |
| Domain Of | [IOSpec](IOSpec.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [IOSpec](IOSpec.md) |












## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_sheet | SW입출력 |
| form_header | SW ID * |
| form_column | A |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:owner_source_key |
| native | eg:owner_source_key |




## LinkML Source

<details>
```yaml
name: owner_source_key
annotations:
  form_sheet:
    tag: form_sheet
    value: SW입출력
  form_header:
    tag: form_header
    value: SW ID *
  form_column:
    tag: form_column
    value: A
description: SW ID 원문. SW기본정보에 없으면 고아 입출력 — io_owner 없이 적재하고 경고.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: IOSpec
domain_of:
- IOSpec
range: string
required: true

```
</details></div>