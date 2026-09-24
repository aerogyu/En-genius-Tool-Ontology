---
search:
  boost: 5.0
---

# Slot: extensions_raw 


_파일 형식/확장자 원문._



<div data-search-exclude markdown="1">



URI: [eg:extensions_raw](http://en-genius.local/onto/extensions_raw)
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
| form_header | 파일 형식/확장자 * |
| form_column | F |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:extensions_raw |
| native | eg:extensions_raw |




## LinkML Source

<details>
```yaml
name: extensions_raw
annotations:
  form_sheet:
    tag: form_sheet
    value: SW입출력
  form_header:
    tag: form_header
    value: 파일 형식/확장자 *
  form_column:
    tag: form_column
    value: F
description: 파일 형식/확장자 원문.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: IOSpec
domain_of:
- IOSpec
range: string
required: true

```
</details></div>