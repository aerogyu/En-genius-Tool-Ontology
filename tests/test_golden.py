"""M2 골든 기대값 — expected.yaml 이 명세와 참조 계산(oracle)으로 재현되고, 사례별 기대값이 맞는지."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

from engenius_onto import synth

GOLDEN = Path(__file__).parent / "golden"
sys.path.insert(0, str(GOLDEN))
import oracle  # noqa: E402

EXPECTED = yaml.safe_load((GOLDEN / "expected.yaml").read_text(encoding="utf-8"))
RESULT = oracle.compute(synth.load_spec())
AGG = oracle.summarize(RESULT)
CASES = EXPECTED["cases"]


def test_aggregates_reproduce_from_spec():
    """명세를 바꾸고 골든을 다시 만들지 않으면 여기서 실패한다."""
    assert AGG == EXPECTED["aggregates"]


def _feed(frm, to):
    hits = [f for f in RESULT["feeds"] if f.o.key == frm and f.i.key == to]
    assert len(hits) == 1, (frm, to, [(f.o.key, f.i.key) for f in RESULT["feeds"] if f.o.key == frm])
    return hits[0]


def _recon(io_key, tool):
    hits = [v for x, t, v in RESULT["recon"] if x.key == io_key and t == tool]
    assert len(hits) == 1, (io_key, tool)
    return hits[0]


def _io(key):
    hits = [x for x in RESULT["ios"] if x.key == key]
    assert len(hits) == 1, key
    return hits[0]


def test_P1_manual_chain():
    for e in CASES["P1"]["manual_feeds"]:
        f = _feed(e["from"], e["to"])
        assert (f.manual, f.grade, f.confidence, f.declared) == (True, e["grade"], e["confidence"], e["declared"])


@pytest.mark.parametrize("case", ["P2", "P3", "D2"])
def test_reconciliation_cases(case):
    for e in CASES[case]["reconciliation"]:
        assert _recon(e["io"], e["tool"]) == e["verdict"]


def test_P2_conversion_handoff():
    e = CASES["P2"]["conversion_handoff"]
    rows = [h for h in AGG["handoff_ranking"] if h["kind"] == "변환"]
    assert rows == [{"supplier": e["supplier"], "consumer": e["consumer"], "kind": "변환", "grade": e["grade"]}]


def test_P3_undeclared_feed():
    e = CASES["P3"]["feed"]
    f = _feed(e["from"], e["to"])
    assert (f.declared, f.manual) == (e["declared"], e["manual"])


def test_P4_isolation():
    assert AGG["isolated"] == {"no_io": CASES["P4"]["no_io"], "unlinked": CASES["P4"]["unlinked"]}


def test_P5_tools():
    e = CASES["P5"]
    for key, variants in e["merged"].items():
        assert AGG["tools"][key] == sorted(variants)
    assert AGG["merge_candidates"] == e["candidates_only"]
    c = e["attribute_conflict"]
    assert AGG["attribute_conflicts"][c["tool"]][c["attr"]]["majority"] == c["majority"]


def test_P6_extensions():
    for e in CASES["P6"]["extensions"]:
        io = _io(e["io"])
        assert (io.ext_raw, io.exts, io.inhouse) == (e["raw"], e["normalized"], e.get("inhouse", False))
    e = CASES["P6"]["feed_via_normalization"]
    assert _feed(e["from"], e["to"]).matched == e["matched"]


def test_P7_hubs_not_in_ranking_keys():
    e = CASES["P7"]
    counts = AGG["hub_partner_counts"]
    top = sorted(counts, key=lambda k: -counts[k])[:2]
    assert sorted(top) == sorted(e["top_hubs"])
    third = sorted(counts.values(), reverse=True)[2]
    assert min(counts[k] for k in e["top_hubs"]) > third
    for tool, n in e["fields_using"].items():
        assert len({u.field for u in RESULT["tools"][tool]}) == n


@pytest.mark.parametrize("case", ["P8", "P12", "D2"])
def test_manual_feed_grades(case):
    e = CASES[case]["manual_feed"]
    f = _feed(e["from"], e["to"])
    assert f.manual and f.grade == e["grade"]


def test_P9_missing():
    e = CASES["P9"]["missing"]
    assert AGG["missing_tools"][e["key"]] == {"mentions": e["mentions"], "fields": e["fields"]}


def test_P11_note_signal():
    e = CASES["P11"]["feed"]
    f = _feed(e["from"], e["to"])
    assert (f.manual, f.manual_basis, f.grade) == (e["manual"], e["manual_basis"], e["grade"])
    ranked = {(h["supplier"], h["consumer"]) for h in AGG["handoff_ranking"]}
    assert (f.o.owner.key, f.i.owner.key) not in ranked   # I3: 착수 순위 제외


def test_D2_two_io_nodes():
    for k in CASES["D2"]["io_keys"]:
        _io(k)


def test_D3_file_scoped_ownership():
    for io_key, tool in CASES["D3"]["owner_of"].items():
        assert _io(io_key).owner.tool == tool


def test_P24_duplicate_rows_kept_with_seq():
    for k in CASES["P24"]["io_keys"]:
        _io(k)


def test_handoff_ranking_order_explained():
    """착수 순위가 docs/02 7.4 정렬(등급 → 수요 빈도·인원·우선순위 → 공급)과 맞는다 — 손 계산 값."""
    got = [(h["supplier"], h["consumer"], h["grade"]) for h in AGG["handoff_ranking"]]
    assert got == [
        ("2차유로(SAS)/SAS-02", "2차유로(SAS)/SAS-01", "A"),   # 수요 매일·6명
        ("시험/TEST-02", "시험/TEST-01", "A"),                  # 수요 매일·5명
        ("터빈/TURB-01", "구조/STR-02", "A"),                   # 수요 주1회·6명 (변환 구간)
        ("성능/PERF-01", "2차유로(SAS)/SAS-02", "A"),           # 수요 주1회·3명
        ("2차유로(SAS)/SAS-01", "2차유로(SAS)/SAS-03", "B"),    # 수요 같음 → 공급 매일
        ("터빈/TURB-02", "2차유로(SAS)/SAS-03", "B"),           # 공급 주1회
        ("구조/STR-03", "구조/STR-04", "제외"),                 # 폐쇄망 구동 불가
    ]


def test_loader_counts_consistent_with_oracle():
    ld = EXPECTED["loader"]["loaded"]
    c = AGG["counts"]
    assert (ld["usages"], ld["io_rows"], ld["fields"], ld["categories"]) == \
        (c["usages"], c["io_specs"], c["fields"], c["categories"])


def test_example_row_count():
    spec = synth.load_spec()
    n = sum(1 + (1 if e.get("io_start_row") == 5 else 3) for e in spec["files"])
    assert n == EXPECTED["loader"]["template_example_rows_excluded"]["total"]
