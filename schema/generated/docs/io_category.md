---
search:
  boost: 5.0
---

# Slot: io_category 


_분류. 연결 계산 키 ①._



<div data-search-exclude markdown="1">



URI: [eg:io_category](http://en-genius.local/onto/io_category)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [IOSpec](IOSpec.md) | SW입출력 1행 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [DataCategory](DataCategory.md) |
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
| form_header | 분류 * |
| form_column | E |
| form_list | 온톨로지분류 |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:io_category |
| native | eg:io_category |




## LinkML Source

<details>
```yaml
name: io_category
annotations:
  form_sheet:
    tag: form_sheet
    value: SW입출력
  form_header:
    tag: form_header
    value: 분류 *
  form_column:
    tag: form_column
    value: E
  form_list:
    tag: form_list
    value: 온톨로지분류
description: 분류. 연결 계산 키 ①.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: IOSpec
domain_of:
- IOSpec
range: DataCategory
required: true

```
</details></div>