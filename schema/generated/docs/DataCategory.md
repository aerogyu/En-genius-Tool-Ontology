---
search:
  boost: 10.0
---

# Class: DataCategory 


_데이터 분류 (SW입출력 '분류' 드롭다운 값). 연결 계산 키 ① (docs/02 7.1). ID 는 레지스트리로 고정하고 이번 적재에 없는 분류는 status=폐기 로 계속 낸다 (D7 — v0.2 에서 status 추가)._



<div data-search-exclude markdown="1">



URI: [eg:DataCategory](http://en-genius.local/onto/DataCategory)





```mermaid
 classDiagram
    class DataCategory
    click DataCategory href "../DataCategory/"
      DataCategory : id
        
          
    
        
        
        DataCategory --> "1" Uriorcurie : id
        click Uriorcurie href "../http://www.w3.org/2001/XMLSchema#anyURI/"
    

        
      DataCategory : label
        
          
    
        
        
        DataCategory --> "1" String : label
        click String href "../http://www.w3.org/2001/XMLSchema#string/"
    

        
      DataCategory : status
        
          
    
        
        
        DataCategory --> "0..1" EntityStatus : status
        click EntityStatus href "../EntityStatus/"
    

        
      
```




<!-- no inheritance hierarchy -->

## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [id](id.md) | 1 <br/> [xsd:anyURI](http://www.w3.org/2001/XMLSchema#anyURI) | 노드 식별자 | direct |
| [label](label.md) | 1 <br/> [xsd:string](http://www.w3.org/2001/XMLSchema#string) | 사람이 읽는 이름 | direct |
| [status](status.md) | 0..1 <br/> [EntityStatus](EntityStatus.md) | 수명주기 상태 — 삭제하지 않고 상태를 바꾼다 (docs/01 원칙 9) | direct |





## Usages

| used by | used in | type | used |
| ---  | --- | --- | --- |
| [IOSpec](IOSpec.md) | [io_category](io_category.md) | range | [DataCategory](DataCategory.md) |
| [Feed](Feed.md) | [matched_category](matched_category.md) | range | [DataCategory](DataCategory.md) |












## Identifier and Mapping Information





### Schema Source


* from schema: http://en-genius.local/onto/




## Mappings

| Mapping Type | Mapped Value |
| ---  | ---  |
| self | eg:DataCategory |
| native | eg:DataCategory |






## LinkML Source

<!-- TODO: investigate https://stackoverflow.com/questions/37606292/how-to-create-tabbed-code-blocks-in-mkdocs-or-sphinx -->

### Direct

<details>
```yaml
name: DataCategory
description: 데이터 분류 (SW입출력 '분류' 드롭다운 값). 연결 계산 키 ① (docs/02 7.1). ID 는 레지스트리로 고정하고
  이번 적재에 없는 분류는 status=폐기 로 계속 낸다 (D7 — v0.2 에서 status 추가).
from_schema: http://en-genius.local/onto/
rank: 1000
slots:
- id
- label
- status
slot_usage:
  id:
    name: id
    pattern: ^egid:CAT-[0-9]{3}$

```
</details>

### Induced

<details>
```yaml
name: DataCategory
description: 데이터 분류 (SW입출력 '분류' 드롭다운 값). 연결 계산 키 ① (docs/02 7.1). ID 는 레지스트리로 고정하고
  이번 적재에 없는 분류는 status=폐기 로 계속 낸다 (D7 — v0.2 에서 status 추가).
from_schema: http://en-genius.local/onto/
rank: 1000
slot_usage:
  id:
    name: id
    pattern: ^egid:CAT-[0-9]{3}$
attributes:
  id:
    name: id
    description: 노드 식별자. 의미 없는 일련번호 또는 결정적 해시 (docs/02 4장). 예 egid:TOOL-000001
    from_schema: http://en-genius.local/onto/
    rank: 1000
    identifier: true
    owner: DataCategory
    domain_of:
    - ResearchField
    - Tool
    - DataCategory
    - ToolUsage
    - IOSpec
    - Feed
    - Reconciliation
    - IsolationFinding
    - Handoff
    - SurveyLoad
    range: uriorcurie
    required: true
    pattern: ^egid:CAT-[0-9]{3}$
  label:
    name: label
    description: 사람이 읽는 이름. RDF 에서는 @ko 언어 태그를 붙인다.
    from_schema: http://en-genius.local/onto/
    rank: 1000
    slot_uri: rdfs:label
    owner: DataCategory
    domain_of:
    - ResearchField
    - Tool
    - DataCategory
    - ToolUsage
    - IOSpec
    - Feed
    - Reconciliation
    - IsolationFinding
    - Handoff
    - SurveyLoad
    range: string
    required: true
  status:
    name: status
    description: 수명주기 상태 — 삭제하지 않고 상태를 바꾼다 (docs/01 원칙 9). 없으면 활성.
    from_schema: http://en-genius.local/onto/
    rank: 1000
    ifabsent: string(활성)
    owner: DataCategory
    domain_of:
    - ResearchField
    - Tool
    - DataCategory
    range: EntityStatus

```
</details></div>