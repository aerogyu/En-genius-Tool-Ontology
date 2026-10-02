"""참조 계산(oracle) 경계 사례 — M2 검토에서 찾은 잠재 결함이 다시 생기지 않게 잠근다.

골든 명세에는 없지만 실데이터에서 나올 수 있는 표기들. M3·M4 구현도 같은 입력에 같은 답을 내야 한다
(expected.yaml interpretations 의 해당 번호).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "golden"))
import oracle  # noqa: E402


@pytest.mark.parametrize("raw, exts, inhouse, bad", [
    ("n/a", [], False, []),                        # I16 셀 전체 빈 값 — '/' 로 쪼개 a·n 이 되면 안 된다
    ("N/A", [], False, []),
    ("해당 없음", [], False, []),
    (".dat(ASCII)", ["dat"], False, []),           # I12 사내 아닌 괄호 주석은 떼기만
    ("STEP(AP214)", ["stp"], False, []),
    ("dat(사내용)", ["dat"], True, []),
    (".dat (사내 포맷)", ["dat"], True, []),
    ("비사내 csv", ["csv"], False, ["비사내"]),     # 단어 중간 '사내' 는 사내 표기가 아니다
    ("csvㆍxlsx", ["csv", "xlsx"], False, []),     # I17 가운뎃점 변형
    ("csv・xlsx", ["csv", "xlsx"], False, []),
    ("tar.gz", ["tar.gz"], False, []),
    ("cas.h5, dat.h5", ["cas.h5", "dat.h5"], False, []),
])
def test_extension_normalization(raw, exts, inhouse, bad):
    assert oracle.normalize_extensions(raw) == (exts, inhouse, bad)


@pytest.mark.parametrize("raw, parts", [
    ("CATIA，NX", ["CATIA", "NX"]),                 # 전각 쉼표 — NFKC 후 분리
    ("CATIA\nNX", ["CATIA", "NX"]),
    ("CATIAㆍNX", ["CATIA", "NX"]),
    ("-", []),                                     # I16 빈 값 토큰은 버린다 (CQ09 후보가 되면 안 됨)
    ("없음", []),
    ("(사내툴)", []),                               # 정규화 키가 비는 조각
    ("", []),
])
def test_partner_split(raw, parts):
    assert oracle.split_partners(raw) == parts


@pytest.mark.parametrize("name, vendor, key", [
    ("Tecplot", "Tecplot", "tecplot"),             # I14 툴명 = 제조사명
    ("ANSYS Fluent 2024R1", "ANSYS", "fluent"),
    ("CATIA V5", "Dassault Systèmes", "catia"),
    ("Microsoft Excel", "Microsoft", "excel"),
    ("가상-1D네트워크", "자체개발", "가상1d네트워크"),
    ("C++", None, "cpp"),                          # I2 토큰 치환 (docs/09 #16 A) — C++·C#·C 가 'c' 로 합쳐지지 않는다
    ("C#", "Microsoft", "csharp"),
    ("Visual C++", "Microsoft", "visualcpp"),
    ("Excel 2016", "Microsoft", "excel"),
    ("CFX 2024 R1", "ANSYS", "cfx"),
    ("자체개발 유량계산기", "자체개발", "자체개발유량계산기"),   # I34 범용 제조사는 접두로 떼지 않는다 (Leo Q3(b))
    ("사내 개발 계산기", "사내개발", "사내개발계산기"),
])
def test_tool_key(name, vendor, key):
    assert oracle.tool_key(name, vendor) == key


@pytest.mark.parametrize("name, generic", [("자체개발", True), ("자체 개발", True), ("(자체 매크로)", True), ("-", True),
                                           ("in-house", True), ("가상-1D네트워크", False), ("Excel", False)])
def test_generic_tool_names(name, generic):
    """I34: 빈 키·범용 이름은 행별 키 — 통합 대상이 아니다."""
    assert oracle.is_generic_key(oracle.tool_key(name)) is generic


def test_generic_names_get_row_keys_and_no_candidates():
    """I34 거울: '자체개발' 두 행은 서로 다른 '미상:' 키이고 통합 후보에 오르지 않는다."""
    r = oracle.compute(_spec(
        [{"sw_id": "A-1", "name": "자체개발", "vendor": "자체개발"}, {"sw_id": "A-2", "name": "(자체 매크로)", "vendor": "v"},
         {"sw_id": "A-3", "name": "C", "vendor": "v"}, {"sw_id": "A-4", "name": "C++", "vendor": "v"}], []), REPO)
    assert {u.sw_id: u.tool for u in r["usages"]} == {"A-1": "미상:성능/A-1", "A-2": "미상:성능/A-2", "A-3": "c", "A-4": "cpp"}
    assert r["candidates"] == []                                               # 'c' ⊂ 'cpp' 는 3자 미만 — 후보 아님


def test_vendor_prefix_absorbed_into_existing_key():
    """I1 거울 (Q3(a)): 제조사 칸이 비어도 다른 행의 제조사 접두를 떼면 기존 키와 같으면 그 툴."""
    r = oracle.compute(_spec(
        [{"sw_id": "A-1", "name": "Fluent", "vendor": "ANSYS"}, {"sw_id": "A-2", "name": "ANSYS Fluent", "vendor": ""},
         {"sw_id": "A-3", "name": "ANSYS Fluent Meshing", "vendor": ""}], []), REPO)
    assert {u.sw_id: u.tool for u in r["usages"]} == {"A-1": "fluent", "A-2": "fluent", "A-3": "ansysfluentmeshing"}


def test_vendor_prefix_absorption_is_grouped():
    """I1 거울: 셋이 얽혀도({altairfluent, ansysfluent, fluent}) 한 그룹 — 레지스트리를 모르는 참조 계산은 가장 짧은 키(접두를 뗀 쪽)."""
    r = oracle.compute(_spec(
        [{"sw_id": "A-1", "name": "Altair Fluent", "vendor": ""}, {"sw_id": "A-2", "name": "ANSYS Fluent", "vendor": ""},
         {"sw_id": "A-3", "name": "Fluent", "vendor": "ANSYS"}, {"sw_id": "A-4", "name": "HyperMesh", "vendor": "Altair"}], []), REPO)
    assert {u.sw_id: u.tool for u in r["usages"]} == {"A-1": "fluent", "A-2": "fluent", "A-3": "fluent", "A-4": "hypermesh"}


def test_vendor_absorption_skips_group_with_distinct_pair():
    """I1 거울 (3차 재검토): 별개 판정 쌍(명세 distinct)이 제3의 키를 거쳐 한 그룹에 들면 그 그룹은 흡수하지 않는다 — 툴 4, 경고 1.
    직접 쌍이 별개면 그 쌍만 묶지 않고 나머지는 흡수한다."""
    rows = [{"sw_id": "A-1", "name": "Altair Fluent", "vendor": ""}, {"sw_id": "A-2", "name": "ANSYS Fluent", "vendor": ""},
            {"sw_id": "A-3", "name": "Fluent", "vendor": "ANSYS"}, {"sw_id": "A-4", "name": "HyperMesh", "vendor": "Altair"}]
    spec = {**_spec(rows, []), "distinct": [["altairfluent", "ansysfluent"]]}
    r = oracle.compute(spec, REPO)
    assert {u.sw_id: u.tool for u in r["usages"]} == {"A-1": "altairfluent", "A-2": "ansysfluent", "A-3": "fluent", "A-4": "hypermesh"}
    assert len(r["tools"]) == 4
    assert [w for w in r["warnings"] if w.startswith("제조사 접두")] == ["제조사 접두 흡수와 별개 판정이 충돌: altairfluent / ansysfluent — 흡수하지 않음"]
    spec = {**_spec(rows, []), "distinct": [["altairfluent", "fluent"]]}                 # 직접 쌍 — 그 쌍만 빠지고 ansysfluent 는 흡수
    r = oracle.compute(spec, REPO)
    assert {u.sw_id: u.tool for u in r["usages"]} == {"A-1": "altairfluent", "A-2": "fluent", "A-3": "fluent", "A-4": "hypermesh"}
    assert not any(w.startswith("제조사 접두") for w in r["warnings"])


def test_generic_vendor_never_absorbs():
    """I1·I34 거울 (Q3(b)): 범용 제조사('자체개발')는 접두 흡수·연계 SW명 해석에 쓰지 않는다 — 자체개발 툴은 자동 통합하지 않는다."""
    r = oracle.compute(_spec(
        [{"sw_id": "A-1", "name": "유량계산기", "vendor": "자체개발"}, {"sw_id": "A-2", "name": "자체개발 유량계산기", "vendor": "자체개발"},
         {"sw_id": "A-3", "name": "자체개발 유량계산기", "vendor": "in-house"}],
        [{"sw_id": "A-1", "dir": "in", "name": "d", "cat": "해석-결과", "ext": "dat", "partner": "자체개발 유량계산기"}]), REPO)
    assert {u.sw_id: u.tool for u in r["usages"]} == {"A-1": "유량계산기", "A-2": "자체개발유량계산기", "A-3": "자체개발유량계산기"}
    assert r["ios"][0].partner_tools == {"자체개발유량계산기"} and r["ios"][0].partner_unresolved == []
    assert oracle.survey_vendors(r["usages"]) == []


def test_vendor_absorption_is_order_independent():
    """I1: 흡수 쌍은 키 집합 위에서 정하므로 행 순서를 바꿔도 같은 툴 키."""
    rows = [{"sw_id": "A-1", "name": "Fluent", "vendor": "ANSYS"}, {"sw_id": "A-2", "name": "ANSYS Fluent", "vendor": ""},
            {"sw_id": "A-3", "name": "ANSYS Fluent", "vendor": "다른 회사"}]
    a = oracle.compute(_spec(rows, []), REPO)
    b = oracle.compute(_spec(rows[::-1], []), REPO)
    assert {u.sw_id: u.tool for u in a["usages"]} == {u.sw_id: u.tool for u in b["usages"]} == {"A-1": "fluent", "A-2": "fluent", "A-3": "fluent"}


def _spec(usages, ios):
    return {
        "template": "reference/SW조사양식_EnGenius_v1.0.xlsx", "file_name": "SW조사_{field}_{date}.xlsx",
        "file_date": "20260101", "extra_categories": [],
        "defaults": {"usage": {"purpose": "해석", "detail": "x", "phase": "전 단계", "task": "x", "env": "Windows PC",
                               "airgap": "가능", "op": "GUI+CLI", "batch": "가능", "auto_if": "내장 스크립팅",
                               "vv": "해당없음", "cert": "아니오", "wish": "x", "kind": "상용", "version": "1"},
                     "io": {"nature": "수치·표", "transfer": "파일 저장"}},
        "files": [{"field": "성능", "usages": usages, "ios": ios}],
    }


REPO = Path(__file__).resolve().parents[1]


def test_note_keywords_checked_per_side():
    """두 비고를 이어 붙이면 '계수'+'기록' 경계에 '수기' 가 생긴다 — 비고마다 따로 본다."""
    r = oracle.compute(_spec(
        [{"sw_id": "A-1", "name": "가상-툴A", "vendor": "v"}, {"sw_id": "A-2", "name": "가상-툴B", "vendor": "v"}],
        [{"sw_id": "A-1", "dir": "out", "name": "d", "cat": "해석-결과", "ext": "dat", "note": "유량 계수"},
         {"sw_id": "A-2", "dir": "in", "name": "d", "cat": "해석-결과", "ext": "dat", "note": "기록 보관"}]), REPO)
    assert r["feeds"][0].manual_basis is None


def test_conversion_never_pairs_usage_with_itself():
    """I26: 자기 툴을 연계로 적은 입력의 변환 구간에 자기 자신 쌍이 없다."""
    r = oracle.compute(_spec(
        [{"sw_id": "A-1", "name": "Excel", "vendor": "Microsoft"}, {"sw_id": "B-1", "name": "Excel", "vendor": "Microsoft"}],
        [{"sw_id": "A-1", "dir": "in", "name": "표", "cat": "보고서·문서", "ext": "xlsx", "partner": "Excel"},
         {"sw_id": "B-1", "dir": "out", "name": "그림", "cat": "보고서·문서", "ext": "png"}]), REPO)
    pairs = {(h[0].key, h[1].key) for h in r["ranked"]}
    assert pairs == {("성능/B-1", "성능/A-1")}


def test_empty_extension_with_partner_is_not_hidden_conversion():
    """I13: 확장자가 비면 '숨은변환 의심' 이 아니라 '확장자 미기재', 변환 구간 없음."""
    r = oracle.compute(_spec(
        [{"sw_id": "A-1", "name": "가상-툴A", "vendor": "v"}, {"sw_id": "A-2", "name": "가상-툴B", "vendor": "v"}],
        [{"sw_id": "A-1", "dir": "out", "name": "d", "cat": "해석-결과", "ext": "dat"},
         {"sw_id": "A-2", "dir": "in", "name": "d", "cat": "해석-결과", "ext": "모름", "partner": "가상-툴A"}]), REPO)
    assert [v for io, _t, v in r["recon"] if io.direction == "in"] == ["확장자 미기재"]
    assert not r["ranked"] and not r["feeds"]


def test_majority_tie_is_lexical():
    """I23: 속성 다수값 동률은 입력 순서와 무관하게 사전순."""
    def conflict(order):
        r = oracle.compute(_spec(
            [{"sw_id": f"A-{i}", "name": "가상-툴", "vendor": "v", "kind": k} for i, k in enumerate(order)], []), REPO)
        return r["conflicts"]["가상툴"]["kind"]["majority"]
    assert conflict(["상용", "프리웨어"]) == conflict(["프리웨어", "상용"]) == "상용"


def test_top_n_includes_ties():
    counts = {f"t{i}": v for i, v in enumerate([5, 5, 4, 3, 3, 3, 3, 3, 3, 3, 3, 1])}
    assert len(oracle.top_n(counts, 10)) == 11
