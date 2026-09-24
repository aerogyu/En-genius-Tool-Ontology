"""M2 골든 기대값 — expected.yaml 이 명세·참조 계산(oracle)으로 재현되고, 사례별 기대값이 맞는지."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

from engenius_onto import synth
from engenius_onto.config import REPO_ROOT

GOLDEN = Path(__file__).parent / "golden"
sys.path.insert(0, str(GOLDEN))
import make_expected  # noqa: E402
import oracle  # noqa: E402

EXPECTED = yaml.safe_load((GOLDEN / "expected.yaml").read_text(encoding="utf-8"))
RESULT = oracle.compute(synth.load_spec(), REPO_ROOT)
AGG = oracle.summarize(RESULT)
CASES = EXPECTED["cases"]


def test_expected_file_is_up_to_date():
    """머리말·명세·oracle 을 바꾸고 make_expected.py 를 돌리지 않으면 실패한다."""
    assert (GOLDEN / "expected.yaml").read_text(encoding="utf-8") == make_expected.build()


def test_aggregates_reproduce_from_spec():
    assert AGG == EXPECTED["aggregates"]


def _feed(frm, to):
    hits = [f for f in RESULT["feeds"] if f.o.key == frm and f.i.key == to]
    assert len(hits) == 1, (frm, to, sorted(f.i.key for f in RESULT["feeds"] if f.o.key == frm))
    return hits[0]


def _no_feed(frm, to):
    assert not [f for f in RESULT["feeds"] if f.o.key == frm and f.i.key == to], (frm, to)


def _recon(io_key, tool):
    hits = [v for x, t, v in RESULT["recon"] if x.key == io_key and t == tool]
    assert len(hits) == 1, (io_key, tool, [(x.key, t, v) for x, t, v in RESULT["recon"] if x.key == io_key])
    return hits[0]


def _io(key):
    hits = [x for x in RESULT["ios"] if x.key == key]
    assert len(hits) == 1, (key, sorted(x.key for x in RESULT["ios"] if x.key.startswith(key.split("/")[0])))
    return hits[0]


def _usage(key):
    return next(u for u in RESULT["usages"] if u.key == key)


def _ranking():
    return [(h["supplier"], h["consumer"], h["kind"], h["grade"]) for h in AGG["handoff_ranking"]]


# --- 등급 규칙 (7.4) --------------------------------------------------------------
def test_P1_manual_chain_and_both_cli_hop():
    e = CASES["P1"]
    for m in e["manual_feeds"]:
        f = _feed(m["from"], m["to"])
        assert (f.manual, f.grade, f.confidence, f.declared) == (True, m["grade"], m["confidence"], m["declared"])
    s, c = _usage(e["both_cli_hop"]["supplier"]), _usage(e["both_cli_hop"]["consumer"])
    assert s.op in oracle.AUTO_OPS and c.op in oracle.AUTO_OPS


def test_GRADE_OP_only_operation_mode():
    u = _usage(CASES["GRADE-OP"]["usage"])
    assert u.automatable and u.auto_if in oracle.NON_AUTO_IF   # 자동화 IF 로는 불가 — 조작 방식 분기로만 가능


@pytest.mark.parametrize("case", ["GRADE-C", "GRADE-SUPPLIER-B", "GRADE-SUPPLIER-X", "P8", "P12", "D2"])
def test_manual_feed_grades(case):
    e = CASES[case]["manual_feed"]
    f = _feed(e["from"], e["to"])
    assert f.manual and f.grade == e["grade"]


def test_all_grades_present_in_ranking():
    assert {g for *_, g in _ranking()} == {"A", "B", "C", "제외"}


# --- 대조·변환 (7.2, D1-2) --------------------------------------------------------
@pytest.mark.parametrize("case", ["P2", "P3", "D2", "I13"])
def test_reconciliation_cases(case):
    for e in CASES[case]["reconciliation"]:
        assert _recon(e["io"], e["tool"]) == e["verdict"]


def test_D1_2_conversion_expanded_per_usage():
    got = [(s, c, g) for s, c, k, g in _ranking() if k == "변환"]
    assert got == [(e["supplier"], e["consumer"], e["grade"]) for e in CASES["D1-2"]["conversion_handoffs"]]


def test_P3_undeclared_feed():
    e = CASES["P3"]["feed"]
    f = _feed(e["from"], e["to"])
    assert (f.declared, f.manual) == (e["declared"], e["manual"])


def test_P4_isolation():
    assert AGG["isolated"] == {"no_io": CASES["P4"]["no_io"], "unlinked": CASES["P4"]["unlinked"]}
    assert _io("연소기/COM-01/in/연소 조건").partner_unresolved   # I11: 해석 못 한 연계만 있어도 무연결


def test_P5_tools():
    e = CASES["P5"]
    for key, variants in e["merged"].items():
        assert AGG["tools"][key] == sorted(variants)
    assert len({u.key for u in RESULT["tools"]["catia"]}) == 2      # 표기는 같고 사용이 둘 (D1-2)
    assert AGG["merge_candidates"] == e["candidates_only"]
    c = e["attribute_conflict"]
    assert AGG["attribute_conflicts"][c["tool"]][c["attr"]]["majority"] == c["majority"]


def test_P6_extensions():
    for e in CASES["P6"]["extensions"]:
        io = _io(e["io"])
        assert (io.ext_raw, io.exts, io.inhouse) == (e["raw"], e["normalized"], e.get("inhouse", False))
    for e in CASES["P6"]["feeds_via_normalization"]:
        assert _feed(e["from"], e["to"]).matched == e["matched"]


def test_P7_hubs():
    e = CASES["P7"]
    counts = AGG["hub_partner_counts"]
    top = sorted(counts, key=lambda k: -counts[k])[:2]
    assert sorted(top) == sorted(e["top_hubs"])
    assert min(counts[k] for k in e["top_hubs"]) > sorted(counts.values(), reverse=True)[2]
    for tool, n in e["fields_using"].items():
        assert len({u.field for u in RESULT["tools"][tool]}) == n


def test_P7_ranking_ignores_hub():
    """허브 값을 정렬 키에 넣으면 순서가 바뀐다 — 골든 순서는 허브와 무관한 I18 정렬."""
    hub = AGG["hub_partner_counts_usage"]
    alt = sorted(AGG["handoff_ranking"], key=lambda h: (oracle.GRADE_ORDER[h["grade"]], -hub.get(h["consumer"], 0)))
    assert [h["consumer"] for h in alt] != [h["consumer"] for h in AGG["handoff_ranking"]]


def test_P9_missing():
    for k, v in CASES["P9"]["missing"].items():
        assert AGG["missing_tools"][k] == v


def test_P11_note_signal_both_sides():
    ranked = {(h["supplier"], h["consumer"]) for h in AGG["handoff_ranking"]}
    for e in CASES["P11"]["feeds"]:
        f = _feed(e["from"], e["to"])
        assert (f.manual, f.manual_basis, f.grade) == (e["manual"], e["manual_basis"], e["grade"])
        assert (f.o.owner.key, f.i.owner.key) not in ranked   # I3


def test_D2_two_io_nodes():
    for k in CASES["D2"]["io_keys"]:
        _io(k)


def test_D3_file_scoped_ownership():
    for io_key, tool in CASES["D3"]["owner_of"].items():
        assert _io(io_key).owner.tool == tool


def test_P24_duplicate_rows_kept_with_seq():
    for k in CASES["P24"]["io_keys"]:
        _io(k)


# --- 7.1 연결 조건 ---------------------------------------------------------------
def test_SAME_TOOL_feed_allowed():
    e = CASES["SAME-TOOL"]["feed"]
    f = _feed(e["from"], e["to"])
    assert f.matched == e["matched"] and f.o.owner.tool == f.i.owner.tool and f.o.owner is not f.i.owner


def test_SAME_USAGE_no_feed():
    e = CASES["SAME-USAGE"]["no_feed"]
    o, i = _io(e["from"]), _io(e["to"])
    assert o.cat == i.cat and set(o.exts) & set(i.exts)   # 조건은 맞지만
    _no_feed(e["from"], e["to"])                           # 같은 툴사용이라 연결 없음


def test_PARTNER_MULTI():
    e = CASES["PARTNER-MULTI"]
    assert sorted(_io(e["io"]).partner_tools) == e["partner_tools"]


def test_I13_empty_extension():
    e = CASES["I13"]["no_feed"]
    assert _io(e["from"]).cat == _io(e["to"]).cat
    _no_feed(e["from"], e["to"])
    assert AGG["derive_warnings"] == [f"확장자 미기재: {e['to']}"]


def test_I9_orphan_not_linked():
    orphan = _io(CASES["I9"]["orphan"])
    assert orphan.owner is None
    producers = [x for x in RESULT["ios"] if x.owner and x.direction == "out" and x.cat == orphan.cat
                 and set(x.exts) & set(orphan.exts)]
    assert producers                                        # 맞는 생산자가 있지만
    assert not [f for f in RESULT["feeds"] if f.i is orphan]


def test_I5_tie_broken_by_supplier_key():
    pairs = [(s, c) for s, c, _, _ in _ranking()]
    order = [tuple(p) for p in CASES["I5"]["order"]]
    a, b = (pairs.index(p) for p in order)
    assert b == a + 1
    assert _usage(order[0][0]).sort_key() == _usage(order[1][0]).sort_key()   # 정말 동률


def test_I6_non_integer_users_sorts_lowest():
    pairs = [(s, c) for s, c, _, _ in _ranking()]
    e = CASES["I6"]
    assert pairs.index(tuple(e["before"])) < pairs.index(tuple(e["after"]))


def test_handoff_ranking_order_explained():
    """docs/02 7.4 + I4~I6·I18 정렬 — 손으로 계산한 값."""
    assert _ranking() == [
        ("2차유로(SAS)/SAS-02", "2차유로(SAS)/SAS-01", "수기", "A"),   # 수요 매일·6명
        ("시험/TEST-02", "시험/TEST-01", "수기", "A"),                  # 수요 매일·5명, 공급 매일·2명
        ("연소기/COM-04", "시험/TEST-01", "수기", "A"),                 # 위와 정렬 키 동률 → 공급 키 순 (I5)
        ("터빈/TURB-01", "구조/STR-02", "변환", "A"),                   # 수요 주1회·6명
        ("성능/PERF-01", "2차유로(SAS)/SAS-02", "수기", "A"),           # 수요 주1회·3명
        ("압축기/COM-05", "구조/STR-02", "변환", "B"),                  # 수요 주1회·6명, 공급 3명
        ("2차유로(SAS)/SAS-03", "구조/STR-02", "수기", "B"),            # 공급 인원 원문뿐 → 최소 (I6)
        ("2차유로(SAS)/SAS-01", "2차유로(SAS)/SAS-03", "수기", "B"),    # 수요 인원 원문뿐 → STR-02 수요 행보다 뒤
        ("터빈/TURB-02", "2차유로(SAS)/SAS-03", "수기", "B"),           # 공급 주1회
        ("시험/TEST-05", "2차유로(SAS)/SAS-03", "수기", "C"),
        ("구조/STR-04", "구조/STR-02", "수기", "제외"),                 # 공급 측 폐쇄망 불가
        ("구조/STR-03", "구조/STR-04", "수기", "제외"),                 # 수요 측 폐쇄망 불가
    ]


# --- 적재 층 ----------------------------------------------------------------------
def test_loader_counts_consistent():
    ld = EXPECTED["loader"]
    per = AGG["loader_per_file"]
    assert len(per) == ld["files"]
    assert sum(v["excluded"] for v in per.values()) == ld["excluded_total"]
    c = AGG["counts"]
    assert (ld["loaded"]["usages"], ld["loaded"]["io_rows"], ld["loaded"]["fields"], ld["loaded"]["categories"]) == \
        (c["usages"], c["io_specs"], c["fields"], c["categories"])


def test_expected_warning_kinds_present():
    """loader.cases 에 적은 경고가 참조 계산 경고 목록에 실제로 있다."""
    w = "\n".join(AGG["warnings"])
    for needle in ("매핑 안 된 헤더", "엑셀 숫자 변환 가능성", "날짜 셀", "사용 인원수 정수 변환 실패",
                   "인명 유사 패턴", "선택지 밖 값", "필수값 누락", "SW ID 없는 내용 행", "고아 입출력",
                   "중복 SW ID", "파일 분야 ≠ 담당 부서", "완전 중복 입출력 행", "확장자 매핑 실패"):
        assert needle in w, needle
    assert w.count("인명 유사 패턴") == 3
    assert "설계-2D Layout" in w and "압축기" not in [line for line in AGG["warnings"] if "설계-2D Layout" in line][0]
    assert not any(t in w for t in ("수석(내선 9999)", "내선 9998", "홍OO"))   # 문의처·작성안내 값은 읽지 않는다
