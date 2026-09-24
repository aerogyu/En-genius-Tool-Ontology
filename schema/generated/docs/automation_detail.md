---
search:
  boost: 5.0
---

# Slot: automation_detail 


_자동화 상세 — 언어·모듈·예시 — Python API, journal 파일, TCL 등._



<div data-search-exclude markdown="1">



URI: [eg:automation_detail](http://en-genius.local/onto/automation_detail)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [xsd:string](http://www.w3.org/2001/XMLSchema#string) |
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
| form_header | 자동화 상세 |
| form_column | V |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:automation_detail |
| native | eg:automation_detail |




## LinkML Source

<details>
```yaml
name: automation_detail
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 자동화 상세
  form_column:
    tag: form_column
    value: V
description: 자동화 상세 — 언어·모듈·예시 — Python API, journal 파일, TCL 등.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: string

```
</details></div>