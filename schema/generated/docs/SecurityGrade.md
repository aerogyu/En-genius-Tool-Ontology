---
search:
  boost: 2.0
---


# Enum: SecurityGrade 




_원본 양식 '선택지' 시트의 '보안등급' 목록._



<div data-search-exclude markdown="1">

URI: [eg:SecurityGrade](http://en-genius.local/onto/SecurityGrade)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| L1 | None |  |
| L2 | None |  |
| L3 | None |  |
| L4 | None |  |
| L5 | None |  |
| 미정 | None |  |




## Slots

| Name | Description |
| ---  | --- |
| [security_grade](security_grade.md) | 보안등급 — 지금은 속성으로만 적재, 접근 통제는 M6 이후 MCP 게이트웨이 (docs/02 11장) |










## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_list | 보안등급 |




### Schema Source


* from schema: http://en-genius.local/onto/






## LinkML Source

<details>
```yaml
name: SecurityGrade
annotations:
  form_list:
    tag: form_list
    value: 보안등급
description: 원본 양식 '선택지' 시트의 '보안등급' 목록.
from_schema: http://en-genius.local/onto/
rank: 1000
permissible_values:
  L1:
    text: L1
  L2:
    text: L2
  L3:
    text: L3
  L4:
    text: L4
  L5:
    text: L5
  미정:
    text: 미정

```
</details>

</div>