# 자동 생성 — 직접 고치지 말 것. 원본: schema/engenius_tool.yaml, 명령: python -m engenius_onto schema
from __future__ import annotations

import re
import sys
from datetime import (
    date,
    datetime,
    time
)
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Union
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer
)


metamodel_version = "1.11.0"
version = "0.1.0"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )





class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'eg',
     'default_range': 'string',
     'description': '적재 결과 전체를 한 문서로 묶어 검증·직렬화하기 위한 컨테이너. 온톨로지 본체가 아니므로 OWL·SHACL '
                    '생성 대상이 아니다 (engenius_tool.yaml 만 생성). Pydantic 클래스는 이 파일에서 '
                    '생성해 적재기(M3)가 인스턴스 검증에 쓴다.',
     'id': 'http://en-genius.local/onto/dataset',
     'imports': ['linkml:types', 'engenius_tool'],
     'license': '사내 전용 — 개발은 합성 데이터로만',
     'name': 'engenius_tool_dataset',
     'prefixes': {'eg': {'prefix_prefix': 'eg',
                         'prefix_reference': 'http://en-genius.local/onto/'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'}},
     'source_file': '<repo>/schema/engenius_tool_dataset.yaml',
     'title': 'En-Genius 툴 온톨로지 — 검증용 컨테이너'} )

class ToolKind(str, Enum):
    """
    원본 양식 '선택지' 시트의 '구분' 목록.
    """
    상용 = "상용"
    자체개발 = "자체개발"
    오픈소스 = "오픈소스"
    프리웨어 = "프리웨어"


class PurposeClass(str, Enum):
    """
    원본 양식 '선택지' 시트의 '용도대분류' 목록.
    """
    설계 = "설계"
    해석 = "해석"
    시험·계측 = "시험·계측"
    데이터·형상관리 = "데이터·형상관리"
    문서·협업 = "문서·협업"
    프로젝트관리 = "프로젝트관리"
    기타 = "기타"


class DevPhase(str, Enum):
    """
    원본 양식 '선택지' 시트의 '사용단계' 목록.
    """
    전_단계 = "전 단계"
    개념설계 = "개념설계"
    기본설계 = "기본설계"
    상세설계 = "상세설계"
    개념TILDE기본 = "개념~기본"
    기본TILDE상세 = "기본~상세"
    상세TILDE시험 = "상세~시험"
    시험·인증_이후 = "시험·인증 이후"


class UsageFrequency(str, Enum):
    """
    원본 양식 '선택지' 시트의 '사용빈도' 목록.
    """
    매일 = "매일"
    주_1회_이상 = "주 1회 이상"
    월_1회_이상 = "월 1회 이상"
    분기_이하 = "분기 이하"


class LicenseType(str, Enum):
    """
    원본 양식 '선택지' 시트의 '라이선스형태' 목록.
    """
    영구 = "영구"
    연간_구독 = "연간 구독"
    플로팅LEFT_PARENTHESIS동시사용RIGHT_PARENTHESIS = "플로팅(동시사용)"
    노드락 = "노드락"
    무료 = "무료"
    모름 = "모름"


class RuntimeEnv(str, Enum):
    """
    원본 양식 '선택지' 시트의 '실행환경' 목록.
    """
    Windows_PC = "Windows PC"
    Windows_서버 = "Windows 서버"
    Linux_서버 = "Linux 서버"
    HPC_클러스터 = "HPC 클러스터"
    사내_웹 = "사내 웹"
    외부_클라우드LEFT_PARENTHESISSaaSRIGHT_PARENTHESIS = "외부 클라우드(SaaS)"


class AirgapSupport(str, Enum):
    """
    원본 양식 '선택지' 시트의 '폐쇄망구동' 목록.
    """
    가능 = "가능"
    부분_가능LEFT_PARENTHESIS비고_기재RIGHT_PARENTHESIS = "부분 가능(비고 기재)"
    불가 = "불가"
    모름 = "모름"


class OperationMode(str, Enum):
    """
    원본 양식 '선택지' 시트의 '조작방식' 목록.
    """
    GUI_전용 = "GUI 전용"
    CLI_지원 = "CLI 지원"
    GUIPLUS_SIGNCLI = "GUI+CLI"


class BatchCapability(str, Enum):
    """
    원본 양식 '선택지' 시트의 '배치실행' 목록.
    """
    가능 = "가능"
    불가 = "불가"
    모름 = "모름"


class AutomationInterface(str, Enum):
    """
    원본 양식 '선택지' 시트의 '자동화IF' 목록.
    """
    없음 = "없음"
    CLI_인자 = "CLI 인자"
    내장_스크립팅 = "내장 스크립팅"
    REST_API = "REST API"
    COM·OLE = "COM·OLE"
    SDK·라이브러리 = "SDK·라이브러리"
    파일_폴링 = "파일 폴링"
    모름 = "모름"


class HeadlessCapability(str, Enum):
    """
    원본 양식 '선택지' 시트의 '가능불가모름' 목록.
    """
    가능 = "가능"
    불가 = "불가"
    모름 = "모름"


class AuthMethod(str, Enum):
    """
    원본 양식 '선택지' 시트의 '인증방식' 목록.
    """
    없음 = "없음"
    사내_SSO = "사내 SSO"
    자체_계정 = "자체 계정"
    라이선스_서버 = "라이선스 서버"
    모름 = "모름"


class StorageLocation(str, Enum):
    """
    원본 양식 '선택지' 시트의 '저장위치' 목록.
    """
    PDMLEFT_PARENTHESISENOVIARIGHT_PARENTHESIS = "PDM(ENOVIA)"
    공유폴더 = "공유폴더"
    전용_DB = "전용 DB"
    개인_PC = "개인 PC"
    혼재 = "혼재"


class ValidationStatus(str, Enum):
    """
    원본 양식 '선택지' 시트의 '검증상태' 목록.
    """
    완료 = "완료"
    진행중 = "진행중"
    미실시 = "미실시"
    해당없음 = "해당없음"


class YesNoUnknown(str, Enum):
    """
    원본 양식 '선택지' 시트의 '예아니오모름' 목록.
    """
    예 = "예"
    아니오 = "아니오"
    모름 = "모름"


class Priority(str, Enum):
    """
    원본 양식 '선택지' 시트의 '우선순위' 목록.
    """
    상 = "상"
    중 = "중"
    하 = "하"


class IODirection(str, Enum):
    """
    원본 양식 '선택지' 시트의 '방향' 목록.
    """
    입력LEFT_PARENTHESIS소비RIGHT_PARENTHESIS = "입력(소비)"
    출력LEFT_PARENTHESIS생산RIGHT_PARENTHESIS = "출력(생산)"


class FormatStandard(str, Enum):
    """
    원본 양식 '선택지' 시트의 '포맷표준성' 목록.
    """
    국제·업계_표준 = "국제·업계 표준"
    사내_표준_포맷 = "사내 표준 포맷"
    SW_전용LEFT_PARENTHESIS바이너리RIGHT_PARENTHESIS = "SW 전용(바이너리)"
    모름 = "모름"


class DataNature(str, Enum):
    """
    원본 양식 '선택지' 시트의 '데이터성격' 목록.
    """
    서술형_문서 = "서술형 문서"
    수치·표 = "수치·표"
    number_3DMIDDLE_DOT2D_형상 = "3D·2D 형상"
    이미지 = "이미지"
    코드·스크립트 = "코드·스크립트"
    혼합 = "혼합"


class TransferMethod(str, Enum):
    """
    원본 양식 '선택지' 시트의 '전달방법' 목록.
    """
    파일_저장 = "파일 저장"
    PDM_등록 = "PDM 등록"
    DB_기록 = "DB 기록"
    메일·수기_전달 = "메일·수기 전달"
    타_SW_직접_연동 = "타 SW 직접 연동"


class SecurityGrade(str, Enum):
    """
    원본 양식 '선택지' 시트의 '보안등급' 목록.
    """
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"
    미정 = "미정"


class EntityStatus(str, Enum):
    """
    수명주기 상태 — 삭제 대신 전이 (상위 스키마 v0.2 §6, docs/01 원칙 9).
    """
    활성 = "활성"
    """
    사용 중
    """
    통합됨 = "통합됨"
    """
    다른 노드로 통합됨 (Tool.merged_into)
    """
    폐기 = "폐기"
    """
    더 이상 쓰지 않음 — 과거 참조를 위해 노드는 남긴다
    """


class FeedConfidence(str, Enum):
    """
    공급 연결 신뢰도 (docs/02 7.1).
    """
    낮음 = "낮음"
    """
    겹친 확장자가 전부 범용 확장자
    """
    보통 = "보통"
    """
    범용이 아닌 확장자가 하나 이상 겹침
    """


class ManualBasis(str, Enum):
    """
    수기 구간 판정 근거 (docs/02 7.3).
    """
    전달방법 = "전달방법"
    """
    어느 한쪽의 전달 방법이 수기 전달 값
    """
    비고 = "비고"
    """
    전달 방법은 아니지만 비고에 수작업 키워드 — 보조 신호
    """


class StartGrade(str, Enum):
    """
    착수 등급 (docs/02 7.4).
    """
    A = "A"
    """
    양쪽 모두 자동화 가능
    """
    B = "B"
    """
    한쪽만 자동화 가능
    """
    C = "C"
    """
    둘 다 자동화 불가
    """
    제외 = "제외"
    """
    어느 한쪽이 폐쇄망 구동 불가
    """



class Derived(ConfiguredBaseModel):
    """
    규칙으로 계산한 파생 노드의 provenance 묶음 (docs/02 8장). derived 그래프에만 있다.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'http://en-genius.local/onto/',
         'mixin': True,
         'slot_usage': {'derived_from': {'name': 'derived_from', 'required': True},
                        'generated_at': {'name': 'generated_at', 'required': True},
                        'rule_version': {'name': 'rule_version', 'required': True}}})

    rule_version: str = Field(default=..., description="""이 파생 노드를 만든 규칙 버전 (예 feed_v1).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Derived']} })
    derived_from: list[str] = Field(default=..., description="""파생의 근거가 된 적재 기록 (provenance).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Derived'], 'slot_uri': 'prov:wasDerivedFrom'} })
    generated_at: datetime  = Field(default=..., description="""파생 노드 생성 일시 (provenance).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Derived'], 'slot_uri': 'prov:generatedAtTime'} })


class ResearchField(ConfiguredBaseModel):
    """
    연구소 분야 (조직 노드, RDF 클래스 eg:Field — docs/02 용어). SW기본정보 '담당 부서' 값에서 만든다. 개명은 label 갱신, 통폐합·분할은 새 노드 + succeeded_by (상위 스키마 v0.2 §9). ID 는 레지스트리로 고정. 스키마·파이썬 이름만 ResearchField — 'Field' 는 생성되는 Pydantic 코드에서 pydantic.Field 를 덮어써 모든 클래스가 깨진다 (M1 에서 실측).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'eg:Field',
         'from_schema': 'http://en-genius.local/onto/',
         'slot_usage': {'id': {'name': 'id', 'pattern': '^egid:FLD-\\d{3}$'}}})

    id: str = Field(default=..., description="""노드 식별자. 의미 없는 일련번호 또는 결정적 해시 (docs/02 4장). 예 egid:TOOL-000001""", json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchField',
                       'Tool',
                       'DataCategory',
                       'ToolUsage',
                       'IOSpec',
                       'Feed',
                       'SurveyLoad']} })
    label: str = Field(default=..., description="""사람이 읽는 이름. RDF 에서는 @ko 언어 태그를 붙인다.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchField',
                       'Tool',
                       'DataCategory',
                       'ToolUsage',
                       'IOSpec',
                       'Feed',
                       'SurveyLoad'],
         'slot_uri': 'rdfs:label'} })
    status: Optional[EntityStatus] = Field(default=None, description="""수명주기 상태. 삭제하지 않고 상태를 바꾼다 (상위 스키마 v0.2 §6).""", json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchField', 'Tool']} })
    succeeded_by: Optional[list[str]] = Field(default=None, description="""통폐합·분할로 이 분야를 이어받은 분야.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchField']} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^egid:FLD-\d{3}$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v


class Tool(ConfiguredBaseModel):
    """
    제품 단위 툴 (표기 변형을 통합한 것). 예 ANSYS Fluent. 분야별 사용 기록은 ToolUsage. 통합은 정규화 키 일치일 때만 자동, 유사도 후보는 사람이 판정 (docs/02 6.1).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'http://en-genius.local/onto/',
         'slot_usage': {'id': {'name': 'id', 'pattern': '^egid:TOOL-\\d{6}$'}}})

    id: str = Field(default=..., description="""노드 식별자. 의미 없는 일련번호 또는 결정적 해시 (docs/02 4장). 예 egid:TOOL-000001""", json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchField',
                       'Tool',
                       'DataCategory',
                       'ToolUsage',
                       'IOSpec',
                       'Feed',
                       'SurveyLoad']} })
    label: str = Field(default=..., description="""사람이 읽는 이름. RDF 에서는 @ko 언어 태그를 붙인다.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchField',
                       'Tool',
                       'DataCategory',
                       'ToolUsage',
                       'IOSpec',
                       'Feed',
                       'SurveyLoad'],
         'slot_uri': 'rdfs:label'} })
    status: Optional[EntityStatus] = Field(default=None, description="""수명주기 상태. 삭제하지 않고 상태를 바꾼다 (상위 스키마 v0.2 §6).""", json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchField', 'Tool']} })
    pref_label: str = Field(default=..., description="""대표 이름.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Tool'], 'slot_uri': 'skos:prefLabel'} })
    alt_labels: Optional[list[str]] = Field(default=None, description="""조사에서 나온 변형 표기들 (CQ10).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Tool'], 'slot_uri': 'skos:altLabel'} })
    vendor: Optional[str] = Field(default=None, description="""제조사/개발주체 — 사용 기록들의 응답 중 다수값 (엇갈리면 검토표에 표시).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Tool']} })
    kind: Optional[ToolKind] = Field(default=None, description="""구분 — 사용 기록들의 응답 중 다수값.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Tool']} })
    merged_into: Optional[str] = Field(default=None, description="""사람 판정으로 다른 Tool 에 통합된 경우 그 대상 (status=통합됨과 함께).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Tool']} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^egid:TOOL-\d{6}$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v


class DataCategory(ConfiguredBaseModel):
    """
    데이터 분류 (SW입출력 '분류' 드롭다운 값). 연결 계산 키 ① (docs/02 7.1).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'http://en-genius.local/onto/',
         'slot_usage': {'id': {'name': 'id', 'pattern': '^egid:CAT-\\d{3}$'}}})

    id: str = Field(default=..., description="""노드 식별자. 의미 없는 일련번호 또는 결정적 해시 (docs/02 4장). 예 egid:TOOL-000001""", json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchField',
                       'Tool',
                       'DataCategory',
                       'ToolUsage',
                       'IOSpec',
                       'Feed',
                       'SurveyLoad']} })
    label: str = Field(default=..., description="""사람이 읽는 이름. RDF 에서는 @ko 언어 태그를 붙인다.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchField',
                       'Tool',
                       'DataCategory',
                       'ToolUsage',
                       'IOSpec',
                       'Feed',
                       'SurveyLoad'],
         'slot_uri': 'rdfs:label'} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^egid:CAT-\d{3}$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v


class ToolUsage(ConfiguredBaseModel):
    """
    분야별 SW 응답 1건 = SW기본정보 1행 = SW ID 1개. 같은 툴을 여러 분야가 적으면 여러 개. 입출력(IOSpec)은 분야마다 다르므로 여기에 붙는다.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'http://en-genius.local/onto/',
         'slot_usage': {'id': {'name': 'id', 'pattern': '^egid:USE-\\d{6}$'},
                        'note': {'annotations': {'form_column': {'tag': 'form_column',
                                                                 'value': 'AG'},
                                                 'form_header': {'tag': 'form_header',
                                                                 'value': '비고'},
                                                 'form_sheet': {'tag': 'form_sheet',
                                                                'value': 'SW기본정보'}},
                                 'name': 'note'}}})

    id: str = Field(default=..., description="""노드 식별자. 의미 없는 일련번호 또는 결정적 해시 (docs/02 4장). 예 egid:TOOL-000001""", json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchField',
                       'Tool',
                       'DataCategory',
                       'ToolUsage',
                       'IOSpec',
                       'Feed',
                       'SurveyLoad']} })
    label: str = Field(default=..., description="""사람이 읽는 이름. RDF 에서는 @ko 언어 태그를 붙인다.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchField',
                       'Tool',
                       'DataCategory',
                       'ToolUsage',
                       'IOSpec',
                       'Feed',
                       'SurveyLoad'],
         'slot_uri': 'rdfs:label'} })
    source_row: Optional[int] = Field(default=None, description="""원천 엑셀 시트의 행 번호 (조사 보완 시 원본 행을 찾기 위한 추적 정보).""", json_schema_extra = { "linkml_meta": {'domain_of': ['ToolUsage', 'IOSpec']} })
    loaded_in: Optional[str] = Field(default=None, description="""이 노드를 만든 적재 기록 (provenance).""", json_schema_extra = { "linkml_meta": {'domain_of': ['ToolUsage', 'IOSpec']} })
    note: Optional[str] = Field(default=None, description="""비고 (원문).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'AG'},
                         'form_header': {'tag': 'form_header', 'value': '비고'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage', 'IOSpec']} })
    source_key: str = Field(default=..., description="""SW ID 원문 (분야 약칭이 들어 있어 URI 로 쓰지 않는다 — docs/02 4장).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'A'},
                         'form_header': {'tag': 'form_header', 'value': 'SW ID *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    reported_tool_name: str = Field(default=..., description="""SW명(정식) 원문. 툴 통합 정규화 키의 입력.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'B'},
                         'form_header': {'tag': 'form_header', 'value': 'SW명(정식) *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    usage_tool: str = Field(default=..., description="""통합된 Tool (reported_tool_name 을 정규화해 결정).""", json_schema_extra = { "linkml_meta": {'domain_of': ['ToolUsage']} })
    version: str = Field(default=..., description="""사용 중인 버전 전부 (원문).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'C'},
                         'form_header': {'tag': 'form_header', 'value': '버전 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    reported_vendor: str = Field(default=..., description="""제조사/개발주체 원문. Tool.vendor(다수값)의 입력.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'D'},
                         'form_header': {'tag': 'form_header', 'value': '제조사 / 개발주체 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    reported_kind: ToolKind = Field(default=..., description="""구분 원문. Tool.kind(다수값)의 입력.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'E'},
                         'form_header': {'tag': 'form_header', 'value': '구분 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    purpose_class: PurposeClass = Field(default=..., description="""용도 대분류.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'F'},
                         'form_header': {'tag': 'form_header', 'value': '용도 대분류 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    purpose_detail: str = Field(default=..., description="""용도 상세 원문. 예) 이차유로 1D 유동 네트워크 해석""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'G'},
                         'form_header': {'tag': 'form_header', 'value': '용도 상세 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    phase: DevPhase = Field(default=..., description="""이 SW 를 주로 쓰는 개발 단계 (걸치면 범위로).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'H'},
                         'form_header': {'tag': 'form_header', 'value': '주 사용 단계 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    task_summary: str = Field(default=..., description="""이 SW 로 실제 수행하는 업무 1~2문장.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'I'},
                         'form_header': {'tag': 'form_header',
                                         'value': '주요 사용 업무 요약 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    usage_field: str = Field(default=..., description="""담당 부서 값으로 만든 Field (문자열이 아니라 노드).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'J'},
                         'form_header': {'tag': 'form_header', 'value': '담당 부서 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    user_count: Optional[int] = Field(default=None, description="""사용 인원수 (정수 변환 성공 시).""", ge=0, json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'L'},
                         'form_header': {'tag': 'form_header', 'value': '사용 인원수'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    user_count_raw: Optional[str] = Field(default=None, description="""사용 인원수 원문 — 정수 변환에 실패했을 때만 보존 (경고와 함께).""", json_schema_extra = { "linkml_meta": {'domain_of': ['ToolUsage']} })
    frequency: Optional[UsageFrequency] = Field(default=None, description="""사용 빈도 — 착수 순위 정렬 키 (docs/02 7.4).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'M'},
                         'form_header': {'tag': 'form_header', 'value': '사용 빈도'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    license_type: Optional[LicenseType] = Field(default=None, description="""라이선스 형태.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'N'},
                         'form_header': {'tag': 'form_header', 'value': '라이선스 형태'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    license_count: Optional[int] = Field(default=None, description="""보유 수량 (정수 변환 성공 시).""", ge=0, json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'O'},
                         'form_header': {'tag': 'form_header', 'value': '보유 수량'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    license_count_raw: Optional[str] = Field(default=None, description="""보유 수량 원문 — 정수 변환에 실패했을 때만 보존 (경고와 함께).""", json_schema_extra = { "linkml_meta": {'domain_of': ['ToolUsage']} })
    license_expiry: Optional[str] = Field(default=None, description="""만료 시기 YYYY-MM. 영구면 비움.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'P'},
                         'form_header': {'tag': 'form_header', 'value': '만료 시기'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    runtime_env: RuntimeEnv = Field(default=..., description="""실행 환경 (복수면 대표 1개 + 비고).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'Q'},
                         'form_header': {'tag': 'form_header', 'value': '실행 환경 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    airgap_ok: AirgapSupport = Field(default=..., description="""폐쇄망 구동. '불가'가 낀 수기 구간은 착수 등급 '제외' (docs/02 7.4).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'R'},
                         'form_header': {'tag': 'form_header', 'value': '폐쇄망 구동 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    operation_mode: OperationMode = Field(default=..., description="""조작 방식. 착수 등급 규칙의 입력 (docs/02 7.4).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'S'},
                         'form_header': {'tag': 'form_header', 'value': '조작 방식 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    batch_capable: BatchCapability = Field(default=..., description="""배치/스크립트 실행 — 사람이 클릭하지 않고 실행 가능한가.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'T'},
                         'form_header': {'tag': 'form_header', 'value': '배치/스크립트 실행 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    automation_if: AutomationInterface = Field(default=..., description="""자동화 인터페이스 (대표 1개). 착수 등급 규칙의 입력 (docs/02 7.4).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'U'},
                         'form_header': {'tag': 'form_header', 'value': '자동화 인터페이스 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    automation_detail: Optional[str] = Field(default=None, description="""자동화 상세 — 언어·모듈·예시 — Python API, journal 파일, TCL 등.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'V'},
                         'form_header': {'tag': 'form_header', 'value': '자동화 상세'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    headless: Optional[HeadlessCapability] = Field(default=None, description="""헤드리스 실행 — 화면 없이(서버에서) 실행 가능한가.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'W'},
                         'form_header': {'tag': 'form_header', 'value': '헤드리스 실행'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    auth_method: Optional[AuthMethod] = Field(default=None, description="""인증/로그인 방식 — MCP 연결 시 인증 설계용.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'X'},
                         'form_header': {'tag': 'form_header', 'value': '인증/로그인 방식'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    output_storage: Optional[StorageLocation] = Field(default=None, description="""산출물 주 저장 위치 (상세 경로는 SW입출력 시트).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'Y'},
                         'form_header': {'tag': 'form_header', 'value': '산출물 주 저장 위치'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    validation_status: ValidationStatus = Field(default=..., description="""사내 검증 상태 (해석 SW 의 V&V 등).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'Z'},
                         'form_header': {'tag': 'form_header', 'value': '사내 검증 상태 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    validation_ref: Optional[str] = Field(default=None, description="""검증 기준/문서번호 원문.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'AA'},
                         'form_header': {'tag': 'form_header', 'value': '검증 기준/문서번호'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    certification_use: YesNoUnknown = Field(default=..., description="""감항·인증 업무 사용 — 인증 근거 생산에 쓰이는가.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'AB'},
                         'form_header': {'tag': 'form_header',
                                         'value': '감항·인증 업무 사용 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    automation_wish: str = Field(default=..., description="""자동화 희망 작업 — 반복적이라 AI/에이전트가 대신하면 좋을 일.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'AC'},
                         'form_header': {'tag': 'form_header', 'value': '자동화 희망 작업 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    pain_points: Optional[str] = Field(default=None, description="""현재 수작업·애로 구간 — 타 SW 와 데이터를 주고받을 때 수작업 구간 등.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'AD'},
                         'form_header': {'tag': 'form_header', 'value': '현재 수작업·애로 구간'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    priority_opinion: Optional[Priority] = Field(default=None, description="""우선순위 의견 — 착수 순위 정렬 키 (docs/02 7.4).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'AE'},
                         'form_header': {'tag': 'form_header', 'value': '우선순위 의견'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    roadmap_note: Optional[str] = Field(default=None, description="""대체/업그레이드 계획 — 단종·버전업·전환 예정.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'AF'},
                         'form_header': {'tag': 'form_header', 'value': '대체/업그레이드 계획'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW기본정보'}},
         'domain_of': ['ToolUsage']} })
    feeds: Optional[list[str]] = Field(default=None, description="""(파생) 이 툴사용이 데이터를 공급하는 툴사용 — Feed 의 지름길, 경로 질의(eg:feeds+)용. derived 그래프에만 있다.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ToolUsage', 'Dataset']} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^egid:USE-\d{6}$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v

    @field_validator('license_expiry')
    def pattern_license_expiry(cls, v):
        pattern=re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid license_expiry format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid license_expiry format: {v}"
            raise ValueError(err_msg)
        return v


class IOSpec(ConfiguredBaseModel):
    """
    SW입출력 1행. 한 툴사용이 받거나(입력) 내놓는(출력) 데이터 1종 — 에이전트 단계에서 MCP 함수의 입력·출력 정의가 된다 (docs/01 원칙 6).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'http://en-genius.local/onto/',
         'slot_usage': {'id': {'name': 'id', 'pattern': '^egid:IO-[0-9a-f]{10}$'},
                        'label': {'description': '데이터/산출물 명칭 (data_name 과 같게 둔다).',
                                  'name': 'label'},
                        'note': {'annotations': {'form_column': {'tag': 'form_column',
                                                                 'value': 'M'},
                                                 'form_header': {'tag': 'form_header',
                                                                 'value': '비고'},
                                                 'form_sheet': {'tag': 'form_sheet',
                                                                'value': 'SW입출력'}},
                                 'description': '비고 원문. 수작업 키워드 보조 신호 (docs/02 7.3).',
                                 'name': 'note'}}})

    id: str = Field(default=..., description="""노드 식별자. 의미 없는 일련번호 또는 결정적 해시 (docs/02 4장). 예 egid:TOOL-000001""", json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchField',
                       'Tool',
                       'DataCategory',
                       'ToolUsage',
                       'IOSpec',
                       'Feed',
                       'SurveyLoad']} })
    label: str = Field(default=..., description="""데이터/산출물 명칭 (data_name 과 같게 둔다).""", json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchField',
                       'Tool',
                       'DataCategory',
                       'ToolUsage',
                       'IOSpec',
                       'Feed',
                       'SurveyLoad'],
         'slot_uri': 'rdfs:label'} })
    source_row: Optional[int] = Field(default=None, description="""원천 엑셀 시트의 행 번호 (조사 보완 시 원본 행을 찾기 위한 추적 정보).""", json_schema_extra = { "linkml_meta": {'domain_of': ['ToolUsage', 'IOSpec']} })
    loaded_in: Optional[str] = Field(default=None, description="""이 노드를 만든 적재 기록 (provenance).""", json_schema_extra = { "linkml_meta": {'domain_of': ['ToolUsage', 'IOSpec']} })
    note: Optional[str] = Field(default=None, description="""비고 원문. 수작업 키워드 보조 신호 (docs/02 7.3).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'M'},
                         'form_header': {'tag': 'form_header', 'value': '비고'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW입출력'}},
         'domain_of': ['ToolUsage', 'IOSpec']} })
    owner_source_key: str = Field(default=..., description="""SW ID 원문. SW기본정보에 없으면 고아 입출력 — io_owner 없이 적재하고 경고.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'A'},
                         'form_header': {'tag': 'form_header', 'value': 'SW ID *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW입출력'}},
         'domain_of': ['IOSpec']} })
    io_owner: Optional[str] = Field(default=None, description="""이 입출력을 가진 툴사용 (owner_source_key 로 찾은 것).""", json_schema_extra = { "linkml_meta": {'domain_of': ['IOSpec']} })
    direction: IODirection = Field(default=..., description="""방향 — 이 SW 가 받는 것 = 입력(소비), 내놓는 것 = 출력(생산).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'C'},
                         'form_header': {'tag': 'form_header', 'value': '방향 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW입출력'}},
         'domain_of': ['IOSpec']} })
    data_name: str = Field(default=..., description="""데이터/산출물 명칭 원문. 표기가 제각각이라 연결 키로 쓰지 않는다 (docs/01 원칙 3).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'D'},
                         'form_header': {'tag': 'form_header', 'value': '데이터/산출물 명칭 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW입출력'}},
         'domain_of': ['IOSpec']} })
    io_category: str = Field(default=..., description="""분류. 연결 계산 키 ①.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'E'},
                         'form_header': {'tag': 'form_header', 'value': '분류 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW입출력'}},
         'domain_of': ['IOSpec']} })
    extensions_raw: str = Field(default=..., description="""파일 형식/확장자 원문.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'F'},
                         'form_header': {'tag': 'form_header', 'value': '파일 형식/확장자 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW입출력'}},
         'domain_of': ['IOSpec']} })
    extensions: Optional[list[str]] = Field(default=None, description="""정규화한 확장자 목록 (소문자, 점·별표 제거, 별칭 적용). 연결 계산 키 ② (docs/02 6.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['IOSpec']} })
    inhouse_format: Optional[bool] = Field(default=None, description="""확장자 원문에 '(사내)'·'사내' 표기가 있었는지.""", json_schema_extra = { "linkml_meta": {'domain_of': ['IOSpec']} })
    format_standard: Optional[FormatStandard] = Field(default=None, description="""포맷 표준성.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'G'},
                         'form_header': {'tag': 'form_header', 'value': '포맷 표준성'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW입출력'}},
         'domain_of': ['IOSpec']} })
    data_nature: DataNature = Field(default=..., description="""데이터 성격 — 서술형은 문서 RAG, 수치는 DB 적재 대상.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'H'},
                         'form_header': {'tag': 'form_header', 'value': '데이터 성격 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW입출력'}},
         'domain_of': ['IOSpec']} })
    transfer_method: TransferMethod = Field(default=..., description="""전달 방법. '메일·수기 전달'이면 수기 구간 (docs/02 7.3).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'I'},
                         'form_header': {'tag': 'form_header', 'value': '전달 방법 *'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW입출력'}},
         'domain_of': ['IOSpec']} })
    partner_raw: Optional[str] = Field(default=None, description="""연계 SW명 원문 — 신고된 연결.""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'J'},
                         'form_header': {'tag': 'form_header', 'value': '연계 SW명'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW입출력'}},
         'domain_of': ['IOSpec']} })
    partner_tools: Optional[list[str]] = Field(default=None, description="""연계 SW명 중 Tool 로 해석된 것.""", json_schema_extra = { "linkml_meta": {'domain_of': ['IOSpec']} })
    partner_unresolved: Optional[list[str]] = Field(default=None, description="""연계 SW명 중 Tool 로 해석하지 못한 이름 — 조사 누락 후보 (CQ09).""", json_schema_extra = { "linkml_meta": {'domain_of': ['IOSpec']} })
    storage_path: Optional[str] = Field(default=None, description="""저장 위치/경로 원문 (공유폴더 경로, PDM 폴더명).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'K'},
                         'form_header': {'tag': 'form_header', 'value': '저장 위치/경로'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW입출력'}},
         'domain_of': ['IOSpec']} })
    security_grade: Optional[SecurityGrade] = Field(default=None, description="""보안등급 — 지금은 속성으로만 적재, 접근 통제는 M6 이후 MCP 게이트웨이 (docs/02 11장).""", json_schema_extra = { "linkml_meta": {'annotations': {'form_column': {'tag': 'form_column', 'value': 'L'},
                         'form_header': {'tag': 'form_header', 'value': '보안등급'},
                         'form_sheet': {'tag': 'form_sheet', 'value': 'SW입출력'}},
         'domain_of': ['IOSpec']} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^egid:IO-[0-9a-f]{10}$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v

    @field_validator('extensions')
    def pattern_extensions(cls, v):
        pattern=re.compile(r"^[a-z0-9_+-]+$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid extensions format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid extensions format: {v}"
            raise ValueError(err_msg)
        return v


class Feed(Derived):
    """
    (파생) 규칙으로 계산한 공급 연결 — 출력 명세 from_io 와 입력 명세 to_io 의 분류가 같고 정규화 확장자가 겹칠 때 (docs/02 7.1). 매번 전체 재계산하며 derived 그래프에만 있다.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'http://en-genius.local/onto/',
         'mixins': ['Derived'],
         'slot_usage': {'id': {'name': 'id', 'pattern': '^egid:FEED-[0-9a-f]{10}$'}}})

    id: str = Field(default=..., description="""노드 식별자. 의미 없는 일련번호 또는 결정적 해시 (docs/02 4장). 예 egid:TOOL-000001""", json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchField',
                       'Tool',
                       'DataCategory',
                       'ToolUsage',
                       'IOSpec',
                       'Feed',
                       'SurveyLoad']} })
    label: str = Field(default=..., description="""사람이 읽는 이름. RDF 에서는 @ko 언어 태그를 붙인다.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchField',
                       'Tool',
                       'DataCategory',
                       'ToolUsage',
                       'IOSpec',
                       'Feed',
                       'SurveyLoad'],
         'slot_uri': 'rdfs:label'} })
    from_io: str = Field(default=..., description="""공급 측 출력 명세.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Feed']} })
    to_io: str = Field(default=..., description="""수요 측 입력 명세.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Feed']} })
    supplier: str = Field(default=..., description="""공급 측 툴사용 (from_io 의 io_owner).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Feed']} })
    consumer: str = Field(default=..., description="""수요 측 툴사용 (to_io 의 io_owner).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Feed']} })
    matched_category: str = Field(default=..., description="""양쪽이 일치한 분류.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Feed']} })
    matched_extensions: list[str] = Field(default=..., description="""양쪽이 겹친 정규화 확장자.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Feed']} })
    confidence: FeedConfidence = Field(default=..., description="""겹친 확장자가 전부 범용(config rules.yaml generic_extensions)이면 낮음.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Feed']} })
    declared: bool = Field(default=..., description="""어느 한쪽의 신고(연계 SW명)와 일치하는지 (docs/02 7.2).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Feed']} })
    transfer: Optional[list[TransferMethod]] = Field(default=None, description="""양쪽 명세의 전달 방법.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Feed']} })
    manual: bool = Field(default=..., description="""수기 구간 여부 (전달 방법 기준).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Feed']} })
    manual_basis: Optional[ManualBasis] = Field(default=None, description="""수기 판정 근거 — 전달방법, 또는 비고 키워드만 있는 보조 신호.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Feed']} })
    grade: Optional[StartGrade] = Field(default=None, description="""착수 등급 (수기·변환 구간에만 매긴다, docs/02 7.4).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Feed']} })
    rule_version: str = Field(default=..., description="""이 파생 노드를 만든 규칙 버전 (예 feed_v1).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Derived']} })
    derived_from: list[str] = Field(default=..., description="""파생의 근거가 된 적재 기록 (provenance).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Derived'], 'slot_uri': 'prov:wasDerivedFrom'} })
    generated_at: datetime  = Field(default=..., description="""파생 노드 생성 일시 (provenance).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Derived'], 'slot_uri': 'prov:generatedAtTime'} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^egid:FEED-[0-9a-f]{10}$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v


class SurveyLoad(ConfiguredBaseModel):
    """
    적재 기록 1건 — 원천 조사 파일 1개를 한 번 적재한 것. 같은 실행(run_id)에서 여러 파일을 적재하면 파일마다 1건. 경로는 남기지 않는다 (파일명과 sha256 만).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'http://en-genius.local/onto/',
         'slot_usage': {'id': {'name': 'id',
                               'pattern': '^egid:LOAD-\\d{8}T\\d{6}-\\d{2}$'}}})

    id: str = Field(default=..., description="""노드 식별자. 의미 없는 일련번호 또는 결정적 해시 (docs/02 4장). 예 egid:TOOL-000001""", json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchField',
                       'Tool',
                       'DataCategory',
                       'ToolUsage',
                       'IOSpec',
                       'Feed',
                       'SurveyLoad']} })
    label: str = Field(default=..., description="""사람이 읽는 이름. RDF 에서는 @ko 언어 태그를 붙인다.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ResearchField',
                       'Tool',
                       'DataCategory',
                       'ToolUsage',
                       'IOSpec',
                       'Feed',
                       'SurveyLoad'],
         'slot_uri': 'rdfs:label'} })
    run_id: str = Field(default=..., description="""적재 실행 ID (output/<실행ID> 와 같다).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SurveyLoad']} })
    source_file_name: str = Field(default=..., description="""원천 파일명 (경로 제외).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SurveyLoad']} })
    source_sha256: str = Field(default=..., description="""원천 파일 SHA-256 (소문자 16진수).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SurveyLoad']} })
    loaded_at: datetime  = Field(default=..., description="""적재 일시.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SurveyLoad']} })
    row_count: Optional[int] = Field(default=None, description="""적재한 행 수 (두 시트 합).""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['SurveyLoad']} })
    excluded_row_count: Optional[int] = Field(default=None, description="""제외한 행 수 (예시 행·빈 행 등, 사유는 실행 로그).""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['SurveyLoad']} })
    warning_count: Optional[int] = Field(default=None, description="""적재 중 경고 수 (내용은 실행 로그).""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['SurveyLoad']} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^egid:LOAD-\d{8}T\d{6}-\d{2}$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v

    @field_validator('source_sha256')
    def pattern_source_sha256(cls, v):
        pattern=re.compile(r"^[0-9a-f]{64}$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid source_sha256 format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid source_sha256 format: {v}"
            raise ValueError(err_msg)
        return v


class Dataset(ConfiguredBaseModel):
    """
    적재 1회 분량의 survey 그래프 + (선택) derived 그래프 내용.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'http://en-genius.local/onto/dataset', 'tree_root': True})

    fields: Optional[list[ResearchField]] = Field(default=None, description="""분야 노드.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Dataset']} })
    tools: Optional[list[Tool]] = Field(default=None, description="""통합된 툴 노드.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Dataset']} })
    data_categories: Optional[list[DataCategory]] = Field(default=None, description="""데이터 분류 노드.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Dataset']} })
    tool_usages: Optional[list[ToolUsage]] = Field(default=None, description="""툴사용 노드 (SW기본정보 행).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Dataset']} })
    io_specs: Optional[list[IOSpec]] = Field(default=None, description="""입출력 명세 노드 (SW입출력 행).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Dataset']} })
    survey_loads: Optional[list[SurveyLoad]] = Field(default=None, description="""적재 기록.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Dataset']} })
    feeds: Optional[list[Feed]] = Field(default=None, description="""(파생) 공급 연결.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ToolUsage', 'Dataset']} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
Derived.model_rebuild()
ResearchField.model_rebuild()
Tool.model_rebuild()
DataCategory.model_rebuild()
ToolUsage.model_rebuild()
IOSpec.model_rebuild()
Feed.model_rebuild()
SurveyLoad.model_rebuild()
Dataset.model_rebuild()
