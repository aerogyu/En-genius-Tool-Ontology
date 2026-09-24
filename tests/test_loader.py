"""M3 적재 파이프라인 — 엑셀을 읽은 결과가 골든(명세 기반 독립 참조 계산)과 같은지, 그리고 완료 기준.

완료 기준 (docs/03 M3): 합성 파일 적재 성공 / P5·P6·P9·P10 검출 / 재실행해도 FLD·TOOL·USE ID 불변 /
TTL 이 rdflib 와 Fuseki 양쪽에 올라감. 적재기는 엑셀 층(헤더·셀 타입·예시 행 위치)을 직접 읽고, 참조 계산은
명세를 읽는다 — 두 구현이 같은 답을 내는지가 검사의 핵심이다.
"""

from __future__ import annotations

import csv
import datetime as dt
import shutil
import sys
from pathlib import Path

import pytest
import yaml
from rdflib import Dataset, Literal, URIRef
from rdflib.namespace import RDF, RDFS, SKOS

from engenius_onto import synth
from engenius_onto.config import CONFIG_DIR, REPO_ROOT, namespaces
from engenius_onto.loader import Loader, extract_template_examples
from engenius_onto.survey_load import DATA_SETS, apply_review, run_load

GOLDEN = Path(__file__).parent / "golden"
sys.path.insert(0, str(GOLDEN))
import oracle  # noqa: E402

EXPECTED = yaml.safe_load((GOLDEN / "expected.yaml").read_text(encoding="utf-8"))
AGG, CASES, LOADER = EXPECTED["aggregates"], EXPECTED["cases"], EXPECTED["loader"]
ORACLE = oracle.compute(synth.load_spec(), REPO_ROOT)
NS = namespaces()
EG, EGID = NS["eg"], NS["egid"]
NOW = dt.datetime(2026, 9, 24, 12, 0, 0)
SURVEY_DIR, REGISTRY_DIR = DATA_SETS["synthetic"]


def _copy_registry(tmp: Path) -> Path:
    reg = tmp / "registry"
    shutil.copytree(REGISTRY_DIR, reg)
    return reg


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("load")
    return run_load(registry_dir=_copy_registry(tmp), out_root=tmp / "out", now=NOW, shacl=False)


@pytest.fixture(scope="module")
def res(out):
    return out.result


@pytest.fixture(scope="module")
def graph(out):
    ds = Dataset(default_union=True)
    ds.graph(URIRef("http://en-genius.local/graph/survey")).parse(data=out.turtle, format="turtle")
    return ds


def _usage(res, key):
    return next(u for u in res.usages if u.key == key)


def _io(res, key):
    hits = [x for x in res.ios if x.key == key]
    assert len(hits) == 1, (key, sorted(x.key for x in res.ios if x.key.startswith(key.split("/")[0])))
    return hits[0]


# --- 골든 대조 (적재 층) -----------------------------------------------------------------
def test_warnings_equal_golden(res):
    assert sorted(res.warnings) == AGG["warnings"]


def test_per_file_stats_equal_golden(res):
    assert res.per_file() == AGG["loader_per_file"]
    assert len(res.files) == LOADER["files"] and len(res.loaded_files) == LOADER["files_loaded"]
    assert len(res.excluded_rows) == LOADER["excluded_total"]


def test_counts_equal_golden(res):
    c = AGG["counts"]
    assert len(res.usages) == c["usages"] == LOADER["loaded"]["usages"]
    assert len(res.ios) == c["io_specs"] == LOADER["loaded"]["io_rows"]
    assert sum(1 for x in res.ios if x.owner is None) == c["orphan_io_specs"]
    assert len(res.tools) == c["tools"]
    assert len({u.field for u in res.usages}) == c["fields"]
    assert len({x.category for x in res.ios}) == c["categories"]


def test_io_records_equal_oracle(res):
    """입출력 77건 전부 — 키·소유·분류·정규화 확장자·사내 표기·연계 해석이 참조 계산과 같다."""
    def sig(x, owner_key, cat, exts, inhouse, pt, pu):
        return (x, owner_key, cat, tuple(exts), inhouse, tuple(sorted(pt)), tuple(sorted(pu)))

    got = sorted(sig(x.key, x.owner.key if x.owner else None, x.category, x.exts, x.inhouse, x.partner_tools,
                     x.partner_unresolved) for x in res.ios)
    exp = sorted(sig(x.key, x.owner.key if x.owner else None, x.cat, x.exts, x.inhouse, x.partner_tools,
                     x.partner_unresolved) for x in ORACLE["ios"])
    assert got == exp


def test_usage_records_equal_oracle(res):
    got = sorted((u.key, u.tool_key, u.v.get("operation_mode"), u.v.get("automation_if"), u.v.get("airgap_ok"),
                  u.v.get("frequency"), u.v.get("user_count") if u.v.get("user_count") is not None
                  else u.raw.get("user_count"), u.v.get("priority_opinion")) for u in res.usages)
    exp = sorted((u.key, u.tool, u.op, u.auto_if, u.airgap, u.freq, u.users, u.prio) for u in ORACLE["usages"])
    assert got == exp


# --- 사례 (완료 기준 P5·P6·P9·P10) ------------------------------------------------------
def test_P5_tool_merge(res):
    assert {k: g.names for k, g in res.tools.items()} == AGG["tools"]
    assert [[c["a"], c["b"]] for c in res.merge_candidates] == AGG["merge_candidates"]
    assert res.attribute_conflicts == AGG["attribute_conflicts"]
    assert len({u.key for u in res.tools["catia"].usages}) == 2


def test_P6_extensions(res):
    for e in CASES["P6"]["extensions"]:
        x = _io(res, e["io"])
        assert (x.v["extensions_raw"], x.exts, x.inhouse) == (e["raw"], e["normalized"], e.get("inhouse", False))


def test_P9_unresolved_partners(out):
    assert out.log["unresolved_partners"] == AGG["missing_tools"]


def test_P10_example_rows_by_content(res):
    ex = [r for r in res.excluded_rows if r["reason"].startswith("템플릿 예시 행")]
    assert len(ex) == LOADER["template_example_rows_excluded"]
    perf = [r for r in ex if "성능" in r["file"] and r["sheet"] == "SW기본정보"]
    assert {r["row"] for r in perf} == {4, 9}                                   # I15: 위치 무관 (복사본 9행)
    ctrl = [r for r in ex if "제어" in r["file"] and r["sheet"] == "SW입출력"]
    assert [r["row"] for r in ctrl] == [4]                                      # P10-b: 5·6행은 응답
    assert len([x for x in res.ios if x.file.endswith("제어_20260924.xlsx") and x.row in (5, 6)]) == 2
    assert _usage(res, "2차유로(SAS)/SAS-01").v["reported_tool_name"] == "가상-1D네트워크"   # P10-c
    assert not [w for w in res.warnings if "중복 SW ID" in w and "SAS-01" in w]


def test_RESEND_superseded_file_not_loaded(res):
    e = CASES["RESEND"]
    assert {f.name: f.superseded_by for f in res.files}[e["superseded"]] == e["effective"]
    assert not [u for u in res.usages if u.file == e["superseded"]]
    assert e["absent_tool"] not in res.tools


def test_D2_P24_io_node_ids(res):
    ids = {x.key: x.node_id for x in res.ios}
    assert len(set(ids.values())) == len(res.ios) == 77                          # 합쳐진 노드 없음
    for k in CASES["D2"]["io_keys"] + CASES["P24"]["io_keys"]:
        assert ids[k].startswith("IO-")


def test_person_tokens_absent_from_outputs(out):
    texts = [(out.out_dir / n).read_text(encoding="utf-8-sig") for n in ("survey.ttl", "load_log.json", "tool_review.csv")]
    for t in texts:
        for tok in ("홍OO", "수석(내선 9999)", "내선 9998", "내선 1234"):
            assert tok not in t, tok


# --- survey 그래프 --------------------------------------------------------------------
def _count(g, cls):
    return len(set(g.subjects(RDF.type, URIRef(EG + cls))))


def test_graph_node_counts(graph):
    assert (_count(graph, "ToolUsage"), _count(graph, "IOSpec"), _count(graph, "Tool"), _count(graph, "Field"),
            _count(graph, "DataCategory"), _count(graph, "SurveyLoad")) == (34, 77, 22, 8, 8, 8)


def test_graph_labels_and_literals(graph):
    """이름 속성만 @ko, 선택지 값은 태그 없는 문자열, eg:id 트리플 없음 (docs/02 §12)."""
    for p in (RDFS.label, SKOS.prefLabel, SKOS.altLabel):
        assert all(o.language == "ko" for o in graph.objects(None, p))
    assert all(o.language is None for o in graph.objects(None, URIRef(EG + "operation_mode")))
    assert not list(graph.triples((None, URIRef(EG + "id"), None)))
    for key, variants in AGG["tools"].items():                                # 대표 1 + 변형 = 조사 표기 전부
        hits = [s for s in graph.subjects(RDF.type, URIRef(EG + "Tool"))
                if str(graph.value(s, SKOS.prefLabel)) in variants]
        assert len(hits) == 1, key
        names = [str(o) for o in graph.objects(hits[0], SKOS.prefLabel)] + \
            [str(o) for o in graph.objects(hits[0], SKOS.altLabel)]
        assert sorted(names) == variants and len(names) == len(set(names)), key


def test_graph_orphan_and_unresolved(graph):
    q = f"""PREFIX eg: <{EG}>
    SELECT ?k (COUNT(?io) AS ?n) WHERE {{ ?io eg:partner_unresolved ?k }} GROUP BY ?k ORDER BY ?k"""
    assert {str(r.k): int(r.n) for r in graph.query(q)} == {k: v["mentions"] for k, v in AGG["missing_tools"].items()}
    q = f"""PREFIX eg: <{EG}>
    SELECT ?io WHERE {{ ?io a eg:IOSpec ; eg:owner_source_key "TURB-3" FILTER NOT EXISTS {{ ?io eg:io_owner ?u }} }}"""
    assert len(list(graph.query(q))) == 1


def test_survey_loads_provenance(graph, out):
    loads = set(graph.subjects(RDF.type, URIRef(EG + "SurveyLoad")))
    assert {str(s)[len(EGID):] for s in loads} == {f"LOAD-{out.run_id}-{n:02d}" for n in range(1, 9)}
    names = {str(o) for o in graph.objects(None, URIRef(EG + "source_file_name"))}
    assert CASES["RESEND"]["superseded"] not in names and len(names) == 8
    assert all("/" not in n and "\\" not in n for n in names)
    for u in graph.subjects(RDF.type, URIRef(EG + "ToolUsage")):
        assert graph.value(u, URIRef(EG + "loaded_in")) in loads


# --- 레지스트리 (재실행 ID 불변, D7) ------------------------------------------------------
def test_committed_registry_is_stable(out, tmp_path):
    """커밋된 레지스트리로 다시 적재해도 레지스트리가 한 바이트도 바뀌지 않는다 (ID 불변)."""
    for f in REGISTRY_DIR.glob("*.csv"):
        assert (out.out_dir.parent.parent / "registry" / f.name).read_bytes() == f.read_bytes(), f.name


def test_rerun_same_ids_and_same_graph(tmp_path):
    reg = tmp_path / "reg"
    a = run_load(registry_dir=reg, out_root=tmp_path / "a", now=NOW, shacl=False)
    b = run_load(registry_dir=reg, out_root=tmp_path / "b", now=NOW, shacl=False)
    assert a.turtle == b.turtle
    c = run_load(registry_dir=reg, out_root=tmp_path / "c", now=NOW + dt.timedelta(hours=1), shacl=False)
    assert {x.key: x.node_id for x in a.result.ios} == {x.key: x.node_id for x in c.result.ios}
    assert {u.key: u.node_id for u in a.result.usages} == {u.key: u.node_id for u in c.result.usages}


def test_D7_missing_field_retired_not_deleted(tmp_path):
    reg = _copy_registry(tmp_path)
    inp = tmp_path / "survey"
    inp.mkdir()
    for p in SURVEY_DIR.glob("*.xlsx"):
        if "제어" not in p.name:
            shutil.copy(p, inp)
    before = {r["key"]: r["id"] for r in csv.DictReader((reg / "fields.csv").open(encoding="utf-8-sig"))}
    o = run_load(input_dir=inp, registry_dir=reg, out_root=tmp_path / "o", now=NOW, shacl=False)
    rows = {r["key"]: r for r in csv.DictReader((reg / "fields.csv").open(encoding="utf-8-sig"))}
    assert rows["제어"]["status"] == "폐기" and rows["제어"]["id"] == before["제어"]
    ds = Dataset(default_union=True)
    ds.parse(data=o.turtle, format="turtle")
    fld = URIRef(EGID + before["제어"])
    assert (fld, URIRef(EG + "status"), Literal("폐기")) in ds                  # 그래프에서 사라지지 않는다
    tools = {r["key"]: r for r in csv.DictReader((reg / "tools.csv").open(encoding="utf-8-sig"))}
    assert tools["가상제어로직툴"]["status"] == "폐기"
    # 다시 전체 적재하면 같은 ID 로 활성 복귀
    run_load(registry_dir=reg, out_root=tmp_path / "p", now=NOW, shacl=False)
    rows = {r["key"]: r for r in csv.DictReader((reg / "fields.csv").open(encoding="utf-8-sig"))}
    assert rows["제어"]["status"] == "활성" and rows["제어"]["id"] == before["제어"]


# --- 툴 통합 HITL (6.1-5) -------------------------------------------------------------
def test_review_merge_and_distinct(tmp_path, out):
    cfg = tmp_path / "config"
    shutil.copytree(CONFIG_DIR, cfg)
    reg = _copy_registry(tmp_path)
    review = out.out_dir / "tool_review.csv"
    rows = list(csv.DictReader(review.open(encoding="utf-8-sig")))
    assert [(r["툴A_키"], r["툴B_키"]) for r in rows] == [tuple(p) for p in AGG["merge_candidates"]]
    rows[0]["판정(통합/별개)"], rows[0]["대표 이름(통합 시)"] = "통합", "MATLAB"
    decided = tmp_path / "review.csv"
    with decided.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    assert apply_review(decided, cfg) == (1, 0)
    o = run_load(registry_dir=reg, out_root=tmp_path / "o", now=NOW, shacl=False, config_dir=cfg)
    assert "matlabsimulink" not in o.result.tools and len(o.result.tools) == 21
    assert o.result.tools["matlab"].names == ["MATLAB", "MATLAB Simulink"]
    assert o.result.merge_candidates == []
    tools = {r["key"]: r for r in csv.DictReader((reg / "tools.csv").open(encoding="utf-8-sig"))}
    assert tools["matlabsimulink"]["status"] == "통합됨"
    assert tools["matlabsimulink"]["merged_into"] == tools["matlab"]["id"]
    # 별개 판정은 후보에서 빠진다
    cfg2 = tmp_path / "config2"
    shutil.copytree(CONFIG_DIR, cfg2)
    rows[0]["판정(통합/별개)"], rows[0]["대표 이름(통합 시)"] = "별개", ""
    with decided.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    assert apply_review(decided, cfg2) == (0, 1)
    assert Loader(config_dir=cfg2).load(Loader(config_dir=cfg2).discover(SURVEY_DIR)).merge_candidates == []


# --- 설정 ----------------------------------------------------------------------------
def test_template_examples_config_matches_form():
    cfg = yaml.safe_load((CONFIG_DIR / "template_examples.yaml").read_text(encoding="utf-8"))
    assert cfg == extract_template_examples(REPO_ROOT / "reference" / "SW조사양식_EnGenius_v1.0.xlsx")
    assert len(cfg["SW기본정보"]) == 1 and len(cfg["SW입출력"]) == 3


def test_header_alias_config(tmp_path):
    """사내 양식 헤더가 달라도 config/header_map.yaml 만 고치면 된다."""
    from engenius_onto.form_spec import load_form_spec

    cfg = tmp_path / "config"
    shutil.copytree(CONFIG_DIR, cfg)
    (cfg / "header_map.yaml").write_text("SW입출력:\n  extensions_raw: [확장자]\n", encoding="utf-8")
    assert load_form_spec(config_dir=cfg).by_header("SW입출력")["확장자"].slot == "extensions_raw"
    (cfg / "header_map.yaml").write_text("SW입출력:\n  없는슬롯: [x]\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_form_spec(config_dir=cfg)


# --- 검증 (D4) ------------------------------------------------------------------------
EXPECTED_ISSUES = {  # (골든 키, 슬롯) — 적재 경고와 같은 문제를 스키마 층도 잡는다
    ("성능/PERF-02", "license_expiry"), ("시험/TEST-05", "operation_mode"), ("시험/TEST-05", "automation_if"),
    ("제어/MATLAB", "operation_mode"), ("터빈/TURB-03/in/유동장 결과", "transfer_method"),
}


def test_pydantic_row_issues(out):
    assert {(i["key"], i["slot"]) for i in out.schema_issues} == EXPECTED_ISSUES


@pytest.mark.shacl
def test_shacl_report_matches_row_issues(out):
    from engenius_onto.survey_load import run_shacl
    from engenius_onto.shacl_check import find_tools

    if not find_tools():
        pytest.skip("FUSEKI_HOME/JAVA 없음")
    r = run_shacl(out.turtle)
    assert r["ran"] and not r["conforms"]
    ids = {u.node_id: u.key for u in out.result.usages} | {x.node_id: x.key for x in out.result.ios}
    got = {(ids[f[len(EGID):]], p[len(EG):]) for f, p in ((x["focus"], x["path"]) for x in r["results"])}
    assert got == EXPECTED_ISSUES


# --- Fuseki (rdflib 과 같은 결과) --------------------------------------------------------
@pytest.mark.fuseki
def test_survey_loads_into_fuseki_same_as_rdflib(out, graph):
    from engenius_onto.backends import delete_graph, fuseki_alive, push_graph, select
    from engenius_onto.config import fuseki_config

    cfg = fuseki_config()
    if not fuseki_alive(cfg):
        pytest.skip("Fuseki 가 떠 있지 않음")
    gi = "http://en-genius.local/graph/test-survey"
    try:
        n = push_graph(cfg, gi, out.turtle.encode("utf-8"))
        assert n == len(list(graph.quads((None, None, None, None)))) == out.log["counts"]["triples"]
        q = f"""PREFIX eg: <{EG}>
        SELECT ?c (COUNT(?s) AS ?n) WHERE {{ GRAPH <{gi}> {{ ?s a ?c }} }} GROUP BY ?c"""
        remote = {r["c"]: int(r["n"]) for r in select(cfg, q)}
        local = {str(r.c): int(r.n) for r in graph.query(q.replace(f"GRAPH <{gi}> ", "GRAPH ?g "))}
        assert remote == local
    finally:
        delete_graph(cfg, gi)
