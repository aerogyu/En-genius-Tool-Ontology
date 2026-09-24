---
search:
  boost: 2.0
---


# Enum: ValidationStatus 




_원본 양식 '선택지' 시트의 '검증상태' 목록._



<div data-search-exclude markdown="1">

URI: [eg:ValidationStatus](http://en-genius.local/onto/ValidationStatus)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| 완료 | None |  |
| 진행중 | None |  |
| 미실시 | None |  |
| 해당없음 | None |  |




## Slots

| Name | Description |
| ---  | --- |
| [validation_status](validation_status.md) | 사내 검증 상태 (해석 SW 의 V&V 등) |










## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_list | 검증상태 |




### Schema Source


* from schema: http://en-genius.local/onto/






## LinkML Source

<details>
```yaml
name: ValidationStatus
annotations:
  form_list:
    tag: form_list
    value: 검증상태
description: 원본 양식 '선택지' 시트의 '검증상태' 목록.
from_schema: http://en-genius.local/onto/
rank: 1000
permissible_values:
  완료:
    text: 완료
  진행중:
    text: 진행중
  미실시:
    text: 미실시
  해당없음:
    text: 해당없음

```
</details>

</div>