---
search:
  boost: 5.0
---

# Slot: auth_method 


_인증/로그인 방식 — MCP 연결 시 인증 설계용._



<div data-search-exclude markdown="1">



URI: [eg:auth_method](http://en-genius.local/onto/auth_method)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [AuthMethod](AuthMethod.md) |
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
| form_header | 인증/로그인 방식 |
| form_column | X |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:auth_method |
| native | eg:auth_method |




## LinkML Source

<details>
```yaml
name: auth_method
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 인증/로그인 방식
  form_column:
    tag: form_column
    value: X
description: 인증/로그인 방식 — MCP 연결 시 인증 설계용.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: AuthMethod

```
</details></div>