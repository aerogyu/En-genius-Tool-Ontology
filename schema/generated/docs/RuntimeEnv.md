---
search:
  boost: 2.0
---


# Enum: RuntimeEnv 




_원본 양식 '선택지' 시트의 '실행환경' 목록._



<div data-search-exclude markdown="1">

URI: [eg:RuntimeEnv](http://en-genius.local/onto/RuntimeEnv)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| Windows PC | None |  |
| Windows 서버 | None |  |
| Linux 서버 | None |  |
| HPC 클러스터 | None |  |
| 사내 웹 | None |  |
| 외부 클라우드(SaaS) | None |  |




## Slots

| Name | Description |
| ---  | --- |
| [runtime_env](runtime_env.md) | 실행 환경 (복수면 대표 1개 + 비고) |










## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_list | 실행환경 |




### Schema Source


* from schema: http://en-genius.local/onto/






## LinkML Source

<details>
```yaml
name: RuntimeEnv
annotations:
  form_list:
    tag: form_list
    value: 실행환경
description: 원본 양식 '선택지' 시트의 '실행환경' 목록.
from_schema: http://en-genius.local/onto/
rank: 1000
permissible_values:
  Windows PC:
    text: Windows PC
  Windows 서버:
    text: Windows 서버
  Linux 서버:
    text: Linux 서버
  HPC 클러스터:
    text: HPC 클러스터
  사내 웹:
    text: 사내 웹
  외부 클라우드(SaaS):
    text: 외부 클라우드(SaaS)

```
</details>

</div>