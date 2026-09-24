---
search:
  boost: 5.0
---

# Slot: extensions 


_정규화한 확장자 목록 (소문자, 점·별표 제거, 별칭 적용). 연결 계산 키 ② (docs/02 6.2)._



<div data-search-exclude markdown="1">



URI: [eg:extensions](http://en-genius.local/onto/extensions)
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


### Value Constraints

| Property | Value |
| --- | --- |
| Regex Pattern | `^[a-z0-9_+-]+$` |












## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:extensions |
| native | eg:extensions |




## LinkML Source

<details>
```yaml
name: extensions
description: 정규화한 확장자 목록 (소문자, 점·별표 제거, 별칭 적용). 연결 계산 키 ② (docs/02 6.2).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: IOSpec
domain_of:
- IOSpec
range: string
multivalued: true
pattern: ^[a-z0-9_+-]+$

```
</details></div>