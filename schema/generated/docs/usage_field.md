---
search:
  boost: 5.0
---

# Slot: usage_field 


_이 응답을 낸 파트 (Field 노드). v0.3 부터 파일명의 약칭(docs/10 5장)에서 정한다 — 한 파일에 여러 파트가 든 묶음 파일은 행의 Tool ID 앞부분으로 (config/parts.yaml file_bundles). v0.2 까지는 행의 '담당 부서' 값이었다._



<div data-search-exclude markdown="1">



URI: [eg:usage_field](http://en-genius.local/onto/usage_field)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [ToolUsage](ToolUsage.md) | 분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개 |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [ResearchField](ResearchField.md) |
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
| self | eg:usage_field |
| native | eg:usage_field |




## LinkML Source

<details>
```yaml
name: usage_field
description: 이 응답을 낸 파트 (Field 노드). v0.3 부터 파일명의 약칭(docs/10 5장)에서 정한다 — 한 파일에 여러 파트가
  든 묶음 파일은 행의 Tool ID 앞부분으로 (config/parts.yaml file_bundles). v0.2 까지는 행의 '담당 부서'
  값이었다.
from_schema: http://en-genius.local/onto/
rank: 1000
owner: ToolUsage
domain_of:
- ToolUsage
range: ResearchField
required: true

```
</details></div>