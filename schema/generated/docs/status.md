---
search:
  boost: 5.0
---

# Slot: status 


_수명주기 상태 — 삭제하지 않고 상태를 바꾼다 (docs/01 원칙 9). 없으면 활성._



<div data-search-exclude markdown="1">



URI: [eg:status](http://en-genius.local/onto/status)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ResearchField](ResearchField.md) | 연구소 분야 (조직 노드, RDF 클래스 eg:Field — docs/02 용어) |  no  |
| [Tool](Tool.md) | 제품 단위 툴 (표기 변형을 통합한 것) |  no  |
| [DataCategory](DataCategory.md) | 데이터 분류 (SW입출력 '분류' 드롭다운 값) |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [EntityStatus](EntityStatus.md) |
| Domain Of | [ResearchField](ResearchField.md), [Tool](Tool.md), [DataCategory](DataCategory.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| If Absent | `string(활성)` |












## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:status |
| native | eg:status |




## LinkML Source

<details>
```yaml
name: status
description: 수명주기 상태 — 삭제하지 않고 상태를 바꾼다 (docs/01 원칙 9). 없으면 활성.
from_schema: http://en-genius.local/onto/
rank: 1000
ifabsent: string(활성)
domain_of:
- ResearchField
- Tool
- DataCategory
range: EntityStatus

```
</details></div>