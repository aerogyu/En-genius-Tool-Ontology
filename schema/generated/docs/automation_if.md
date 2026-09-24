---
search:
  boost: 5.0
---

# Slot: automation_if 


_자동화 인터페이스 (대표 1개). 착수 등급 규칙의 입력 (docs/02 7.4)._



<div data-search-exclude markdown="1">



URI: [eg:automation_if](http://en-genius.local/onto/automation_if)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [AutomationInterface](AutomationInterface.md) |
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
| form_header | 자동화 인터페이스 * |
| form_column | U |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:automation_if |
| native | eg:automation_if |




## LinkML Source

<details>
```yaml
name: automation_if
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 자동화 인터페이스 *
  form_column:
    tag: form_column
    value: U
description: 자동화 인터페이스 (대표 1개). 착수 등급 규칙의 입력 (docs/02 7.4).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: AutomationInterface
required: true

```
</details></div>