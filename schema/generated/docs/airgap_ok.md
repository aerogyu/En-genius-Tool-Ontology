---
search:
  boost: 5.0
---

# Slot: airgap_ok 


_폐쇄망 구동 (양식 v1.0 에만 있음 — v1.1 에서 열 삭제, v0.3 에서 선택으로). '제외' 등급 규칙은 폐지 결정 (Leo 2026-09-29) — M4 에서 반영._



<div data-search-exclude markdown="1">



URI: [eg:airgap_ok](http://en-genius.local/onto/airgap_ok)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [AirgapSupport](AirgapSupport.md) |
| Domain Of | [ToolUsage](ToolUsage.md) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [ToolUsage](ToolUsage.md) |












## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_sheet | SW기본정보 |
| form_header | 폐쇄망 구동 * |
| form_column | R |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:airgap_ok |
| native | eg:airgap_ok |




## LinkML Source

<details>
```yaml
name: airgap_ok
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 폐쇄망 구동 *
  form_column:
    tag: form_column
    value: R
description: 폐쇄망 구동 (양식 v1.0 에만 있음 — v1.1 에서 열 삭제, v0.3 에서 선택으로). '제외' 등급 규칙은 폐지 결정
  (Leo 2026-09-29) — M4 에서 반영.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: AirgapSupport

```
</details></div>