---
search:
  boost: 5.0
---

# Slot: alt_labels 


_조사에서 나온 변형 표기들 (CQ10)._



<div data-search-exclude markdown="1">



URI: [skos:altLabel](http://www.w3.org/2004/02/skos/core#altLabel)
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
| Slot URI | [skos:altLabel](http://www.w3.org/2004/02/skos/core#altLabel) |

### Cardinality and Requirements

| Property | Value |
| --- | --- |
| Multivalued | Yes |
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
| self | skos:altLabel |
| native | eg:alt_labels |




## LinkML Source

<details>
```yaml
name: alt_labels
description: 조사에서 나온 변형 표기들 (CQ10).
from_schema: http://en-genius.local/onto/
rank: 1000
slot_uri: skos:altLabel
owner: Tool
domain_of:
- Tool
range: string
multivalued: true

```
</details></div>