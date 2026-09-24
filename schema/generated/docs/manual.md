---
search:
  boost: 5.0
---

# Slot: manual 


_수기 구간 여부 (전달 방법 기준)._



<div data-search-exclude markdown="1">



URI: [eg:manual](http://en-genius.local/onto/manual)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Feed](Feed.md) | (파생) 규칙으로 계산한 공급 연결 — 출력 명세 from_io 와 입력 명세 to_io 의 분류가 같고 정규화 확장자가 겹칠 때 (doc... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [xsd:boolean](http://www.w3.org/2001/XMLSchema#boolean) |
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
| self | eg:manual |
| native | eg:manual |




## LinkML Source

<details>
```yaml
name: manual
description: 수기 구간 여부 (전달 방법 기준).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: Feed
domain_of:
- Feed
range: boolean
required: true

```
</details></div>