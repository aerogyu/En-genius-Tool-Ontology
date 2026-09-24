---
search:
  boost: 5.0
---

# Slot: direction 


_방향 — 이 SW 가 받는 것 = 입력(소비), 내놓는 것 = 출력(생산)._



<div data-search-exclude markdown="1">



URI: [eg:direction](http://en-genius.local/onto/direction)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [IOSpec](IOSpec.md) | SW입출력 1행 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [IODirection](IODirection.md) |
| Domain Of | [IOSpec](IOSpec.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [IOSpec](IOSpec.md) |












## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_sheet | SW입출력 |
| form_header | 방향 * |
| form_column | C |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:direction |
| native | eg:direction |




## LinkML Source

<details>
```yaml
name: direction
annotations:
  form_sheet:
    tag: form_sheet
    value: SW입출력
  form_header:
    tag: form_header
    value: 방향 *
  form_column:
    tag: form_column
    value: C
description: 방향 — 이 SW 가 받는 것 = 입력(소비), 내놓는 것 = 출력(생산).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: IOSpec
domain_of:
- IOSpec
range: IODirection
required: true

```
</details></div>