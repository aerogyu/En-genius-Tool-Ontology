"""M1 스키마 v0.1 — 완료 기준과 설계 결정을 잠근다.

- linkml lint 0건 / 양식 열 ↔ 슬롯 매핑 누락 0 / 선택지 = 원본 양식 (docs/03 M1 완료 기준)
- 커밋된 생성물(OWL·SHACL·매핑표·문서·Pydantic)이 스키마와 일치 (드리프트 방지)
- OWL 2 DL 정리·SHACL 이름 속성 langString (schema_gen 의 후처리)
합성 값만 쓴다 (공개 상용 툴 이름·가상 이름).
"""

from __future__ import annotations

import urllib.parse
import urllib.request

import pytest
import yaml
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from engenius_onto import schema_gen
from engenius_onto.backends import fuseki_alive
from engenius_onto.config import fuseki_config, namespaces

EG = Namespace("http://en-genius.local/onto/")
SH = Namespace("http://www.w3.org/ns/shacl#")
CORE_CLASSES = {"Field", "Tool", "ToolUsage", "IOSpec", "DataCategory", "Feed", "SurveyLoad"}
# 노드를 가리키는 관계만 ObjectProperty — 나머지는 전부 리터럴 (선택지 포함)
OBJECT_PROPERTIES = {
    "usage_field", "usage_tool", "io_owner", "io_category", "partner_tools", "from_io", "to_io",
    "supplier", "consumer", "matched_category", "feeds", "loaded_in", "merged_into", "succeeded_by",
}


@pytest.fixture(scope="module")
def owl():
    return Graph().parse(schema_gen.GEN_DIR / "engenius_tool.owl.ttl")


@pytest.fixture(scope="module")
def shacl():
    return Graph().parse(schema_gen.GEN_DIR / "engenius_tool.shacl.ttl")


# --- M1 완료 기준 ------------------------------------------------------------
def test_lint_clean():
    assert schema_gen.lint() == []


def test_form_mapping_complete():
    assert schema_gen.check_mapping() == []


def test_form_mapping_counts():
    """원본 양식: SW기본정보 33열 = 적재 32 + 제외 1, SW입출력 13열 = 적재 12 + 제외 1."""
    rows = schema_gen.form_mapping()
    excl = schema_gen.excluded_columns()
    xlsx = schema_gen.form_headers_xlsx()
    for sheet, total in (("SW기본정보", 33), ("SW입출력", 13)):
        assert len(xlsx[sheet]) == total
        assert len([r for r in rows if r.sheet == sheet]) + len([e for e in excl if e[0] == sheet]) == total
    assert {h for _, h, _ in excl} == {"실무 문의처(선택)", "SW명(자동)"}


def test_person_column_not_in_schema():
    """'실무 문의처'(인명)는 어떤 슬롯에도 매핑되지 않는다 (절대 규칙 5)."""
    assert not [r for r in schema_gen.form_mapping() if "문의처" in r.header]


def test_enums_match_form_choices():
    assert schema_gen.check_enums_vs_form() == []


def test_generated_files_up_to_date():
    assert schema_gen.run(check=True) == 0


def test_namespaces_config_matches_schema():
    sch = yaml.safe_load(schema_gen.SCHEMA.read_text(encoding="utf-8"))
    ns = namespaces()
    assert sch["prefixes"]["eg"] == ns["eg"] and sch["prefixes"]["egid"] == ns["egid"]
    assert sch["id"] == ns["eg"]


# --- OWL ---------------------------------------------------------------------
def test_owl_core_classes(owl):
    classes = {str(c)[len(EG):] for c in owl.subjects(RDF.type, OWL.Class)
               if isinstance(c, URIRef) and str(c).startswith(str(EG))}
    assert CORE_CLASSES <= classes
    assert classes - CORE_CLASSES == {"Derived"}  # 파생 provenance 믹스인 (Feed 가 상속)


def test_owl_object_properties_are_only_node_links(owl):
    obj = {str(p)[len(EG):] for p in owl.subjects(RDF.type, OWL.ObjectProperty) if str(p).startswith(str(EG))}
    assert obj == OBJECT_PROPERTIES


def test_owl_reserved_vocab_not_redeclared(owl):
    """rdfs:label·skos 이름 속성은 주석 속성 — 데이터 속성 선언·클래스 제약 금지 (OWL 2 DL)."""
    for p in map(URIRef, schema_gen._ANNOTATION_PROPS):
        assert (p, RDF.type, OWL.DatatypeProperty) not in owl
        assert (p, RDF.type, OWL.ObjectProperty) not in owl
        assert not list(owl.subjects(OWL.onProperty, p))


def test_owl_enums_are_literal_datatypes(owl):
    enums = [e for e in owl.subjects(RDF.type, RDFS.Datatype) if isinstance(e, URIRef)]
    assert len(enums) == 25  # 양식 선택지 21 + 스키마 정의 4
    for e in enums:
        assert (e, RDF.type, OWL.Class) not in owl
        eq = owl.value(e, OWL.equivalentClass)
        assert eq is not None and owl.value(eq, OWL.oneOf) is not None


def test_owl_form_annotations_present(owl):
    assert owl.value(EG.source_key, EG.form_header) is not None


# --- SHACL -------------------------------------------------------------------
def test_shacl_labels_accept_language_tags(shacl):
    for p in map(URIRef, schema_gen._ANNOTATION_PROPS):
        shapes = list(shacl.subjects(SH.path, p))
        assert shapes
        for ps in shapes:
            assert shacl.value(ps, SH.datatype) == RDF.langString


def test_shacl_enum_values_are_plain_strings(shacl):
    """선택지 값은 언어 태그 없는 문자열 (적재기가 @ko 를 붙이면 sh:in 에 걸린다)."""
    from rdflib.collection import Collection

    ins = list(shacl.objects(None, SH["in"]))
    assert ins
    for lst in ins:
        for v in Collection(shacl, lst):
            assert v.language is None


# --- Pydantic (적재기 검증용) -----------------------------------------------
def _sample():
    return dict(
        fields=[{"id": "egid:FLD-001", "label": "2차유로(SAS)"}],
        tools=[{"id": "egid:TOOL-000001", "label": "ANSYS Fluent", "pref_label": "ANSYS Fluent",
                "alt_labels": ["Fluent", "ANSYS FLUENT"], "vendor": "ANSYS", "kind": "상용"}],
        data_categories=[{"id": "egid:CAT-001", "label": "해석-결과"}],
        tool_usages=[{
            "id": "egid:USE-000001", "label": "ANSYS Fluent @ 2차유로(SAS)", "source_key": "X-01",
            "reported_tool_name": "ANSYS Fluent 2024R1", "usage_tool": "egid:TOOL-000001",
            "version": "2024R1", "reported_vendor": "ANSYS", "reported_kind": "상용",
            "purpose_class": "해석", "purpose_detail": "합성 예시", "phase": "기본~상세",
            "task_summary": "합성 예시", "usage_field": "egid:FLD-001", "user_count": 3,
            "runtime_env": "Windows PC", "airgap_ok": "부분 가능(비고 기재)", "operation_mode": "GUI+CLI",
            "batch_capable": "가능", "automation_if": "내장 스크립팅", "validation_status": "완료",
            "certification_use": "모름", "automation_wish": "합성 예시", "license_expiry": "2027-03",
        }],
        io_specs=[{
            "id": "egid:IO-0123456789", "label": "유동장 결과", "owner_source_key": "X-01",
            "io_owner": "egid:USE-000001", "direction": "출력(생산)", "data_name": "유동장 결과",
            "io_category": "egid:CAT-001", "extensions_raw": ".cas / .dat", "extensions": ["cas", "dat"],
            "data_nature": "수치·표", "transfer_method": "메일·수기 전달",
        }],
    )


def test_pydantic_accepts_valid_sample():
    from engenius_onto.schema_model import Dataset

    ds = Dataset(**_sample())
    assert ds.tool_usages[0].airgap_ok == "부분 가능(비고 기재)"  # 선택지 값은 문자열로 저장된다 (use_enum_values)
    assert ds.io_specs[0].transfer_method == "메일·수기 전달"


@pytest.mark.parametrize("path, bad", [
    (("tool_usages", "operation_mode"), "CLI만"),          # 선택지에 없는 값
    (("tool_usages", "license_expiry"), "2027/03"),         # YYYY-MM 아님
    (("tool_usages", "user_count"), -1),                    # 음수
    (("tool_usages", "id"), "egid:USE-1"),                  # ID 규칙 위반
    (("io_specs", "extensions"), [".CAS"]),                 # 정규화 안 된 확장자
    (("fields", "id"), "egid:FLD-1"),
])
def test_pydantic_rejects_invalid(path, bad):
    """거부는 적재기(M3)가 잡아 '경고'로 낮춘다 — 여기서는 검출되는지만 본다."""
    from pydantic import ValidationError

    from engenius_onto.schema_model import Dataset

    d = _sample()
    d[path[0]][0][path[1]] = bad
    with pytest.raises(ValidationError):
        Dataset(**d)


def test_pydantic_required_field_missing():
    from pydantic import ValidationError

    from engenius_onto.schema_model import Dataset

    d = _sample()
    del d["tool_usages"][0]["airgap_ok"]
    with pytest.raises(ValidationError):
        Dataset(**d)


# --- Fuseki (Jena 파서로도 읽히는지) -----------------------------------------
@pytest.mark.fuseki
def test_owl_loads_into_fuseki():
    cfg = fuseki_config()
    if not fuseki_alive(cfg):
        pytest.skip("Fuseki 가 떠 있지 않음")
    graph = "http://en-genius.local/graph/test-schema"
    url = f"{cfg.dataset_url}/data?graph=" + urllib.parse.quote(graph, safe="")
    body = (schema_gen.GEN_DIR / "engenius_tool.owl.ttl").read_bytes()
    req = urllib.request.Request(url, data=body, method="PUT",
                                 headers={"Content-Type": "text/turtle; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_s) as r:
            assert r.status in (200, 201, 204)
        q = f"SELECT (COUNT(DISTINCT ?c) AS ?n) WHERE {{ GRAPH <{graph}> {{ ?c a <{OWL.Class}> FILTER(isIRI(?c)) }} }}"
        qurl = f"{cfg.dataset_url}/sparql?query=" + urllib.parse.quote(q)
        import json
        with urllib.request.urlopen(urllib.request.Request(
                qurl, headers={"Accept": "application/sparql-results+json"}), timeout=cfg.timeout_s) as r:
            n = int(json.load(r)["results"]["bindings"][0]["n"]["value"])
        assert n == len(CORE_CLASSES) + 1
    finally:
        try:
            urllib.request.urlopen(urllib.request.Request(url, method="DELETE"), timeout=cfg.timeout_s)
        except Exception:
            pass
