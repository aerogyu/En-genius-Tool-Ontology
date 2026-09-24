---
search:
  boost: 5.0
---

# Slot: pref_label 


_대표 이름._



<div data-search-exclude markdown="1">



URI: [skos:prefLabel](http://www.w3.org/2004/02/skos/core#prefLabel)
<!-- no inheritance hierarchy -->





## Applicable Classes

| Name | Description | Modifies Slot |
| --- | --- | --- |
| [Tool](Tool.md) | 제품 단위 툴 (표기 변형을 통합한 것) |  no  |






## Properties

### Type and Range

| Property | Value |
| --- | --- |
| Range | [xsd:string](http://www.w3.org/2001/XMLSchema#string) |
| Domain Of | [Tool](Tool.md) |
| Slot URI | [skos:prefLabel](http://www.w3.org/2004/02/skos/core#prefLabel) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Required | Yes |
### Slot Characteristics

| Property | Value |
| --- | --- |
| Owner | [Tool](Tool.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | skos:prefLabel |
| native | eg:pref_label |




## LinkML Source

<details>
```yaml
name: pref_label
description: 대표 이름.
from_schema: http://en-genius.local/onto/
rank: 1000
slot_uri: skos:prefLabel
owner: Tool
domain_of:
- Tool
range: string
required: true

```
</details></div>