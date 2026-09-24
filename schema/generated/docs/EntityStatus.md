---
search:
  boost: 2.0
---


# Enum: EntityStatus 




_레지스트리 노드(분야·툴)의 수명주기 — 삭제 대신 전이 (docs/01 원칙 9). 상위 스키마 v0.2 §6 의 산출물 수명주기(작성중→검토중→승인→대체됨|폐기)와는 대상이 다르다: 여기 노드는 사람이 작성·승인하는 산출물이 아니라 조사에서 나온 기준 노드다. 대응은 통합됨 ≈ 대체됨, 폐기 = 폐기._



<div data-search-exclude markdown="1">

URI: [eg:EntityStatus](http://en-genius.local/onto/EntityStatus)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| 활성 | None | 사용 중 |
| 통합됨 | None | 다른 노드로 통합됨 (Tool |
| 폐기 | None | 더 이상 쓰지 않음 — 과거 참조를 위해 노드는 남긴다 |




## Slots

| Name | Description |
| ---  | --- |
| [status](status.md) | 수명주기 상태 — 삭제하지 않고 상태를 바꾼다 (docs/01 원칙 9) |










## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/






## LinkML Source

<details>
```yaml
name: EntityStatus
description: '레지스트리 노드(분야·툴)의 수명주기 — 삭제 대신 전이 (docs/01 원칙 9). 상위 스키마 v0.2 §6 의 산출물
  수명주기(작성중→검토중→승인→대체됨|폐기)와는 대상이 다르다: 여기 노드는 사람이 작성·승인하는 산출물이 아니라 조사에서 나온 기준 노드다. 대응은
  통합됨 ≈ 대체됨, 폐기 = 폐기.'
from_schema: http://en-genius.local/onto/
rank: 1000
permissible_values:
  활성:
    text: 활성
    description: 사용 중
  통합됨:
    text: 통합됨
    description: 다른 노드로 통합됨 (Tool.merged_into)
  폐기:
    text: 폐기
    description: 더 이상 쓰지 않음 — 과거 참조를 위해 노드는 남긴다

```
</details>

</div>