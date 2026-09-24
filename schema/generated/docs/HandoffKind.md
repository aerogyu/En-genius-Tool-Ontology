---
search:
  boost: 2.0
---


# Enum: HandoffKind 




_착수 구간 종류 (docs/02 7.3·7.4, 골든 I3·I4)._



<div data-search-exclude markdown="1">

URI: [eg:HandoffKind](http://en-genius.local/onto/HandoffKind)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| 수기 | None | 전달 방법이 수기인 계산된 연결 (골든 I32 범위) |
| 변환 | None | 숨은변환 의심 — 상대 툴의 사용마다 펼침 |
| 비고 | None | 비고에만 수작업 키워드가 있는 계산된 연결 — 같은 등급 안에서 수기·변환 뒤 |




## Slots

| Name | Description |
| ---  | --- |
| [handoff_kind](handoff_kind.md) | 착수 구간 종류 |










## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/






## LinkML Source

<details>
```yaml
name: HandoffKind
description: 착수 구간 종류 (docs/02 7.3·7.4, 골든 I3·I4).
from_schema: http://en-genius.local/onto/
rank: 1000
permissible_values:
  수기:
    text: 수기
    description: 전달 방법이 수기인 계산된 연결 (골든 I32 범위)
  변환:
    text: 변환
    description: 숨은변환 의심 — 상대 툴의 사용마다 펼침
  비고:
    text: 비고
    description: 비고에만 수작업 키워드가 있는 계산된 연결 — 같은 등급 안에서 수기·변환 뒤

```
</details>

</div>