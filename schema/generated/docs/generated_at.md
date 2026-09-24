---
search:
  boost: 5.0
---

# Slot: generated_at 


_파생 노드 생성 일시 (provenance)._



<div data-search-exclude markdown="1">



URI: [prov:generatedAtTime](http://www.w3.org/ns/prov#generatedAtTime)
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
| Range | [xsd:dateTime](http://www.w3.org/2001/XMLSchema#dateTime) |
| Domain Of | [Derived](Derived.md) |
| Slot URI | [prov:generatedAtTime](http://www.w3.org/ns/prov#generatedAtTime) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |










## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | prov:generatedAtTime |
| native | eg:generated_at |




## LinkML Source

<details>
```yaml
name: generated_at
description: 파생 노드 생성 일시 (provenance).
from_schema: http://en-genius.local/onto/
rank: 1000
slot_uri: prov:generatedAtTime
domain_of:
- Derived
range: datetime

```
</details></div>