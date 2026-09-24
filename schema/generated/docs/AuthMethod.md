---
search:
  boost: 2.0
---


# Enum: AuthMethod 




_원본 양식 '선택지' 시트의 '인증방식' 목록._



<div data-search-exclude markdown="1">

URI: [eg:AuthMethod](http://en-genius.local/onto/AuthMethod)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| 없음 | None |  |
| 사내 SSO | None |  |
| 자체 계정 | None |  |
| 라이선스 서버 | None |  |
| 모름 | None |  |




## Slots

| Name | Description |
| ---  | --- |
| [auth_method](auth_method.md) | 인증/로그인 방식 — MCP 연결 시 인증 설계용 |










## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_list | 인증방식 |




### Schema Source


* from schema: http://en-genius.local/onto/






## LinkML Source

<details>
```yaml
name: AuthMethod
annotations:
  form_list:
    tag: form_list
    value: 인증방식
description: 원본 양식 '선택지' 시트의 '인증방식' 목록.
from_schema: http://en-genius.local/onto/
rank: 1000
permissible_values:
  없음:
    text: 없음
  사내 SSO:
    text: 사내 SSO
  자체 계정:
    text: 자체 계정
  라이선스 서버:
    text: 라이선스 서버
  모름:
    text: 모름

```
</details>

</div>