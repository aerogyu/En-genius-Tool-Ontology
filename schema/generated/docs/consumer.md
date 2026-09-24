---
search:
  boost: 5.0
---

# Slot: consumer 


_수요 측 툴사용 (to_io 의 io_owner)._



<div data-search-exclude markdown="1">



URI: [eg:consumer](http://en-genius.local/onto/consumer)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Feed](Feed.md) | (파생) 규칙으로 계산한 공급 연결 — 출력 명세 from_io 와 입력 명세 to_io 의 분류가 같고 정규화 확장자가 겹칠 때 (doc... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [ToolUsage](ToolUsage.md) |
| Domain Of | [Feed](Feed.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [Feed](Feed.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:consumer |
| native | eg:consumer |




## LinkML Source

<details>
```yaml
name: consumer
description: 수요 측 툴사용 (to_io 의 io_owner).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: Feed
domain_of:
- Feed
range: ToolUsage
required: true

```
</details></div>