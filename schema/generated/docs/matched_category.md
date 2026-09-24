---
search:
  boost: 5.0
---

# Slot: matched_category 


_양쪽이 일치한 분류._



<div data-search-exclude markdown="1">



URI: [eg:matched_category](http://en-genius.local/onto/matched_category)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Feed](Feed.md) | (파생) 규칙으로 계산한 공급 연결 — 출력 명세 from_io 와 입력 명세 to_io 의 분류가 같고 정규화 확장자가 겹칠 때 (doc... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [DataCategory](DataCategory.md) |
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
| self | eg:matched_category |
| native | eg:matched_category |




## LinkML Source

<details>
```yaml
name: matched_category
description: 양쪽이 일치한 분류.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: Feed
domain_of:
- Feed
range: DataCategory
required: true

```
</details></div>