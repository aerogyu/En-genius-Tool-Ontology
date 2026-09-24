---
search:
  boost: 5.0
---

# Slot: partner_unresolved 


_연계 SW명 중 Tool 로 해석하지 못한 이름 — 조사 누락 후보 (CQ09). 원문은 partner_raw 에 있으므로 여기에는 툴 통합과 같은 정규화 키를 넣는다 (SPARQL 로는 정규화를 재현할 수 없어 원문을 넣으면 표기 변형이 서로 다른 후보로 쪼개진다 — M1 검토)._



<div data-search-exclude markdown="1">



URI: [eg:partner_unresolved](http://en-genius.local/onto/partner_unresolved)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [IOSpec](IOSpec.md) | SW입출력 1행 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [xsd:string](http://www.w3.org/2001/XMLSchema#string) |
| Domain Of | [IOSpec](IOSpec.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Multivalued | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [IOSpec](IOSpec.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:partner_unresolved |
| native | eg:partner_unresolved |




## LinkML Source

<details>
```yaml
name: partner_unresolved
description: 연계 SW명 중 Tool 로 해석하지 못한 이름 — 조사 누락 후보 (CQ09). 원문은 partner_raw 에 있으므로
  여기에는 툴 통합과 같은 정규화 키를 넣는다 (SPARQL 로는 정규화를 재현할 수 없어 원문을 넣으면 표기 변형이 서로 다른 후보로 쪼개진다
  — M1 검토).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: IOSpec
domain_of:
- IOSpec
range: string
multivalued: true

```
</details></div>