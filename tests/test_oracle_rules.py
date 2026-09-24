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
])
def test_tool_key(name, vendor, key):
    assert oracle.tool_key(name, vendor) == key


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
