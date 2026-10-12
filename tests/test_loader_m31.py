"""M3.1 적재기 보강 — 양식 v1.1·파트 단위·실데이터 안전장치 (docs/09, docs/10, reference/양식_v1.1_변경분.md).

합성 파일 사본을 고쳐 실제 회신 파일에서 생길 상황을 만든다: v1.1 시트·헤더 이름, 묶음 파일(MD), 병합 셀, 깨진 파일,
인명, 드롭다운 밖 값 대응표, 규칙 밖 파일명. 골든 값은 test_loader.py 가 본다.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import openpyxl
import pytest
import yaml

from engenius_onto.config import CONFIG_DIR
from engenius_onto.loader import Loader, id_key
from engenius_onto.survey_load import DATA_SETS, diag_text, run_load

SURVEY_DIR, REGISTRY_DIR = DATA_SETS["synthetic"]
STR = "SW조사_구조_20260924.xlsx"
V11_SHEETS = {"SW기본정보": "Tool 기본정보", "SW입출력": "Tool 입출력", "선택지": "선택지(수정금지)"}
V11_HEADERS = {"SW ID *": "Tool ID *", "SW명(정식) *": "Tool명(정식) *", "주 사용 단계 *": "사용 기간 *",
               "SW명(자동)": "Tool명(자동)", "연계 SW명": "연계 Tool명"}


def _copy(tmp: Path, names=(STR,)) -> Path:
    d = tmp / "survey"
    d.mkdir(parents=True)
    for n in names:
        shutil.copy(SURVEY_DIR / n, d / n)
    return d


def _load(survey: Path, tmp: Path, config_dir: Path | None = None, **kw):
    return run_load(input_dir=survey, registry_dir=tmp / "registry", out_root=tmp / "out", shacl=False,
                    config_dir=config_dir, **kw)


def _config(tmp: Path, **files) -> Path:
    """config 사본 + 덮어쓸 YAML 파일들."""
    cfg = tmp / "config"
    shutil.copytree(CONFIG_DIR, cfg)
    for name, data in files.items():
        (cfg / f"{name}.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return cfg


def _to_v11(path: Path) -> None:
    """합성 v1.0 파일을 양식 v1.1 모양으로: 시트 이름·헤더 문구·선택지 목록 이름('사용단계' → '사용 기간')."""
    wb = openpyxl.load_workbook(path)
    for old, new in V11_SHEETS.items():
        wb[old].title = new
    for sheet in ("Tool 기본정보", "Tool 입출력"):
        for c in wb[sheet][2]:
            if c.value in V11_HEADERS:
                c.value = V11_HEADERS[c.value]
    for c in wb["선택지(수정금지)"][2]:
        if c.value == "사용단계":
            c.value = "사용 기간"
    wb.save(path)


def test_id_key():
    assert id_key("MDC-01") == id_key("MDC-1") == id_key(" mdc-1 ") == id_key("ＭＤＣ－１") == id_key("MDC-​1") == "MDC-1"
    assert id_key("SAS-10") == "SAS-10" and id_key("01") == "01"      # 숫자만인 ID 는 그대로 (#18 결정)


def test_v11_form_loads_same_as_v10(tmp_path):
    """양식 v1.1 시트·헤더·목록 이름이어도 v1.0 과 같은 툴사용·입출력 (docs/09 #13, 묶음 T)."""
    base = _load(_copy(tmp_path / "a"), tmp_path / "a")
    d = _copy(tmp_path / "b")
    new = d / "Tool조사_구조_20260930.xlsx"
    (d / STR).rename(new)
    _to_v11(new)
    v11 = _load(d, tmp_path / "b")
    key = lambda out: (sorted(u.key for u in out.result.usages), sorted(x.key for x in out.result.ios))  # noqa: E731
    assert key(v11) == key(base)
    assert not [w for w in v11.result.warnings if w.startswith(("시트 없음", "양식 열 없음", "매핑 안 된 헤더", "선택지 목록 없음"))]


def test_part_is_file_code_and_domain_is_attribute(tmp_path):
    """파트 = 파일명 약칭, '담당 부서' 는 reported_domain (docs/10). 구조 파일 STR-05 의 담당 부서 '시험' → 키는 구조, 경고만."""
    out = _load(_copy(tmp_path), tmp_path)
    u = next(u for u in out.result.usages if u.sw_id == "STR-05")
    assert (u.field, u.v["reported_domain"]) == ("구조", "시험")
    assert any(w.startswith("파일 분야 ≠ 담당 부서") and "STR-05" in w for w in out.result.warnings)


def test_domain_other_is_allowed(tmp_path):
    """'담당 부서' = '기타' 는 드롭다운 목록에 없어도 양식 안내가 허용한 값 — 선택지 밖 경고 없음 (rules.yaml extra_choice_values)."""
    d = _copy(tmp_path)
    wb = openpyxl.load_workbook(d / STR)
    ws = wb["SW기본정보"]
    col = next(c.column for c in ws[2] if c.value == "담당 부서 *")
    row = next(r[0].row for r in ws.iter_rows(min_row=4) if r[0].value == "STR-01")
    ws.cell(row, col).value = "기타"
    wb.save(d / STR)
    cfg = _config(tmp_path, parts={"parts": {}, "synthetic_parts": ["구조"]})
    out = _load(d, tmp_path, config_dir=cfg)
    assert not any("= '기타'" in w for w in out.result.warnings)


def test_bundle_file_splits_parts_by_tool_id_prefix(tmp_path):
    """묶음 파일 (MD = MDT+MDC 처럼): 행의 Tool ID 앞부분으로 파트를 정하고, 못 정하면 파일 약칭으로 + 수정 요청."""
    d = _copy(tmp_path)
    (d / STR).rename(d / "Tool조사_MDX_20260930.xlsx")
    wb = openpyxl.load_workbook(d / "Tool조사_MDX_20260930.xlsx")
    ids = {"STR-01": "MDA-1", "STR-02": "MDA-02", "STR-03": "MDB-1", "STR-04": "MDB-2"}   # STR-05 는 그대로 → 파트 미정
    for sheet in ("SW기본정보", "SW입출력"):
        for row in wb[sheet].iter_rows(min_row=4):
            if row[0].value in ids:
                row[0].value = ids[row[0].value]
    wb.save(d / "Tool조사_MDX_20260930.xlsx")
    cfg = _config(tmp_path, parts={"parts": {"MDA": {"name": "가상 A 파트", "domains": ["구조"]},
                                             "MDB": {"name": "가상 B 파트", "domains": ["구조"]}},
                                   "file_bundles": {"MDX": ["MDA", "MDB"]}})
    out = _load(d, tmp_path, config_dir=cfg)
    parts = {u.sw_id: u.field for u in out.result.usages}
    assert parts == {"MDA-1": "MDA", "MDA-02": "MDA", "MDB-1": "MDB", "MDB-2": "MDB", "STR-05": "MDX"}
    assert out.result.part_labels["MDA"] == "가상 A 파트 (MDA)"
    assert any(w.startswith("묶음 파일 파트 미정") for w in out.result.warnings)
    assert any(i["kind"] == "묶음 파일 파트 미정" for i in out.result.issues)
    # 입출력은 주인 툴사용의 파트를 따른다 — MDA-02 의 입출력이 MDA-2 로 적혀도 연결 (#18)
    assert all(x.owner is not None for x in out.result.ios if x.sw_id.startswith("MD"))


def test_merged_cells_filled_with_warning(tmp_path):
    """세로 병합 셀은 위 칸 값으로 채우고 범위마다 경고 1회 (docs/09 #4 A)."""
    d = _copy(tmp_path)
    wb = openpyxl.load_workbook(d / STR)
    ws = wb["SW입출력"]
    col = next(c.column for c in ws[2] if c.value == "전달 방법 *")
    rows = [r[0].row for r in ws.iter_rows(min_row=4) if r[0].value == "STR-02"][:2]
    ws.cell(rows[1], col).value = None
    ws.merge_cells(start_row=rows[0], end_row=rows[1], start_column=col, end_column=col)
    top = ws.cell(rows[0], col).value
    wb.save(d / STR)
    out = _load(d, tmp_path)
    got = {x.row: x.v["transfer_method"] for x in out.result.ios if x.row in rows}
    assert got == {rows[0]: top, rows[1]: top}
    assert sum(w.startswith("병합 셀") for w in out.result.warnings) == 1


def test_rows_after_blank_gap_are_recorded_not_lost(tmp_path):
    """빈 행 10개 뒤 내용은 적재하지 않되 제외 행·수정 요청으로 남긴다 (docs/09 #6 A)."""
    d = _copy(tmp_path)
    wb = openpyxl.load_workbook(d / STR)
    ws = wb["SW기본정보"]
    last = max(r[0].row for r in ws.iter_rows(min_row=4) if r[0].value)
    ws.cell(last + 15, 1).value = "STR-99"
    ws.cell(last + 15, 2).value = "가상-뒤쪽툴"
    wb.save(d / STR)
    out = _load(d, tmp_path)
    assert "STR-99" not in {u.sw_id for u in out.result.usages}
    assert any(r["row"] == last + 15 for r in out.result.excluded_rows)
    assert any(w.startswith("빈 행 10개 뒤 내용 행") for w in out.result.warnings)


def test_unreadable_file_is_skipped_and_nothing_retired(tmp_path):
    """깨진 파일 하나가 적재를 멈추지 않는다 — 경고, 나머지 적재, 이번 실행은 폐기 판정 안 함 (docs/09 #7 A)."""
    reg = tmp_path / "registry"
    shutil.copytree(REGISTRY_DIR, reg)
    d = tmp_path / "survey"
    shutil.copytree(SURVEY_DIR, d)
    (d / "SW조사_제어_20260924.xlsx").write_bytes(b"not a real workbook")
    out = run_load(input_dir=d, registry_dir=reg, out_root=tmp_path / "out", shacl=False)
    assert not out.result.complete and out.log["complete"] is False
    assert any(w.startswith("읽을 수 없는 파일") for w in out.result.warnings)
    assert not any(w.startswith("툴사용 0건") for w in out.result.warnings)   # 읽지 못한 파일은 0건 경고 대상이 아니다 (I37)
    assert out.log["counts"]["usages"] == 31                     # 34 - 제어 3
    rows = {r["key"]: r["status"] for r in csv_rows(reg / "fields.csv")}
    assert rows["제어"] == "활성"                                  # 읽지 못한 분야를 폐기로 바꾸지 않는다


def csv_rows(path: Path) -> list[dict]:
    import csv
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_person_like_text_warns_without_value(tmp_path):
    """인명 유사 패턴은 모든 문자열 열에서 경고 — 경고·수정 요청에 값을 옮기지 않는다 (docs/09 #20)."""
    d = _copy(tmp_path)
    wb = openpyxl.load_workbook(d / STR)
    ws = wb["SW기본정보"]
    col = next(c.column for c in ws[2] if c.value == "검증 기준/문서번호")
    row = next(r[0].row for r in ws.iter_rows(min_row=4) if r[0].value == "STR-01")
    ws.cell(row, col).value = "가상인 책임님 확인"
    wb.save(d / STR)
    out = _load(d, tmp_path)
    hits = [w for w in out.result.warnings if w.startswith("인명 유사 패턴") and "STR-01" in w]
    assert hits and not any("가상인" in w for w in out.result.warnings)
    assert [i for i in out.result.issues if i["kind"] == "인명 유사" and i["value"] == ""]


def test_value_aliases_map_free_text_to_dropdown(tmp_path):
    """드롭다운 대신 적은 값 → config/value_aliases.yaml 로 바꿔 적재, 건수 경고 (M3.1, Leo 2026-09-30)."""
    d = _copy(tmp_path, ("SW조사_터빈_20260924.xlsx",))
    base = _load(d, tmp_path / "a")
    assert any("= '메일'" in w for w in base.result.warnings)
    cfg = _config(tmp_path, value_aliases={"전달 방법": {"메일": "메일·수기 전달"}})
    out = _load(d, tmp_path / "b", config_dir=cfg)
    x = next(x for x in out.result.ios if x.sw_id == "TURB-03" and x.name == "유동장 결과")
    assert x.v["transfer_method"] == "메일·수기 전달"
    assert not any("= '메일'" in w for w in out.result.warnings)
    assert any(w.startswith("값 대응표 적용") for w in out.result.warnings)
    with pytest.raises(ValueError, match="알 수 없는 열"):
        Loader(config_dir=_config(tmp_path / "c", value_aliases={"없는 열": {"a": "b"}}))


def test_na_in_dropdown_is_not_a_choice_error(tmp_path):
    """양식 v1.1 안내대로 'NA' 를 적은 드롭다운 칸은 선택지 밖 경고·수정 요청이 아니다 — 파일당 한 줄 (#21)."""
    d = _copy(tmp_path)
    wb = openpyxl.load_workbook(d / STR)
    ws = wb["SW기본정보"]
    col = next(c.column for c in ws[2] if c.value == "인증/로그인 방식")
    for r in ws.iter_rows(min_row=4):
        if r[0].value in ("STR-01", "STR-02"):
            ws.cell(r[0].row, col).value = "NA"
    wb.save(d / STR)
    out = _load(d, tmp_path)
    assert not any("= 'NA'" in w for w in out.result.warnings)
    assert any(w.startswith("빈 값 표기") and "2칸" in w for w in out.result.warnings)
    assert {u.v["auth_method"] for u in out.result.usages if u.sw_id in ("STR-01", "STR-02")} == {"NA"}   # 원문 보존


def test_seed_tool_aliases():
    """기본 별칭 (Leo Q1 2026-10-01): 대소문자·버전은 정규화로, 한글·약칭 표기는 config/tool_aliases.yaml 로 같은 툴."""
    ld = Loader()
    amap, labels = ld._alias_map()
    key = lambda s: amap.get(ld.norm.tool_key(s), ld.norm.tool_key(s))  # noqa: E731
    assert key("Excel") == key("EXCEL") == key("excel 2016") == key("엑셀") == key("MS Excel")
    assert key("PPT") == key("PowerPoint") and key("매트랩") == key("MATLAB") and key("워드") == key("Word")
    assert labels[key("Excel")] == "Excel"


def test_off_rule_file_name_is_hashed_everywhere(tmp_path):
    """규칙 밖 파일명(인명이 섞였을 수 있음)은 해시 이름으로만 — 로그·그래프·수정 요청표 (docs/09 #8 A)."""
    d = _copy(tmp_path)
    (d / STR).rename(d / "Tool조사_구조_가상인_20260930.xlsx")
    out = _load(d, tmp_path)
    blob = out.turtle + json.dumps(out.log, ensure_ascii=False) + (out.out_dir / "diag.txt").read_text(encoding="utf-8")
    assert "가상인" not in blob
    assert any(f["name"].startswith("Tool조사_규칙밖_") for f in out.log["files"])
    assert not any("가상인" in p.name for p in (out.out_dir / "fix_requests").iterdir())


def test_input_without_registry_is_refused(tmp_path):
    """--input 만 주면 합성 레지스트리에 쓰게 되므로 거부 (docs/09 #9)."""
    with pytest.raises(ValueError, match="--registry"):
        run_load(input_dir=SURVEY_DIR, out_root=tmp_path, shacl=False)


def test_fix_requests_and_diag(tmp_path):
    """파일별 수정 요청표와 반출용 진단 요약 — diag 에는 셀 값이 없다."""
    reg = tmp_path / "registry"
    shutil.copytree(REGISTRY_DIR, reg)
    out = run_load(registry_dir=reg, out_root=tmp_path / "out", shacl=False)
    files = sorted(p.name for p in (out.out_dir / "fix_requests").iterdir())
    assert "SW조사_터빈_20260924_수정요청.xlsx" in files
    ws = openpyxl.load_workbook(out.out_dir / "fix_requests" / "SW조사_터빈_20260924_수정요청.xlsx").active
    rows = [[c.value for c in r] for r in ws.iter_rows(min_row=3)]
    assert ["Tool 입출력", "전달 방법", "메일", "선택지 밖 값"] in [[r[0], r[3], r[4], r[5]] for r in rows]
    text = diag_text(out.out_dir)
    assert "선택지 밖 값" in text and "'메일'" not in text and "보고서/문서" not in text and "TURB" not in text
    assert (out.out_dir / "diag.txt").read_text(encoding="utf-8") == text
