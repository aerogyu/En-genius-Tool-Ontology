---
search:
  boost: 2.0
---


# Enum: ReconVerdict 




_계산 vs 신고 대조 판정 (docs/02 7.2, 골든 I13)._



<div data-search-exclude markdown="1">

URI: [eg:ReconVerdict](http://en-genius.local/onto/ReconVerdict)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| 확정 | None | 계산된 연결이 있고 신고와도 일치 |
| 숨은변환 의심 | None | 신고는 있는데 분류·확장자가 맞지 않음 — 중간에 수작업 변환이 있을 가능성 |
| 잠재(신고와 다름) | None | 계산된 연결이 있으나 신고한 상대와 다름 |
| 잠재(연계 미기재) | None | 계산된 연결이 있고 연계 SW명이 비어 있음 |
| 확장자 미기재 | None | 입출력의 확장자가 비어 계산할 수 없음 — 신고 상대마다 |




## Slots

| Name | Description |
| ---  | --- |
| [verdict](verdict.md) | 판정 (docs/02 7 |










## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/






## LinkML Source

<details>
```yaml
name: ReconVerdict
description: 계산 vs 신고 대조 판정 (docs/02 7.2, 골든 I13).
from_schema: http://en-genius.local/onto/
rank: 1000
permissible_values:
  확정:
    text: 확정
    description: 계산된 연결이 있고 신고와도 일치
  숨은변환 의심:
    text: 숨은변환 의심
    description: 신고는 있는데 분류·확장자가 맞지 않음 — 중간에 수작업 변환이 있을 가능성
  잠재(신고와 다름):
    text: 잠재(신고와 다름)
    description: 계산된 연결이 있으나 신고한 상대와 다름
  잠재(연계 미기재):
    text: 잠재(연계 미기재)
    description: 계산된 연결이 있고 연계 SW명이 비어 있음
  확장자 미기재:
    text: 확장자 미기재
    description: 입출력의 확장자가 비어 계산할 수 없음 — 신고 상대마다

```
</details>

</div>