---
search:
  boost: 5.0
---

# Slot: data_name 


_데이터/산출물 명칭 원문. 표기가 제각각이라 연결 키로 쓰지 않는다 (docs/01 원칙 3)._



<div data-search-exclude markdown="1">



URI: [eg:data_name](http://en-genius.local/onto/data_name)
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
| form_header | 데이터/산출물 명칭 * |
| form_column | D |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:data_name |
| native | eg:data_name |




## LinkML Source

<details>
```yaml
name: data_name
annotations:
  form_sheet:
    tag: form_sheet
    value: SW입출력
  form_header:
    tag: form_header
    value: 데이터/산출물 명칭 *
  form_column:
    tag: form_column
    value: D
description: 데이터/산출물 명칭 원문. 표기가 제각각이라 연결 키로 쓰지 않는다 (docs/01 원칙 3).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: IOSpec
domain_of:
- IOSpec
range: string
required: true

```
</details></div>