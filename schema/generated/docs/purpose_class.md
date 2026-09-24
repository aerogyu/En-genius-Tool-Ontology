---
search:
  boost: 5.0
---

# Slot: purpose_class 


_용도 대분류._



<div data-search-exclude markdown="1">



URI: [eg:purpose_class](http://en-genius.local/onto/purpose_class)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [PurposeClass](PurposeClass.md) |
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
| form_header | 용도 대분류 * |
| form_column | F |




### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:purpose_class |
| native | eg:purpose_class |




## LinkML Source

<details>
```yaml
name: purpose_class
annotations:
  form_sheet:
    tag: form_sheet
    value: SW기본정보
  form_header:
    tag: form_header
    value: 용도 대분류 *
  form_column:
    tag: form_column
    value: F
description: 용도 대분류.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: PurposeClass
required: true

```
</details></div>