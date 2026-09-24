---
search:
  boost: 5.0
---

# Slot: feeds 


_(파생) 이 툴사용이 데이터를 공급하는 툴사용 — Feed 의 지름길, 경로 질의(eg:feeds+)용. derived 그래프에만 있다._



<div data-search-exclude markdown="1">



URI: [eg:feeds](http://en-genius.local/onto/feeds)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [ToolUsage](ToolUsage.md) |
| Domain Of | [ToolUsage](ToolUsage.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Multivalued | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [ToolUsage](ToolUsage.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:feeds |
| native | eg:feeds |




## LinkML Source

<details>
```yaml
name: feeds
description: (파생) 이 툴사용이 데이터를 공급하는 툴사용 — Feed 의 지름길, 경로 질의(eg:feeds+)용. derived 그래프에만
  있다.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: ToolUsage
multivalued: true

```
</details></div>