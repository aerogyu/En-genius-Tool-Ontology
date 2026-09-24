---
search:
  boost: 5.0
---

# Slot: note 


_비고 (원문)._



<div data-search-exclude markdown="1">



URI: [eg:note](http://en-genius.local/onto/note)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  yes  |
| [IOSpec](IOSpec.md) | SW입출력 1행 |  yes  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [xsd:string](http://www.w3.org/2001/XMLSchema#string) |
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
| self | eg:note |
| native | eg:note |




## LinkML Source

<details>
```yaml
name: note
description: 비고 (원문).
from_schema: http://en-genius.local/onto/
rank: 1000
domain_of:
- ToolUsage
- IOSpec
range: string

```
</details></div>