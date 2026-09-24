---
search:
  boost: 5.0
---

# Slot: airgap_ok 


_폐쇄망 구동. '불가'가 낀 수기 구간은 착수 등급 '제외' (docs/02 7.4)._



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
description: 폐쇄망 구동. '불가'가 낀 수기 구간은 착수 등급 '제외' (docs/02 7.4).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: AirgapSupport
required: true

```
</details></div>