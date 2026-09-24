---
search:
  boost: 5.0
---

# Slot: usage_tool 


_통합된 Tool (reported_tool_name 을 정규화해 결정)._



<div data-search-exclude markdown="1">



URI: [eg:usage_tool](http://en-genius.local/onto/usage_tool)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [Tool](Tool.md) |
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





### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:usage_tool |
| native | eg:usage_tool |




## LinkML Source

<details>
```yaml
name: usage_tool
description: 통합된 Tool (reported_tool_name 을 정규화해 결정).
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: Tool
required: true

```
</details></div>