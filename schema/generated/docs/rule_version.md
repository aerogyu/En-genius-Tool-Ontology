---
search:
  boost: 5.0
---

# Slot: rule_version 


_이 파생 노드를 만든 규칙 버전 (예 feed_v1)._



<div data-search-exclude markdown="1">



URI: [eg:rule_version](http://en-genius.local/onto/rule_version)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Derived](Derived.md) | 규칙으로 계산한 파생 노드의 provenance 묶음 (docs/02 8장) |  yes  |
| [Feed](Feed.md) | (파생) 규칙으로 계산한 공급 연결 — 출력 명세 from_io 와 입력 명세 to_io 의 분류가 같고 정규화 확장자가 겹칠 때 (doc... |  no  |
| [Reconciliation](Reconciliation.md) | (파생) 계산 vs 신고 대조 1건 (CQ04, docs/02 7 |  no  |
| [IsolationFinding](IsolationFinding.md) | (파생) 고립 툴사용 1건 (CQ05, docs/02 7 |  no  |
| [Handoff](Handoff.md) | (파생) 착수 구간 1행 (CQ03, docs/02 7 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [xsd:string](http://www.w3.org/2001/XMLSchema#string) |
| Domain Of | [Derived](Derived.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:rule_version |
| native | eg:rule_version |




## LinkML Source

<details>
```yaml
name: rule_version
description: 이 파생 노드를 만든 규칙 버전 (예 feed_v1).
from_schema: http://en-genius.local/onto/
rank: 1000
domain_of:
- Derived
range: string

```
</details></div>