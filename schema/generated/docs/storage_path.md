---
search:
  boost: 5.0
---

# Slot: storage_path 


_저장 위치/경로 원문 (공유폴더 경로, PDM 폴더명)._



<div data-search-exclude markdown="1">



URI: [eg:storage_path](http://en-genius.local/onto/storage_path)
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
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [IOSpec](IOSpec.md) |












## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_sheet | SW입출력 |
| form_header | 저장 위치/경로 |
| form_column | K |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:storage_path |
| native | eg:storage_path |




## LinkML Source

<details>
```yaml
name: storage_path
annotations:
  form_sheet:
    tag: form_sheet
    value: SW입출력
  form_header:
    tag: form_header
    value: 저장 위치/경로
  form_column:
    tag: form_column
    value: K
description: 저장 위치/경로 원문 (공유폴더 경로, PDM 폴더명).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: IOSpec
domain_of:
- IOSpec
range: string

```
</details></div>