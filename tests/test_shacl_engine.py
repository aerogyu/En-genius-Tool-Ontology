"""생성된 SHACL 을 실제 엔진(Jena SHACL — Fuseki 배포본 jar)으로 돌린다.

M1 검토에서 SHACL 이 한 번도 실행된 적이 없어 무효 제약(eg:id 패턴)이 통과했던 것을 잠근다.
Java 와 Fuseki 가 없으면 skip — FUSEKI_HOME/JAVA_HOME 환경변수, 없으면 개발 PC 배치
(<저장소 상위>/tools/apache-jena-fuseki-*, jdk-*)를 찾는다. 데이터는 전부 합성.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from engenius_onto import schema_gen
from engenius_onto.config import REPO_ROOT
from engenius_onto.shacl_check import find_tools, validate

pytestmark = pytest.mark.shacl

SHAPES = schema_gen.GEN_DIR / "engenius_tool.shacl.ttl"

PREFIXES = """\
@prefix eg: <http://en-genius.local/onto/> .
@prefix egid: <http://en-genius.local/id/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""

# survey ∪ derived 합집합 — 적재기(M3)·도출기(M4)가 만들 모양 그대로
GOOD = PREFIXES + """
egid:LOAD-20260924T120000-01 a eg:SurveyLoad ; rdfs:label "합성 적재"@ko ; eg:run_id "R1" ;
    eg:source_file_name "survey_synthetic.xlsx" ; eg:source_sha256 "%s" ;
    eg:loaded_at "2026-09-24T12:00:00"^^xsd:dateTime .
egid:FLD-001 a eg:Field ; rdfs:label "2차유로(SAS)"@ko ; eg:status "활성" .
egid:FLD-002 a eg:Field ; rdfs:label "성능"@ko .
egid:CAT-001 a eg:DataCategory ; rdfs:label "해석-결과"@ko .
egid:TOOL-000001 a eg:Tool ; rdfs:label "가상-성능덱"@ko ; skos:prefLabel "가상-성능덱"@ko ;
    skos:altLabel "성능덱"@ko ; eg:kind "자체개발" .
egid:TOOL-000002 a eg:Tool ; rdfs:label "가상-1D네트워크"@ko ; skos:prefLabel "가상-1D네트워크"@ko .
egid:USE-000001 a eg:ToolUsage ; rdfs:label "가상-성능덱 @ 성능"@ko ; eg:source_key "PF-01" ;
    eg:reported_tool_name "가상-성능덱 v2" ; eg:usage_tool egid:TOOL-000001 ; eg:version "v2" ;
    eg:reported_vendor "자체개발" ; eg:reported_kind "자체개발" ; eg:purpose_class "해석" ;
    eg:purpose_detail "합성" ; eg:phase "전 단계" ; eg:task_summary "합성" ; eg:usage_field egid:FLD-002 ;
    eg:runtime_env "Windows PC" ; eg:airgap_ok "가능" ; eg:operation_mode "CLI 지원" ;
    eg:batch_capable "가능" ; eg:automation_if "CLI 인자" ; eg:validation_status "완료" ;
    eg:certification_use "아니오" ; eg:automation_wish "합성" ; eg:user_count 4 ;
    eg:license_expiry "2027-03" ; eg:source_row 5 ; eg:loaded_in egid:LOAD-20260924T120000-01 ;
    eg:feeds egid:USE-000002 .
egid:USE-000002 a eg:ToolUsage ; rdfs:label "가상-1D네트워크 @ 2차유로(SAS)"@ko ; eg:source_key "SA-01" ;
    eg:reported_tool_name "가상-1D네트워크" ; eg:usage_tool egid:TOOL-000002 ; eg:version "1.0" ;
    eg:reported_vendor "자체개발" ; eg:reported_kind "자체개발" ; eg:purpose_class "해석" ;
    eg:purpose_detail "합성" ; eg:phase "기본~상세" ; eg:task_summary "합성" ; eg:usage_field egid:FLD-001 ;
    eg:runtime_env "Windows PC" ; eg:airgap_ok "부분 가능(비고 기재)" ; eg:operation_mode "GUI+CLI" ;
    eg:batch_capable "가능" ; eg:automation_if "내장 스크립팅" ; eg:validation_status "진행중" ;
    eg:certification_use "모름" ; eg:automation_wish "합성" .
egid:IO-aaaaaaaaaa a eg:IOSpec ; rdfs:label "경계조건 표"@ko ; eg:owner_source_key "PF-01" ;
    eg:io_owner egid:USE-000001 ; eg:direction "출력(생산)" ; eg:data_name "경계조건 표" ;
    eg:io_category egid:CAT-001 ; eg:extensions_raw ".xlsx" ; eg:extensions "xlsx" ;
    eg:data_nature "수치·표" ; eg:transfer_method "메일·수기 전달" .
egid:IO-bbbbbbbbbb a eg:IOSpec ; rdfs:label "경계조건"@ko ; eg:owner_source_key "SA-01" ;
    eg:io_owner egid:USE-000002 ; eg:direction "입력(소비)" ; eg:data_name "경계조건" ;
    eg:io_category egid:CAT-001 ; eg:extensions_raw "엑셀, tar.gz" ; eg:extensions "xlsx", "tar.gz" ;
    eg:data_nature "수치·표" ; eg:transfer_method "메일·수기 전달" ; eg:partner_raw "성능덱" ;
    eg:partner_tools egid:TOOL-000001 ; eg:inhouse_format false .
egid:FEED-cccccccccc a eg:Feed ; rdfs:label "경계조건 표 → 경계조건"@ko ;
    eg:from_io egid:IO-aaaaaaaaaa ; eg:to_io egid:IO-bbbbbbbbbb ;
    eg:supplier egid:USE-000001 ; eg:consumer egid:USE-000002 ; eg:matched_category egid:CAT-001 ;
    eg:matched_extensions "xlsx" ; eg:confidence "낮음" ; eg:declared true ; eg:manual true ;
    eg:manual_basis "전달방법" ; eg:transfer "메일·수기 전달" ; eg:grade "A" ;
    eg:rule_version "feed_v1" ; prov:wasDerivedFrom egid:LOAD-20260924T120000-01 ;
    prov:generatedAtTime "2026-09-24T12:00:01"^^xsd:dateTime .
""" % ("0" * 64)


@pytest.fixture(scope="module")
def tools():
    t = find_tools()
    if not t:
        dev = REPO_ROOT.parent / "tools"
        fuseki = sorted(dev.glob("apache-jena-fuseki-6.*")) + sorted(dev.glob("apache-jena-fuseki-5.*"))
        jdk = sorted(dev.glob("jdk-*"))
        if fuseki and jdk:
            java = jdk[-1] / "bin" / "java.exe"
            t = find_tools(fuseki[0], str(java) if java.exists() else None)
    if not t:
        pytest.skip("Java·Fuseki 없음 (FUSEKI_HOME/JAVA_HOME 설정 시 실행)")
    return t


def _run(tools, ttl):
    java, jar = tools
    return validate(SHAPES, ttl, java, jar)


def test_synthetic_union_conforms(tools):
    r = _run(tools, GOOD)
    assert r.conforms, r.results


# (치환 전 문자열, 치환 후, 기대 메시지 일부) — 각각 위반 1종
VIOLATIONS = [
    pytest.param("egid:CAT-001 a eg:DataCategory", "<http://example.org/cat> a eg:DataCategory", "Pattern",
                 id="ID-IRI-규칙"),
    pytest.param('rdfs:label "해석-결과"@ko', 'rdfs:label "해석-결과"@en', "LanguageIn", id="이름-@ko-아님"),
    pytest.param('rdfs:label "해석-결과"@ko', 'rdfs:label "해석-결과"', "Datatype", id="이름-태그-없음"),
    pytest.param('eg:operation_mode "GUI+CLI"', 'eg:operation_mode "GUI 와 CLI"', "InConstraint",
                 id="선택지-밖-값"),
    pytest.param('eg:operation_mode "GUI+CLI"', 'eg:operation_mode "GUI+CLI"@ko', "InConstraint",
                 id="선택지-값에-언어태그"),
    pytest.param('eg:airgap_ok "부분 가능(비고 기재)" ;', "", "MinCount", id="필수값-누락"),
    pytest.param("eg:usage_tool egid:TOOL-000002", "eg:usage_tool egid:FLD-001", "Class", id="참조-클래스-불일치"),
    pytest.param('eg:extensions "xlsx", "tar.gz"', 'eg:extensions "xlsx", ".STP"', "Pattern", id="확장자-정규화"),
    pytest.param('eg:inhouse_format false', 'eg:inhouse_format false ; eg:unknown_prop "x"', "Closed",
                 id="닫힌-모양-미정의-속성"),
    pytest.param('eg:source_file_name "survey_synthetic.xlsx"', r'eg:source_file_name "C:\\\\data\\\\s.xlsx"',
                 "Pattern", id="파일명에-경로"),
    pytest.param('prov:generatedAtTime "2026-09-24T12:00:01"^^xsd:dateTime .', ".", "MinCount",
                 id="파생-provenance-누락"),
]


@pytest.mark.parametrize("old, new, expect", VIOLATIONS)
def test_violation_detected(tools, old, new, expect):
    assert old in GOOD
    r = _run(tools, GOOD.replace(old, new, 1))
    assert not r.conforms
    assert any(expect.lower() in msg.lower() for _, _, msg in r.results), r.results


def test_shapes_file_exists():
    assert Path(SHAPES).is_file()
