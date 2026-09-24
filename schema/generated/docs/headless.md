---
search:
  boost: 5.0
---

# Slot: headless 


_헤드리스 실행 — 화면 없이(서버에서) 실행 가능한가._



<div data-search-exclude markdown="1">



URI: [eg:headless](http://en-genius.local/onto/headless)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [HeadlessCapability](HeadlessCapability.md) |
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
| form_header | 헤드리스 실행 |
| form_column | W |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:headless |
| native | eg:headless |




## LinkML Source

<details>
```yaml
name: headless
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 헤드리스 실행
  form_column:
    tag: form_column
    value: W
description: 헤드리스 실행 — 화면 없이(서버에서) 실행 가능한가.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: HeadlessCapability

```
</details></div>