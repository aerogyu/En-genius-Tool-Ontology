---
search:
  boost: 5.0
---

# Slot: output_storage 


_산출물 주 저장 위치 (상세 경로는 SW입출력 시트)._



<div data-search-exclude markdown="1">



URI: [eg:output_storage](http://en-genius.local/onto/output_storage)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [StorageLocation](StorageLocation.md) |
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
| form_header | 산출물 주 저장 위치 |
| form_column | Y |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:output_storage |
| native | eg:output_storage |




## LinkML Source

<details>
```yaml
name: output_storage
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 산출물 주 저장 위치
  form_column:
    tag: form_column
    value: Y
description: 산출물 주 저장 위치 (상세 경로는 SW입출력 시트).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: StorageLocation

```
</details></div>