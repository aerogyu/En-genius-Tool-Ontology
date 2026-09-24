---
search:
  boost: 5.0
---

# Slot: derived_from 


_파생의 근거가 된 적재 기록 (provenance)._



<div data-search-exclude markdown="1">



URI: [prov:wasDerivedFrom](http://www.w3.org/ns/prov#wasDerivedFrom)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Derived](Derived.md) | 규칙으로 계산한 파생 노드의 provenance 묶음 (docs/02 8장) |  yes  |
| [Feed](Feed.md) | (파생) 규칙으로 계산한 공급 연결 — 출력 명세 from_io 와 입력 명세 to_io 의 분류가 같고 정규화 확장자가 겹칠 때 (doc... |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [SurveyLoad](SurveyLoad.md) |
| Domain Of | [Derived](Derived.md) |
| Slot URI | [prov:wasDerivedFrom](http://www.w3.org/ns/prov#wasDerivedFrom) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Multivalued | Yes |










## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | prov:wasDerivedFrom |
| native | eg:derived_from |




## LinkML Source

<details>
```yaml
name: derived_from
description: 파생의 근거가 된 적재 기록 (provenance).
from_schema: http://en-genius.local/onto/
rank: 1000
slot_uri: prov:wasDerivedFrom
domain_of:
- Derived
range: SurveyLoad
multivalued: true

```
</details></div>