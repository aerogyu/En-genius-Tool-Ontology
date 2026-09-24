---
search:
  boost: 2.0
---


# Enum: OperationMode 




_원본 양식 '선택지' 시트의 '조작방식' 목록._



<div data-search-exclude markdown="1">

URI: [eg:OperationMode](http://en-genius.local/onto/OperationMode)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| GUI 전용 | None |  |
| CLI 지원 | None |  |
| GUI+CLI | None |  |




## Slots

| Name | Description |
| ---  | --- |
| [operation_mode](operation_mode.md) | 조작 방식 |










## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_list | 조작방식 |




### Schema Source


* from schema: http://en-genius.local/onto/






## LinkML Source

<details>
```yaml
name: OperationMode
annotations:
  form_list:
    tag: form_list
    value: 조작방식
description: 원본 양식 '선택지' 시트의 '조작방식' 목록.
from_schema: http://en-genius.local/onto/
rank: 1000
permissible_values:
  GUI 전용:
    text: GUI 전용
  CLI 지원:
    text: CLI 지원
  GUI+CLI:
    text: GUI+CLI

```
</details>

</div>