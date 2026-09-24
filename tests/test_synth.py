"""M2 합성 조사 파일 — 결정성, 명세 ↔ 엑셀 일치, 템플릿 보존, 엑셀 층 사례, 합성 데이터 규칙."""

from __future__ import annotations

import datetime as dt
import hashlib
import re

import openpyxl
import pytest

from engenius_onto import synth

SPEC = synth.load_spec()
BY_FIELD = {e["field"]: e for e in SPEC["files"] if "file_date" not in e}   # 분야별 유효 파일 (재발송 이전 파일 제외)
FILE_IDS = [synth.file_name(SPEC, e) for e in SPEC["files"]]


def test_committed_files_match_spec():
    """커밋된 xlsx 가 명세에서 다시 만든 것과 바이트까지 같다 (같은 명세 → 같은 파일, M2 완료 기준)."""
    assert synth.run(check=True) == 0


def test_generation_is_deterministic():
    e = SPEC["files"][0]
    assert hashlib.sha256(synth.build_workbook_bytes(SPEC, e)).digest() == \
        hashlib.sha256(synth.build_workbook_bytes(SPEC, e)).digest()


def _wb(entry):
    """분야 이름(유효 파일) 또는 파일 명세."""
    return openpyxl.load_workbook(synth.OUT_DIR / synth.file_name(SPEC, BY_FIELD[entry] if isinstance(entry, str) else entry))


def _rows(ws, start, renamed):
    """헤더 이름으로 읽되, 파일에서 바뀐 헤더(header_overrides)는 원래 이름으로 되돌려 대조한다."""
    back = {new: old for old, new in renamed.items()}
    cols = {back.get(str(c.value), str(c.value)): c.column for c in ws[2] if c.value}
    return [(r, {h: ws.cell(r, c).value for h, c in cols.items()}) for r in range(start, ws.max_row + 1)], cols


def _as_cell(v):
    if isinstance(v, dt.date) and not isinstance(v, dt.datetime):
        return dt.datetime.combine(v, dt.time())   # 엑셀은 날짜를 datetime 으로 돌려준다
    return v


@pytest.mark.parametrize("entry", SPEC["files"], ids=FILE_IDS)
def test_xlsx_carries_spec_rows(entry):
    """명세의 모든 행이 해당 파일의 올바른 위치에 그대로 들어 있다 (셀 타입·덧붙인 열 포함)."""
    wb = _wb(entry)
    tmpl = openpyxl.load_workbook(synth.REPO_ROOT / SPEC["template"])
    overrides = entry.get("header_overrides", {})
    du, di = SPEC["defaults"]["usage"], SPEC["defaults"]["io"]
    rows, _ = _rows(wb["SW기본정보"], synth.USAGE_START_ROW, overrides.get("SW기본정보", {}))
    for (r, row), u in zip(rows, entry["usages"]):
        if u.get("example_copy"):
            assert [c.value for c in wb["SW기본정보"][r]][:33] == [c.value for c in tmpl["SW기본정보"][4]][:33]
            continue
        v = {**du, "field_cell": entry["field"], **u}
        for key, header in synth.USAGE_COLUMNS.items():
            assert row[header] == _as_cell(v.get(key)), (entry["field"], r, header)
    rows, _ = _rows(wb["SW입출력"], entry.get("io_start_row", synth.IO_START_ROW), overrides.get("SW입출력", {}))
    for (r, row), io in zip(rows, entry["ios"]):
        if io.get("blank"):
            assert all(x is None for h, x in row.items() if h != "SW명(자동)"), (entry["field"], r)
            continue
        v = {**di, **io}
        for key, header in synth.IO_COLUMNS.items():
            want = synth.DIRECTION.get(v.get(key)) if key == "dir" else v.get(key)
            assert row[header] == want, (entry["field"], r, header)
        for h, val in (io.get("extra") or {}).items():
            assert row[h] == val


def test_template_example_rows_kept():
    """예시 행은 그대로 (P10). 제어 파일만 SW입출력 5·6행을 응답으로 덮어썼다 (P10-b)."""
    tmpl = openpyxl.load_workbook(synth.REPO_ROOT / SPEC["template"])
    ex_base = [c.value for c in tmpl["SW기본정보"][4]]
    ex_io = [[c.value for c in tmpl["SW입출력"][r]][:13] for r in (4, 5, 6)]
    for e in SPEC["files"]:
        wb = _wb(e["field"])
        assert [c.value for c in wb["SW기본정보"][4]][:33] == ex_base[:33]
        for r in ((4,) if e.get("io_start_row") == 5 else (4, 5, 6)):
            assert [c.value for c in wb["SW입출력"][r]][:13] == ex_io[r - 4]
    assert _wb("제어")["SW입출력"]["A5"].value == "MATLAB"


def test_example_copy_at_other_position():
    """I15: 성능 파일 SW기본정보 9행 = 예시 행 복사본 (응답 4행 아래)."""
    ws = _wb("성능")["SW기본정보"]
    assert [c.value for c in ws[9]][:33] == [c.value for c in ws[4]][:33]


def test_choices_per_file():
    """P22 / CHOICE-FILE: 압축기 파일 선택지에는 '설계-2D Layout' 이 있고 구조 파일에는 없다."""
    for field, has in (("압축기", True), ("구조", False)):
        ws = _wb(field)["선택지"]
        col = next(c.column for c in ws[2] if c.value == "온톨로지분류")
        values = [ws.cell(r, col).value for r in range(3, ws.max_row + 1) if ws.cell(r, col).value]
        assert ("설계-2D Layout" in values) == has, field
    wb = _wb("압축기")
    assert "선택지!$S$3:$S$12" in [dv.formula1 for dv in wb["SW입출력"].data_validations.dataValidation]


def test_header_variants_and_extra_column():
    """HEADER: 터빈 파일은 헤더 문구가 바뀌었고 '내부 메모' 열이 덧붙었다."""
    wb = _wb("터빈")
    io_headers = [c.value for c in wb["SW입출력"][2]]
    assert "파일형식/확장자＊" in io_headers and "파일 형식/확장자 *" not in io_headers
    assert io_headers[-1] == "내부 메모"
    assert "사용빈도" in [c.value for c in wb["SW기본정보"][2]]


def test_cell_types_planted():
    """D5: 엑셀이 바꿔 놓은 셀 타입이 실제로 들어 있다."""
    assert _wb("터빈")["SW기본정보"]["C6"].value == 2024                        # 정수
    assert _wb("구조")["SW기본정보"]["C5"].value == 5.1                         # 실수 ('5.10')
    assert _wb("구조")["SW기본정보"]["C7"].value == dt.datetime(2023, 1, 1)     # 버전 칸 날짜
    assert _wb("성능")["SW기본정보"]["P6"].value == 2027.1                      # 만료 시기 실수 ('2027.10')
    assert _wb("성능")["SW기본정보"]["P7"].value == dt.datetime(2027, 3, 31)    # 만료 시기 날짜
    assert _wb("2차유로(SAS)")["SW기본정보"]["L7"].value == "약 4명"            # 정수 슬롯에 문자열


def test_blank_id_content_row():
    """I22: 압축기 파일에 SW ID 없이 내용만 있는 SW입출력 행."""
    ws = _wb("압축기")["SW입출력"]
    hits = [r for r in range(7, ws.max_row + 1) if ws.cell(r, 1).value is None and ws.cell(r, 4).value]
    assert [ws.cell(r, 4).value for r in hits] == ["형상 검토 메모"]


def test_guide_sheet_pseudonyms_only():
    ws = _wb("시험")["작성안내"]
    assert (ws["C21"].value, ws["C22"].value) == ("OOO", "내선 9998")


def test_file_names_follow_form_rule():
    for e in SPEC["files"]:
        assert re.fullmatch(r"SW조사_[^_]+_\d{8}\.xlsx", synth.file_name(SPEC, e))
    assert len(set(FILE_IDS)) == len(FILE_IDS)


def test_resend_file_is_older_same_field():
    """재발송 사례(I33): 같은 분야의 이전 날짜 파일이 따로 있고, 분야 이름으로 고르면 최신 파일이 나온다."""
    old = [e for e in SPEC["files"] if "file_date" in e]
    assert [e["field"] for e in old] == ["압축기"]
    assert old[0]["file_date"] < SPEC["file_date"]
    assert (synth.OUT_DIR / synth.file_name(SPEC, old[0])).exists()
    assert synth.file_name(SPEC, "압축기").endswith(f"_{SPEC['file_date']}.xlsx")


# --- 합성 데이터 규칙 (CLAUDE.md 절대 규칙 2·5) -------------------------------------------
ALLOWED_TOOLS = {  # 공개 상용·오픈소스 툴 이름 — 그 밖에는 '가상-' 접두만 허용
    "MATLAB", "Excel", "Microsoft Excel", "Python", "ANSYS FLUENT", "ANSYS Fluent 2024R1", "ANSYS Fluent", "Fluent",
    "CATIA V5", "CATIA", "Tecplot", "STAR-CCM+", "HyperMesh", "ANSYS Mechanical", "NASTRAN", "Abaqus",
    "MATLAB Simulink", "LabVIEW",
}


def test_tool_names_public_or_fictional():
    names = {u["name"] for e in SPEC["files"] for u in e["usages"] if "name" in u}
    partners = {p.strip() for e in SPEC["files"] for io in e["ios"] if io.get("partner")
                for p in re.split(r"[,;/·，]", io["partner"])}
    for n in names | partners:
        assert n in ALLOWED_TOOLS or n.startswith("가상-"), n


def test_no_person_names_or_paths():
    """인명은 가명 토큰(OOO)만, 사내 경로·문서번호를 지어내지 않는다."""
    text = synth.SPEC.read_text(encoding="utf-8")
    body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    for m in re.finditer(r"([가-힣A-Za-z]{1,3})\s*(책임|선임|수석|연구원|과장|부장|대리)", body):
        assert set(m.group(1)) <= {"O"}, m.group(0)
    assert "\\\\share" not in body
    assert not re.search(r"(?<![A-Z])TR-\d{4}", body)
