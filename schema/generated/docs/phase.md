---
search:
  boost: 5.0
---

# Slot: phase 


_이 SW 를 주로 쓰는 개발 단계 (걸치면 범위로)._



<div data-search-exclude markdown="1">



URI: [eg:phase](http://en-genius.local/onto/phase)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [DevPhase](DevPhase.md) |
| Domain Of | [ToolUsage](ToolUsage.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [ToolUsage](ToolUsage.md) |












## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_sheet | SW기본정보 |
| form_header | 주 사용 단계 * |
| form_column | H |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:phase |
| native | eg:phase |




## LinkML Source

<details>
```yaml
name: phase
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 주 사용 단계 *
  form_column:
    tag: form_column
    value: H
description: 이 SW 를 주로 쓰는 개발 단계 (걸치면 범위로).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: DevPhase
required: true

```
</details></div>