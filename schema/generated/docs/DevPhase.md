---
search:
  boost: 2.0
---


# Enum: DevPhase 




_원본 양식 '선택지' 시트의 '사용단계' 목록._



<div data-search-exclude markdown="1">

URI: [eg:DevPhase](http://en-genius.local/onto/DevPhase)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| 전 단계 | None |  |
| 개념설계 | None |  |
| 기본설계 | None |  |
| 상세설계 | None |  |
| 개념~기본 | None |  |
| 기본~상세 | None |  |
| 상세~시험 | None |  |
| 시험·인증 이후 | None |  |
| 개념&기본 | None |  |
| 기본&상세 | None |  |
| 상세&시험 | None |  |




## Slots

| Name | Description |
| ---  | --- |
| [phase](phase.md) | 이 SW 를 주로 쓰는 개발 단계 (걸치면 범위로) |










## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_list | 사용단계 |




### Schema Source


* from schema: http://en-genius.local/onto/






## LinkML Source

<details>
```yaml
name: DevPhase
annotations:
  form_list:
    tag: form_list
    value: 사용단계
description: 원본 양식 '선택지' 시트의 '사용단계' 목록.
from_schema: http://en-genius.local/onto/
rank: 1000
permissible_values:
  전 단계:
    text: 전 단계
  개념설계:
    text: 개념설계
  기본설계:
    text: 기본설계
  상세설계:
    text: 상세설계
  개념~기본:
    text: 개념~기본
  기본~상세:
    text: 기본~상세
  상세~시험:
    text: 상세~시험
  시험·인증 이후:
    text: 시험·인증 이후
  개념&기본:
    text: 개념&기본
  기본&상세:
    text: 기본&상세
  상세&시험:
    text: 상세&시험

```
</details>

</div>