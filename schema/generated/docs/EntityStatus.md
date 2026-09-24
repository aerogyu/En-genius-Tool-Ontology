---
search:
  boost: 2.0
---


# Enum: EntityStatus 




_수명주기 상태 — 삭제 대신 전이 (상위 스키마 v0.2 §6, docs/01 원칙 9)._



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
| [status](status.md) | 수명주기 상태 |










## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/






## LinkML Source

<details>
```yaml
name: EntityStatus
description: 수명주기 상태 — 삭제 대신 전이 (상위 스키마 v0.2 §6, docs/01 원칙 9).
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