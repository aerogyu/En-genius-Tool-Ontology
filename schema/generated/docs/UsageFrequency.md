---
search:
  boost: 2.0
---


# Enum: UsageFrequency 




_원본 양식 '선택지' 시트의 '사용빈도' 목록._



<div data-search-exclude markdown="1">

URI: [eg:UsageFrequency](http://en-genius.local/onto/UsageFrequency)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| 매일 | None |  |
| 주 1회 이상 | None |  |
| 월 1회 이상 | None |  |
| 분기 이하 | None |  |




## Slots

| Name | Description |
| ---  | --- |
| [frequency](frequency.md) | 사용 빈도 — 착수 순위 정렬 키 (docs/02 7 |










## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_list | 사용빈도 |




### Schema Source


* from schema: http://en-genius.local/onto/






## LinkML Source

<details>
```yaml
name: UsageFrequency
annotations:
  form_list:
    tag: form_list
    value: 사용빈도
description: 원본 양식 '선택지' 시트의 '사용빈도' 목록.
from_schema: http://en-genius.local/onto/
rank: 1000
permissible_values:
  매일:
    text: 매일
  주 1회 이상:
    text: 주 1회 이상
  월 1회 이상:
    text: 월 1회 이상
  분기 이하:
    text: 분기 이하

```
</details>

</div>