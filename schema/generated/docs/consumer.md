---
search:
  boost: 5.0
---

# Slot: consumer 


_수요 측 툴사용 (Feed 는 to_io 의 io_owner, Handoff 는 착수 구간의 수요 측)._



<div data-search-exclude markdown="1">



URI: [eg:consumer](http://en-genius.local/onto/consumer)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Feed](Feed.md) | (파생) 규칙으로 계산한 공급 연결 — 출력 명세 from_io 와 입력 명세 to_io 의 분류가 같고 정규화 확장자가 겹칠 때 (doc... |  yes  |
| [Handoff](Handoff.md) | (파생) 착수 구간 1행 (CQ03, docs/02 7 |  yes  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [ToolUsage](ToolUsage.md) |
| Domain Of | [Feed](Feed.md), [Handoff](Handoff.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










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
description: 수요 측 툴사용 (Feed 는 to_io 의 io_owner, Handoff 는 착수 구간의 수요 측).
from_schema: http://en-genius.local/onto/
rank: 1000
domain_of:
- Feed
- Handoff
range: ToolUsage

```
</details></div>