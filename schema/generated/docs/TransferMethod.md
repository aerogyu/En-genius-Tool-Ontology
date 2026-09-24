---
search:
  boost: 2.0
---


# Enum: TransferMethod 




_원본 양식 '선택지' 시트의 '전달방법' 목록._



<div data-search-exclude markdown="1">

URI: [eg:TransferMethod](http://en-genius.local/onto/TransferMethod)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| 파일 저장 | None |  |
| PDM 등록 | None |  |
| DB 기록 | None |  |
| 메일·수기 전달 | None |  |
| 타 SW 직접 연동 | None |  |




## Slots

| Name | Description |
| ---  | --- |
| [transfer_method](transfer_method.md) | 전달 방법 |
| [transfer](transfer.md) | 양쪽 명세의 전달 방법 |










## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_list | 전달방법 |




### Schema Source


* from schema: http://en-genius.local/onto/






## LinkML Source

<details>
```yaml
name: TransferMethod
annotations:
  form_list:
    tag: form_list
    value: 전달방법
description: 원본 양식 '선택지' 시트의 '전달방법' 목록.
from_schema: http://en-genius.local/onto/
rank: 1000
permissible_values:
  파일 저장:
    text: 파일 저장
  PDM 등록:
    text: PDM 등록
  DB 기록:
    text: DB 기록
  메일·수기 전달:
    text: 메일·수기 전달
  타 SW 직접 연동:
    text: 타 SW 직접 연동

```
</details>

</div>