---
search:
  boost: 2.0
---


# Enum: FeedConfidence 




_공급 연결 신뢰도 (docs/02 7.1)._



<div data-search-exclude markdown="1">

URI: [eg:FeedConfidence](http://en-genius.local/onto/FeedConfidence)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| 낮음 | None | 겹친 확장자가 전부 범용 확장자 |
| 보통 | None | 범용이 아닌 확장자가 하나 이상 겹침 |




## Slots

| Name | Description |
| ---  | --- |
| [confidence](confidence.md) | 겹친 확장자가 전부 범용(config rules |










## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/






## LinkML Source

<details>
```yaml
name: FeedConfidence
description: 공급 연결 신뢰도 (docs/02 7.1).
from_schema: http://en-genius.local/onto/
rank: 1000
permissible_values:
  낮음:
    text: 낮음
    description: 겹친 확장자가 전부 범용 확장자
  보통:
    text: 보통
    description: 범용이 아닌 확장자가 하나 이상 겹침

```
</details>

</div>