"""M2 합성 조사 파일 — 결정성, 명세 ↔ 엑셀 일치, 템플릿 보존, 합성 데이터 규칙."""

from __future__ import annotations

import datetime as dt
import hashlib
import re

import openpyxl
import pytest

from engenius_onto import synth

SPEC = synth.load_spec()


def test_committed_files_match_spec():
    """커밋된 xlsx 가 명세에서 다시 만든 것과 바이트까지 같다 (같은 명세 → 같은 파일, M2 완료 기준)."""
    assert synth.run(check=True) == 0


def test_generation_is_deterministic():
    e = SPEC["files"][0]
    a = synth.build_workbook_bytes(SPEC, e)
    b = synth.build_workbook_bytes(SPEC, e)
    assert hashlib.sha256(a).digest() == hashlib.sha256(b).digest()


def _wb(field):
    return openpyxl.load_workbook(synth.OUT_DIR / synth.file_name(SPEC, field))


def _rows(ws, start):
    cols = {str(c.value): c.column for c in ws[2] if c.value}
    out = []
    for r in range(start, ws.max_row + 1):
        row = {h: ws.cell(r, c).value for h, c in cols.items()}
        out.append((r, row))
    return out


@pytest.mark.parametrize("entry", SPEC["files"], ids=[e["field"] for e in SPEC["files"]])
def test_xlsx_carries_spec_rows(entry):
    """명세의 모든 행이 해당 파일의 올바른 위치에 그대로 들어 있다 (셀 타입 포함)."""
    wb = _wb(entry["field"])
    du, di = SPEC["defaults"]["usage"], SPEC["defaults"]["io"]
    base = _rows(wb["SW기본정보"], synth.USAGE_START_ROW)
    for (r, row), u in zip(base, entry["usages"]):
        v = {**du, "field_cell": entry["field"], **u}
        for key, header in synth.USAGE_COLUMNS.items():
            want = v.get(key)
            if isinstance(want, dt.date) and not isinstance(want, dt.datetime):
                want = dt.datetime.combine(want, dt.time())   # 엑셀은 날짜를 datetime 으로 돌려준다
            assert row[header] == want, (entry["field"], r, header)
    rows = _rows(wb["SW입출력"], entry.get("io_start_row", synth.IO_START_ROW))
    specs = entry["ios"]
    for (r, row), io in zip(rows, specs):
        if io.get("blank"):
            assert all(x is None for h, x in row.items() if h != "SW명(자동)"), (entry["field"], r)
            continue
        v = {**di, **io}
        for key, header in synth.IO_COLUMNS.items():
            want = synth.DIRECTION.get(v.get(key)) if key == "dir" else v.get(key)
            assert row[header] == want, (entry["field"], r, header)


def test_template_example_rows_kept():
    """예시 행은 그대로 (P10). 제어 파일만 SW입출력 5·6행을 응답으로 덮어썼다 (P10-b)."""
    tmpl = openpyxl.load_workbook(synth.REPO_ROOT / SPEC["template"])
    ex_base = [c.value for c in tmpl["SW기본정보"][4]]
    ex_io = [[c.value for c in tmpl["SW입출력"][r]] for r in (4, 5, 6)]
    for e in SPEC["files"]:
        wb = _wb(e["field"])
        assert [c.value for c in wb["SW기본정보"][4]] == ex_base
        kept = (4,) if e.get("io_start_row") == 5 else (4, 5, 6)
        for r in kept:
            assert [c.value for c in wb["SW입출력"][r]] == ex_io[r - 4]
    wb = _wb("제어")
    assert wb["SW입출력"]["A5"].value == "MATLAB" and wb["SW입출력"]["A6"].value == "MATLAB"


def test_extra_category_in_choices_and_validation():
    wb = _wb("압축기")
    ws = wb["선택지"]
    col = next(c.column for c in ws[2] if c.value == "온톨로지분류")
    values = [ws.cell(r, col).value for r in range(3, ws.max_row + 1) if ws.cell(r, col).value]
    assert values[-1] == "설계-2D Layout"
    refs = [dv.formula1 for dv in wb["SW입출력"].data_validations.dataValidation]
    assert f"선택지!$S$3:$S${2 + len(values)}" in refs


def test_cell_types_planted():
    """D5: 엑셀이 바꿔 놓은 셀 타입이 실제로 들어 있다."""
    assert _wb("터빈")["SW기본정보"]["C6"].value == 2024                      # 정수
    assert _wb("구조")["SW기본정보"]["C5"].value == 5.1                       # 실수 ('5.10')
    assert _wb("성능")["SW기본정보"]["P7"].value == dt.datetime(2027, 3, 31)  # 날짜
    assert _wb("터빈")["SW기본정보"]["L7"].value == "약 6명"                  # 문자열


def test_file_names_follow_form_rule():
    for e in SPEC["files"]:
        assert re.fullmatch(r"SW조사_[^_]+_\d{8}\.xlsx", synth.file_name(SPEC, e["field"]))


# --- 합성 데이터 규칙 (CLAUDE.md 절대 규칙 2·5) -------------------------------------------
ALLOWED_TOOLS = {  # 공개 상용·오픈소스 툴 이름 — 그 밖에는 '가상-' 접두만 허용
    "MATLAB", "Excel", "Microsoft Excel", "Python", "ANSYS FLUENT", "ANSYS Fluent 2024R1", "ANSYS Fluent", "Fluent",
    "CATIA V5", "Tecplot", "STAR-CCM+", "HyperMesh", "ANSYS Mechanical", "NASTRAN", "Abaqus",
    "MATLAB Simulink", "LabVIEW",
}


def test_tool_names_public_or_fictional():
    names = {u["name"] for e in SPEC["files"] for u in e["usages"]}
    partners = {p.strip() for e in SPEC["files"] for io in e["ios"] if io.get("partner")
                for p in re.split(r"[,;/·]", io["partner"])}
    for n in names | partners:
        assert n in ALLOWED_TOOLS or n.startswith("가상-") or n in {"CATIA"}, n


def test_no_person_names_or_paths():
    """인명은 가명 토큰(OOO)만, 사내 경로·문서번호를 지어내지 않는다."""
    text = synth.SPEC.read_text(encoding="utf-8")
    body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    for m in re.finditer(r"([가-힣]{1,3})\s*(책임|선임|수석|연구원|과장|부장|대리)", body):
        assert m.group(1) in {"OOO"} or set(m.group(1)) <= {"O"}, m.group(0)
    assert "\\\\share" not in body
    assert not re.search(r"(?<![A-Z])TR-\d{4}", body)   # 문서번호 형태 (예시 행의 TR-2024-018 같은 것)
