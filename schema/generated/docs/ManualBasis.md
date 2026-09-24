---
search:
  boost: 2.0
---


# Enum: ManualBasis 




_수기 구간 판정 근거 (docs/02 7.3)._



<div data-search-exclude markdown="1">

URI: [eg:ManualBasis](http://en-genius.local/onto/ManualBasis)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| 전달방법 | None | 어느 한쪽의 전달 방법이 수기 전달 값 |
| 비고 | None | 전달 방법은 아니지만 비고에 수작업 키워드 — 보조 신호 |




## Slots

| Name | Description |
| ---  | --- |
| [manual_basis](manual_basis.md) | 수기 판정 근거 — 전달방법, 또는 비고 키워드만 있는 보조 신호 (manual=false) |










## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/






## LinkML Source

<details>
```yaml
name: ManualBasis
description: 수기 구간 판정 근거 (docs/02 7.3).
from_schema: http://en-genius.local/onto/
rank: 1000
permissible_values:
  전달방법:
    text: 전달방법
    description: 어느 한쪽의 전달 방법이 수기 전달 값
  비고:
    text: 비고
    description: 전달 방법은 아니지만 비고에 수작업 키워드 — 보조 신호. 착수 순위에 종류 '비고' 로 표시

```
</details>

</div>