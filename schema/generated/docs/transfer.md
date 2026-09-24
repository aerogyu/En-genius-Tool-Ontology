---
search:
  boost: 5.0
---

# Slot: transfer 


_양쪽 명세의 전달 방법._



<div data-search-exclude markdown="1">



URI: [eg:transfer](http://en-genius.local/onto/transfer)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Feed](Feed.md) | (파생) 규칙으로 계산한 공급 연결 — 출력 명세 from_io 와 입력 명세 to_io 의 분류가 같고 정규화 확장자가 겹칠 때 (doc... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [TransferMethod](TransferMethod.md) |
| Domain Of | [Feed](Feed.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Multivalued | Yes |
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
| self | eg:transfer |
| native | eg:transfer |




## LinkML Source

<details>
```yaml
name: transfer
description: 양쪽 명세의 전달 방법.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: Feed
domain_of:
- Feed
range: TransferMethod
multivalued: true

```
</details></div>