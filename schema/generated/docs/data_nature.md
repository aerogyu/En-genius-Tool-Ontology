---
search:
  boost: 5.0
---

# Slot: data_nature 


_데이터 성격 — 서술형은 문서 RAG, 수치는 DB 적재 대상._



<div data-search-exclude markdown="1">



URI: [eg:data_nature](http://en-genius.local/onto/data_nature)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [IOSpec](IOSpec.md) | SW입출력 1행 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [DataNature](DataNature.md) |
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
| form_header | 데이터 성격 * |
| form_column | H |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:data_nature |
| native | eg:data_nature |




## LinkML Source

<details>
```yaml
name: data_nature
annotations:
  form_sheet:
    tag: form_sheet
    value: SW입출력
  form_header:
    tag: form_header
    value: 데이터 성격 *
  form_column:
    tag: form_column
    value: H
description: 데이터 성격 — 서술형은 문서 RAG, 수치는 DB 적재 대상.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: IOSpec
domain_of:
- IOSpec
range: DataNature
required: true

```
</details></div>