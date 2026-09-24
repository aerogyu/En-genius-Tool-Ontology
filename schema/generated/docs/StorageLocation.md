---
search:
  boost: 2.0
---


# Enum: StorageLocation 




_원본 양식 '선택지' 시트의 '저장위치' 목록._



<div data-search-exclude markdown="1">

URI: [eg:StorageLocation](http://en-genius.local/onto/StorageLocation)

## Permissible Values
| Value | Meaning | Description |
| --- | --- | --- |
| PDM(ENOVIA) | None |  |
| 공유폴더 | None |  |
| 전용 DB | None |  |
| 개인 PC | None |  |
| 혼재 | None |  |




## Slots

| Name | Description |
| ---  | --- |
| [output_storage](output_storage.md) | 산출물 주 저장 위치 (상세 경로는 SW입출력 시트) |










## Identifier and Mapping Information



### Annotations

| property | value |
| --- | --- |
| form_list | 저장위치 |




### Schema Source


* from schema: http://en-genius.local/onto/






## LinkML Source

<details>
```yaml
name: StorageLocation
annotations:
  form_list:
    tag: form_list
    value: 저장위치
description: 원본 양식 '선택지' 시트의 '저장위치' 목록.
from_schema: http://en-genius.local/onto/
rank: 1000
permissible_values:
  PDM(ENOVIA):
    text: PDM(ENOVIA)
  공유폴더:
    text: 공유폴더
  전용 DB:
    text: 전용 DB
  개인 PC:
    text: 개인 PC
  혼재:
    text: 혼재

```
</details>

</div>