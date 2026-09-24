---
search:
  boost: 5.0
---

# Slot: source_row 


_원천 엑셀 시트의 행 번호 (조사 보완 시 원본 행을 찾기 위한 추적 정보)._



<div data-search-exclude markdown="1">



URI: [eg:source_row](http://en-genius.local/onto/source_row)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |
| [IOSpec](IOSpec.md) | SW입출력 1행 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [xsd:integer](http://www.w3.org/2001/XMLSchema#integer) |
| Domain Of | [ToolUsage](ToolUsage.md), [IOSpec](IOSpec.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:source_row |
| native | eg:source_row |




## LinkML Source

<details>
```yaml
name: source_row
description: 원천 엑셀 시트의 행 번호 (조사 보완 시 원본 행을 찾기 위한 추적 정보).
from_schema: http://en-genius.local/onto/
rank: 1000
domain_of:
- ToolUsage
- IOSpec
range: integer

```
</details></div>