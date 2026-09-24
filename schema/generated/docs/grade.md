---
search:
  boost: 5.0
---

# Slot: grade 


_착수 등급 (docs/02 7.4) — 수기 연결(manual=true)인 Feed 에 매긴다. 변환 구간(숨은변환 의심)은 계산된 연결이 없는 경우라 Feed 노드가 없다 — 그 등급을 둘 자리는 M4 전에 정한다 (docs/05 미결 사항)._



<div data-search-exclude markdown="1">



URI: [eg:grade](http://en-genius.local/onto/grade)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Feed](Feed.md) | (파생) 규칙으로 계산한 공급 연결 — 출력 명세 from_io 와 입력 명세 to_io 의 분류가 같고 정규화 확장자가 겹칠 때 (doc... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [StartGrade](StartGrade.md) |
| Domain Of | [Feed](Feed.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
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
| self | eg:grade |
| native | eg:grade |




## LinkML Source

<details>
```yaml
name: grade
description: 착수 등급 (docs/02 7.4) — 수기 연결(manual=true)인 Feed 에 매긴다. 변환 구간(숨은변환 의심)은
  계산된 연결이 없는 경우라 Feed 노드가 없다 — 그 등급을 둘 자리는 M4 전에 정한다 (docs/05 미결 사항).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: Feed
domain_of:
- Feed
range: StartGrade

```
</details></div>