---
search:
  boost: 5.0
---

# Slot: reported_domain 


_행의 '담당 부서' 원문 (양식 드롭다운 10개 + 목록 밖 파트는 '기타'). 파트의 분류 속성일 뿐 키가 아니다 — config/parts.yaml 의 그 파트 domains 와 다르면 경고만 (v0.3, docs/10)._



<div data-search-exclude markdown="1">



URI: [eg:reported_domain](http://en-genius.local/onto/reported_domain)
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
| form_header | 담당 부서 * |
| form_column | J |
| form_list | 담당부서 |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:reported_domain |
| native | eg:reported_domain |




## LinkML Source

<details>
```yaml
name: reported_domain
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 담당 부서 *
  form_column:
    tag: form_column
    value: J
  form_list:
    tag: form_list
    value: 담당부서
description: 행의 '담당 부서' 원문 (양식 드롭다운 10개 + 목록 밖 파트는 '기타'). 파트의 분류 속성일 뿐 키가 아니다 — config/parts.yaml
  의 그 파트 domains 와 다르면 경고만 (v0.3, docs/10).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: string
required: true

```
</details></div>