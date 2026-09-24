---
search:
  boost: 5.0
---

# Slot: confidence 


_겹친 확장자가 전부 범용(config rules.yaml generic_extensions)이면 낮음._



<div data-search-exclude markdown="1">



URI: [eg:confidence](http://en-genius.local/onto/confidence)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Feed](Feed.md) | (파생) 규칙으로 계산한 공급 연결 — 출력 명세 from_io 와 입력 명세 to_io 의 분류가 같고 정규화 확장자가 겹칠 때 (doc... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [FeedConfidence](FeedConfidence.md) |
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
| self | eg:confidence |
| native | eg:confidence |




## LinkML Source

<details>
```yaml
name: confidence
description: 겹친 확장자가 전부 범용(config rules.yaml generic_extensions)이면 낮음.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: Feed
domain_of:
- Feed
range: FeedConfidence
required: true

```
</details></div>