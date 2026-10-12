"""M3.1 2차 적재기 보강 (docs/11 3장 1·2·3·6번, docs/09 #2·#14·#15·#16·#21·C2·C15, Leo 결정 Q3 2026-10-02).

- 설정 오버레이 data/real/config (C15): 합치는 규칙, 적재기 적용, apply-review 쓰는 곳
- 툴 통합 수리: 토큰 치환(C++)·범용/빈 이름 행별 키·포함 후보 3자·제조사 접두 흡수·키 기반 통합·별개 되돌리기·cp949 CSV
- 정수 열 빈 값 토큰·입출력 없는 툴사용의 수정 요청 행
- 설치 판 표식
합성 파일 사본만 쓴다 (공개 상용 툴 이름·가상 이름).
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

import openpyxl
import pytest
import yaml

from engenius_onto import config as cfgmod
from engenius_onto.config import CONFIG_DIR, REPO_ROOT, installed_version, merge_config, read_csv_rows
from engenius_onto.loader import Loader
from engenius_onto.normalize import Normalizer
from engenius_onto.registry import Registry, copy_registry
from engenius_onto.survey_load import DATA_SETS, apply_review, diag_text, review_target_dir, run_load

SURVEY_DIR, REGISTRY_DIR = DATA_SETS["synthetic"]
STR = "SW조사_구조_20260924.xlsx"
H_NAME, H_VENDOR, H_USERS, H_QTY = "SW명(정식) *", "제조사 / 개발주체 *", "사용 인원수", "보유 수량"


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
    cfg = tmp / "config"
    shutil.copytree(CONFIG_DIR, cfg)
    for name, data in files.items():
        (cfg / f"{name}.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return cfg


def _set_cells(path: Path, sheet: str, changes: dict[str, dict[str, object]]) -> None:
    """{SW ID: {헤더: 값}} 로 셀을 고친다."""
    wb = openpyxl.load_workbook(path)
    ws = wb[sheet]
    col = {c.value: c.column for c in ws[2] if c.value}
    for r in ws.iter_rows(min_row=4):
        if r[0].value in changes:
            for h, v in changes[r[0].value].items():
                ws.cell(r[0].row, col[h]).value = v
    wb.save(path)


def _add_usage(path: Path, sw_id: str, name: str, vendor: str, like: str = "STR-01") -> None:
    """기존 행(like)을 복사해 새 툴사용 행을 끝에 붙인다 (입출력은 없음)."""
    wb = openpyxl.load_workbook(path)
    ws = wb["SW기본정보"]
    col = {c.value: c.column for c in ws[2] if c.value}
    src = next(r for r in ws.iter_rows(min_row=4) if r[0].value == like)
    last = max(r[0].row for r in ws.iter_rows(min_row=4) if r[0].value)
    for c in src:
        ws.cell(last + 1, c.column).value = c.value
    ws.cell(last + 1, 1).value = sw_id
    ws.cell(last + 1, col[H_NAME]).value = name
    ws.cell(last + 1, col[H_VENDOR]).value = vendor
    wb.save(path)


def _write_csv(path: Path, rows: list[dict], encoding: str = "utf-8-sig") -> None:
    with path.open("w", encoding=encoding, newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


# --------------------------------------------------------------------------- A. 설정 오버레이 (C15)
def test_merge_config_rules():
    """tool_aliases 는 합집합, value_aliases 는 열별 깊은 병합, rules 는 키 단위(중첩 dict 는 키별) 덮어쓰기."""
    base = {"aliases": {"Excel": ["엑셀"]}, "distinct": [["a", "b"]], "merge_keys": {"x": "y"}}
    over = {"aliases": {"Excel": ["MS Excel"], "NX": ["Unigraphics"]}, "distinct": [["a", "b"], ["c", "d"]], "labels": {"y": "Y"}}
    got = merge_config("tool_aliases.yaml", base, over)
    assert got["aliases"] == {"Excel": ["MS Excel", "엑셀"], "NX": ["Unigraphics"]}
    assert got["distinct"] == [["a", "b"], ["c", "d"]] and got["merge_keys"] == {"x": "y"} and got["labels"] == {"y": "Y"}
    got = merge_config("value_aliases.yaml", {"전달 방법": {"메일": "메일·수기 전달"}}, {"전달 방법": {"메일로": "메일·수기 전달"}, "방향": {"입력": "입력(소비)"}})
    assert got == {"전달 방법": {"메일": "메일·수기 전달", "메일로": "메일·수기 전달"}, "방향": {"입력": "입력(소비)"}}
    got = merge_config("rules.yaml", {"loader": {"header_row": 2, "sheets": {"usage": ["a"]}}, "hub_top_n": 10},
                       {"loader": {"blank_rows_end": 5}, "hub_top_n": 5})
    assert got == {"loader": {"header_row": 2, "sheets": {"usage": ["a"]}, "blank_rows_end": 5}, "hub_top_n": 5}


def test_overlay_applies_and_is_recorded_without_values(tmp_path):
    """오버레이의 value_aliases·tool_aliases 가 config/ 위에 덮이고, load_log·diag 에는 파일 이름만 남는다."""
    d = _copy(tmp_path, ("SW조사_터빈_20260924.xlsx",))
    base = _load(d, tmp_path / "a")
    assert any("= '메일'" in w for w in base.result.warnings) and base.log["config_overlay"]["used"] is False
    over = tmp_path / "real_config"
    over.mkdir()
    (over / "value_aliases.yaml").write_text(yaml.safe_dump({"전달 방법": {"메일": "메일·수기 전달"}}, allow_unicode=True), encoding="utf-8")
    (over / "tool_aliases.yaml").write_text(yaml.safe_dump({"aliases": {"Tecplot": ["텍플롯"]}}, allow_unicode=True), encoding="utf-8")
    out = _load(d, tmp_path / "b", overlay_dir=over)
    assert not any("= '메일'" in w for w in out.result.warnings)
    assert out.log["config_overlay"] == {"used": True, "dir": str(over.resolve()), "files": ["tool_aliases.yaml", "value_aliases.yaml"],
                                         "outside_repo": True}                                  # 저장소 밖 폴더 — 절대 경로 그대로
    ld = Loader(overlay_dir=over)
    amap, _ = ld._alias_map()
    assert amap.get(ld.norm.tool_key("텍플롯")) == "tecplot" and amap.get(ld.norm.tool_key("엑셀")) == "excel"   # 합집합
    text = diag_text(out.out_dir)
    assert "설정 오버레이 사용: 예 (tool_aliases.yaml, value_aliases.yaml)" in text
    assert "'메일'" not in text and "텍플롯" not in text and str(over) not in text      # 오버레이 값·경로는 diag 에 없다
    assert "설정 오버레이 사용: 아니오" in diag_text(base.out_dir)


def test_overlay_not_applied_to_synthetic_or_custom_by_default(tmp_path, monkeypatch):
    """data/real/config 가 있어도 합성·--input 실행에는 자동으로 붙지 않는다 (--data real 만). overlay=False 로 끌 수도 있다."""
    over = tmp_path / "real_config"
    over.mkdir()
    (over / "rules.yaml").write_text("hub_top_n: 3\n", encoding="utf-8")
    monkeypatch.setattr(cfgmod, "REAL_CONFIG_DIR", over)
    assert cfgmod.default_overlay_dir() == over and cfgmod.default_overlay_dir(tmp_path) is None
    d = _copy(tmp_path)
    out = _load(d, tmp_path)
    assert out.log["config_overlay"]["used"] is False
    reg = tmp_path / "reg"
    copy_registry(REGISTRY_DIR, reg)
    out = run_load(registry_dir=reg, out_root=tmp_path / "s", shacl=False)
    assert out.log["config_overlay"]["used"] is False
    assert Loader(overlay_dir=over).rules["hub_top_n"] == 3 and Loader(overlay_dir=over).overlay_files == ["rules.yaml"]


def test_apply_review_target_follows_run_dataset(tmp_path, monkeypatch):
    """검토표가 나온 실행이 합성이면 config/, 실데이터(또는 모름)이면 data/real/config — 오버레이 파일은 머리말과 함께 새로 만든다."""
    over = tmp_path / "real_config"
    monkeypatch.setattr(cfgmod, "REAL_CONFIG_DIR", over)
    import engenius_onto.survey_load as sl
    monkeypatch.setattr(sl, "REAL_CONFIG_DIR", over)
    reg = tmp_path / "reg"
    copy_registry(REGISTRY_DIR, reg)
    out = run_load(registry_dir=reg, out_root=tmp_path / "s", shacl=False)
    assert review_target_dir(out.out_dir / "tool_review.csv") == CONFIG_DIR
    real_run = tmp_path / "r" / "20260101T000000"
    real_run.mkdir(parents=True)
    (real_run / "load_log.json").write_text('{"input": "real"}', encoding="utf-8")
    shutil.copy(out.out_dir / "tool_review.csv", real_run / "tool_review.csv")
    assert review_target_dir(real_run / "tool_review.csv") == over
    assert review_target_dir(tmp_path / "nowhere.csv") == over
    rows, _ = read_csv_rows(real_run / "tool_review.csv")
    rows[0]["판정(통합/별개)"] = "통합"
    _write_csv(real_run / "tool_review.csv", rows)
    from engenius_onto.cli import main
    repo_file = (CONFIG_DIR / "tool_aliases.yaml").read_bytes()
    assert main(["apply-review", str(real_run / "tool_review.csv")]) == 0
    text = (over / "tool_aliases.yaml").read_text(encoding="utf-8")
    assert text.startswith("# 사내 툴 통합 판정") and yaml.safe_load(text)["merge_keys"] == {"matlabsimulink": "matlab"}
    assert (CONFIG_DIR / "tool_aliases.yaml").read_bytes() == repo_file                      # 저장소 파일은 그대로
    assert main(["apply-review", str(real_run / "tool_review.csv"), "--config-dir", str(tmp_path / "forced")]) == 0
    assert (tmp_path / "forced" / "tool_aliases.yaml").is_file()


# --------------------------------------------------------------------------- B. 툴 통합 수리
@pytest.mark.parametrize("name, vendor, key", [
    ("C++", None, "cpp"), ("C#", None, "csharp"), ("C", None, "c"), ("Visual C++", "Microsoft", "visualcpp"),
    ("Excel 2016", "Microsoft", "excel"), ("CFX 2024 R1", "ANSYS", "cfx"), ("STAR-CCM+", "Siemens", "starccm"),
    ("Tecplot", "Tecplot", "tecplot"), ("Microsoft Excel", "Microsoft", "excel"),
])
def test_tool_key_token_map_matches_oracle(name, vendor, key):
    import sys
    sys.path.insert(0, str(Path(__file__).parent / "golden"))
    import oracle
    norm = Normalizer.from_config()
    assert norm.tool_key(name, vendor) == oracle.tool_key(name, vendor) == key


def test_generic_and_empty_names_get_row_keys(tmp_path):
    """'자체개발'·'(자체 매크로)'·'-' 는 통합하지 않고 행별 '미상:' 키 + 경고 + 수정 요청 '툴 이름을 지어 주세요' (Leo Q3(b))."""
    d = _copy(tmp_path)
    _set_cells(d / STR, "SW기본정보", {"STR-01": {H_NAME: "자체개발", H_VENDOR: "자체개발"},
                                   "STR-02": {H_NAME: "(자체 매크로)"}, "STR-04": {H_NAME: "-"}, "STR-05": {H_NAME: "사내 개발"}})
    out = _load(d, tmp_path)
    keys = {u.sw_id: u.tool_key for u in out.result.usages}
    assert keys["STR-01"] == "미상:구조/STR-01" and keys["STR-02"] == "미상:구조/STR-02"
    assert keys["STR-04"] == "미상:구조/STR-04" and keys["STR-05"] == "미상:구조/STR-05"
    assert len({keys[k] for k in ("STR-01", "STR-02", "STR-04", "STR-05")}) == 4 and "" not in out.result.tools
    assert sum(w.startswith("툴 이름 범용/비어 있음") for w in out.result.warnings) == 4
    hints = [i for i in out.result.issues if i["kind"] == "툴 이름 범용/비어 있음"]
    assert len(hints) == 4 and all("툴 이름을 지어 주세요" in i["hint"] for i in hints)
    assert not any("미상:" in c["a"] or "미상:" in c["b"] for c in out.result.merge_candidates)   # 후보표에도 안 올린다
    assert out.result.tools["미상:구조/STR-01"].pref_label == "자체개발"
    # 연계 Tool명에 적힌 '자체개발' 은 빈 값처럼 버린다 (I34)
    assert Normalizer.from_config().split_partners("자체개발, Excel") == ["Excel"]


def test_containment_candidates_need_three_chars(tmp_path):
    """한두 글자 키('c')가 모든 키에 포함돼 후보표를 채우지 않는다 (docs/09 #16 A)."""
    d = _copy(tmp_path)
    _set_cells(d / STR, "SW기본정보", {"STR-01": {H_NAME: "C"}, "STR-02": {H_NAME: "C++"}, "STR-04": {H_NAME: "CFX"}})
    out = _load(d, tmp_path)
    assert {"c", "cpp", "cfx"} <= set(out.result.tools)
    pairs = {(c["a"], c["b"]) for c in out.result.merge_candidates}
    assert not any("c" in p for p in pairs)                      # 'c' ⊂ 'cpp', 'c' ⊂ 'cfx' 는 후보가 아니다
    assert ("cfx", "cpp") not in pairs                           # 유사도 0.67 — 후보 아님


def test_vendor_prefix_absorbed_into_existing_tool(tmp_path):
    """제조사 칸이 비어 있어도 '제조사+툴' 이름은 조사에 나온 제조사를 떼어 기존 툴로 흡수 (Leo Q3(a)) — 레지스트리 ID 유지, 옛 키는 통합됨."""
    d = _copy(tmp_path)
    _add_usage(d / STR, "STR-90", "ANSYS Mechanical APDL", "")       # 'ansysmechanicalapdl' → 'mechanicalapdl' 은 없다 → 흡수 안 함
    _add_usage(d / STR, "STR-91", "Ansys Mechanical", "")             # → 'mechanical' (STR-02 ANSYS Mechanical/ANSYS 가 있음)
    _add_usage(d / STR, "STR-92", "Altair HyperMesh", "다른 회사")    # 다른 행의 제조사 Altair → 'hypermesh'
    out = _load(d, tmp_path)
    keys = {u.sw_id: u.tool_key for u in out.result.usages}
    assert keys["STR-91"] == "mechanical" and keys["STR-92"] == "hypermesh" and keys["STR-90"] == "ansysmechanicalapdl"
    assert sorted(out.result.tools["mechanical"].names) == ["ANSYS Mechanical", "Ansys Mechanical"]
    assert sum(w.startswith("제조사 접두 흡수") for w in out.result.warnings) == 2
    assert out.result.alias_map.get("ansysmechanical") == "mechanical"
    # 별개 판정 쌍은 흡수하지 않는다
    cfg = _config(tmp_path, tool_aliases={"aliases": {}, "distinct": [["hypermesh", "altairhypermesh"]]})
    out2 = _load(d, tmp_path / "b", config_dir=cfg)
    assert {u.sw_id: u.tool_key for u in out2.result.usages}["STR-92"] == "altairhypermesh"


def _tool_rows(reg: Path) -> dict[str, dict]:
    return {r["key"]: r for r in read_csv_rows(reg / "tools.csv")[0]}


def test_vendor_absorption_keeps_registry_tool_id_across_runs(tmp_path):
    """검토 지적(높음): 1회차 'ANSYS Fluent'(제조사 빈칸) 2행 → 2회차에 'Fluent'/ANSYS 행이 더해지면 기존 키가 새 키로 흡수돼
    TOOL ID 가 바뀌고, 3회차에 그 행이 빠지면 되돌아갔다. 수리: 레지스트리 활성 행이 한쪽에만 있으면 그 키가 생존 — 3회 내내 같은 ID,
    통합됨·폐기 전이 0."""
    d = _copy(tmp_path)
    _set_cells(d / STR, "SW기본정보", {"STR-01": {H_NAME: "ANSYS Fluent", H_VENDOR: ""}, "STR-04": {H_NAME: "ANSYS Fluent", H_VENDOR: ""}})
    reg = tmp_path / "registry"
    one = _load(d, tmp_path)                                                      # 1회차
    assert sorted(u.sw_id for u in one.result.tools["ansysfluent"].usages) == ["STR-01", "STR-04"]
    tid = _tool_rows(reg)["ansysfluent"]["id"]
    assert not any(w.startswith("제조사 접두 흡수") for w in one.result.warnings)

    shutil.copy(d / STR, tmp_path / "run1.xlsx")
    _add_usage(d / STR, "STR-90", "Fluent", "ANSYS")                              # 2회차: 접두 없는 행이 새로 들어온다
    two = _load(d, tmp_path)
    keys = {u.sw_id: u.tool_key for u in two.result.usages}
    assert keys["STR-90"] == keys["STR-01"] == "ansysfluent" and "fluent" not in two.result.tools
    rows = _tool_rows(reg)
    assert rows["ansysfluent"]["id"] == tid and rows["ansysfluent"]["status"] == "활성" and "fluent" not in rows
    assert two.log["registry"]["transitions"]["tool"] == {"created": 0, "revived": 0}
    assert not [r for r in rows.values() if r["status"] != "활성"]
    absorbed = [w for w in two.result.warnings if w.startswith("제조사 접두 흡수")]
    assert len(absorbed) == 1 and "STR-90 'fluent' → 'ansysfluent' (레지스트리 ID 유지)" in absorbed[0]
    assert two.result.alias_map["fluent"] == "ansysfluent"                       # 연계 SW명 'Fluent' 도 같은 툴로
    assert two.result.tools["ansysfluent"].names == ["ANSYS Fluent", "Fluent"]

    shutil.copy(tmp_path / "run1.xlsx", d / STR)                                  # 3회차: 그 행이 빠진다
    three = _load(d, tmp_path)
    rows = _tool_rows(reg)
    assert rows["ansysfluent"]["id"] == tid and rows["ansysfluent"]["status"] == "활성"
    assert three.log["registry"]["transitions"]["tool"] == {"created": 0, "revived": 0}
    assert not [r for r in rows.values() if r["status"] != "활성"]
    assert {u.key: u.node_id for u in one.result.usages} == {u.key: u.node_id for u in three.result.usages}

    # 레지스트리가 없거나(골든 oracle) 두 키 모두 없으면 키 모양 규칙 — 접두를 뗀 'fluent' 생존 (I1).
    _add_usage(d / STR, "STR-90", "Fluent", "ANSYS")
    ld = Loader()
    res = ld.load(ld.discover(d))
    assert {u.sw_id: u.tool_key for u in res.usages}["STR-01"] == "fluent" and res.alias_map["ansysfluent"] == "fluent"
    assert any("'ansysfluent' → 'fluent' (제조사 접두를 뗀 키)" in w for w in res.warnings)
    res = ld.load(ld.discover(d), known_tool_keys={"fluent"})
    assert {u.sw_id: u.tool_key for u in res.usages}["STR-01"] == "fluent"
    # 둘 다 활성(기존 툴 둘)이면 자동 통합하지 않는다 — 보류 경고 + 검토표 후보 '제조사 접두' (HITL, 3차 재검토)
    res = ld.load(ld.discover(d), known_tool_keys={"ansysfluent", "fluent"})
    keys = {u.sw_id: u.tool_key for u in res.usages}
    assert keys["STR-01"] == "ansysfluent" and keys["STR-90"] == "fluent" and "ansysfluent" not in res.alias_map
    assert [w for w in res.warnings if w.startswith("제조사 접두")] == ["제조사 접두 흡수 보류: 기존 툴 둘 이상 (ansysfluent, fluent) — 검토표에서 판정"]
    assert [(c["a"], c["b"], c["reason"]) for c in res.merge_candidates if c["reason"] == "제조사 접두"] == [("ansysfluent", "fluent", "제조사 접두")]


def test_vendor_absorption_groups_three_keys(tmp_path):
    """검토 지적(중간): {altairfluent, ansysfluent, fluent} 처럼 셋이 얽히면 쌍 단위 생존 키 선택이 한 쌍을 통째로 버려 두 툴로 갈라졌다.
    수리: 합집합으로 묶어 그룹 단위 — 활성 레지스트리 키가 정확히 하나면 그것, 없으면 사슬의 끝(접두를 뗀 쪽). 그룹 수는 늘 1.
    활성 키가 둘 이상이면(3차 재검토) 그룹 전체를 보류 — 세 툴 그대로, 경고 1, 검토표에 그룹의 모든 쌍을 '제조사 접두' 로."""
    d = _copy(tmp_path)
    _add_usage(d / STR, "STR-90", "Altair Fluent", "")                # 제조사 빈칸 — Altair 는 다른 행(HyperMesh)의 제조사
    _add_usage(d / STR, "STR-91", "ANSYS Fluent", "")
    _add_usage(d / STR, "STR-92", "Fluent", "ANSYS")
    ld = Loader()
    paths = ld.discover(d)
    assert {ld.norm.tool_key(n, v) for n, v in (("Altair Fluent", ""), ("ANSYS Fluent", ""), ("Fluent", "ANSYS"))} == {"altairfluent", "ansysfluent", "fluent"}
    for known, survivor, why in (({"ansysfluent"}, "ansysfluent", "레지스트리 ID 유지"), (set(), "fluent", "제조사 접두를 뗀 키"),
                                 ({"altairfluent"}, "altairfluent", "레지스트리 ID 유지")):
        res = ld.load(paths, known_tool_keys=known)
        keys = {u.sw_id: u.tool_key for u in res.usages}
        assert keys["STR-90"] == keys["STR-91"] == keys["STR-92"] == survivor, known
        assert len({k for k in res.tools if "fluent" in k}) == 1 and sorted(res.tools[survivor].names) == ["ANSYS Fluent", "Altair Fluent", "Fluent"]
        absorbed = sorted(w for w in res.warnings if w.startswith("제조사 접두 흡수"))
        assert len(absorbed) == 2 and all(f"→ '{survivor}' ({why})" in w for w in absorbed), absorbed
        assert {res.alias_map[k] for k in {"altairfluent", "ansysfluent", "fluent"} - {survivor}} == {survivor}
    res = ld.load(paths, known_tool_keys={"ansysfluent", "fluent"})
    keys = {u.sw_id: u.tool_key for u in res.usages}
    assert (keys["STR-90"], keys["STR-91"], keys["STR-92"]) == ("altairfluent", "ansysfluent", "fluent")
    assert [w for w in res.warnings if w.startswith("제조사 접두")] == ["제조사 접두 흡수 보류: 기존 툴 둘 이상 (ansysfluent, fluent) — 검토표에서 판정"]
    assert {(c["a"], c["b"]) for c in res.merge_candidates if c["reason"] == "제조사 접두"} == \
        {("altairfluent", "ansysfluent"), ("altairfluent", "fluent"), ("ansysfluent", "fluent")}
    assert not any(k in res.alias_map for k in ("altairfluent", "ansysfluent", "fluent"))
    # 참조 계산(레지스트리 없음)도 한 그룹, 가장 짧은 키
    import sys
    sys.path.insert(0, str(Path(__file__).parent / "golden"))
    import oracle
    r = oracle.compute(_oracle_spec([{"sw_id": "A-1", "name": "Altair Fluent", "vendor": ""}, {"sw_id": "A-2", "name": "ANSYS Fluent", "vendor": ""},
                                     {"sw_id": "A-3", "name": "Fluent", "vendor": "ANSYS"}, {"sw_id": "A-4", "name": "HyperMesh", "vendor": "Altair"}]),
                       REPO_ROOT)
    assert {u.sw_id: u.tool for u in r["usages"]} == {"A-1": "fluent", "A-2": "fluent", "A-3": "fluent", "A-4": "hypermesh"}


def test_vendor_absorption_skips_group_with_distinct_pair(tmp_path):
    """3차 재검토(중간): 별개 판정 쌍 (altairfluent, ansysfluent) 이 제3의 키 fluent 를 거쳐 한 그룹이 되면 조용히 통합됐다.
    수리: 그룹 안에 별개 쌍이 있으면 그 그룹은 통째로 흡수하지 않고 경고 1 — 세 툴 그대로 (oracle 거울)."""
    d = _copy(tmp_path)
    _add_usage(d / STR, "STR-90", "Altair Fluent", "")
    _add_usage(d / STR, "STR-91", "ANSYS Fluent", "")
    _add_usage(d / STR, "STR-92", "Fluent", "ANSYS")                 # HyperMesh/Altair 는 STR 파일에 이미 있다
    cfg = _config(tmp_path, tool_aliases={"aliases": {}, "distinct": [["altairfluent", "ansysfluent"]]})
    out = _load(d, tmp_path, config_dir=cfg)
    keys = {u.sw_id: u.tool_key for u in out.result.usages}
    assert (keys["STR-90"], keys["STR-91"], keys["STR-92"]) == ("altairfluent", "ansysfluent", "fluent")
    assert {k for k in out.result.tools if "fluent" in k} == {"altairfluent", "ansysfluent", "fluent"}
    assert [w for w in out.result.warnings if w.startswith("제조사 접두")] == \
        ["제조사 접두 흡수와 별개 판정이 충돌: altairfluent / ansysfluent — 흡수하지 않음"]
    assert not any(k in out.result.alias_map for k in ("altairfluent", "ansysfluent", "fluent"))
    pairs = {(c["a"], c["b"]): c["reason"] for c in out.result.merge_candidates}
    assert ("altairfluent", "ansysfluent") not in pairs                                   # 이미 판정한 쌍은 후보표에 다시 올리지 않는다
    assert pairs.get(("altairfluent", "fluent")) == "포함" and pairs.get(("ansysfluent", "fluent")) == "포함"
    assert "제조사 접두" not in (out.out_dir / "tool_review.csv").read_text(encoding="utf-8-sig")
    # 참조 계산 거울 — 명세의 distinct
    import sys
    sys.path.insert(0, str(Path(__file__).parent / "golden"))
    import oracle
    spec = _oracle_spec([{"sw_id": "A-1", "name": "Altair Fluent", "vendor": ""}, {"sw_id": "A-2", "name": "ANSYS Fluent", "vendor": ""},
                         {"sw_id": "A-3", "name": "Fluent", "vendor": "ANSYS"}, {"sw_id": "A-4", "name": "HyperMesh", "vendor": "Altair"}])
    spec["distinct"] = [["altairfluent", "ansysfluent"]]
    r = oracle.compute(spec, REPO_ROOT)
    assert {u.sw_id: u.tool for u in r["usages"]} == {"A-1": "altairfluent", "A-2": "ansysfluent", "A-3": "fluent", "A-4": "hypermesh"}
    assert len(r["tools"]) == 4 and sum(w.startswith("제조사 접두") for w in r["warnings"]) == 1


def test_vendor_absorption_held_pairs_reach_review_csv(tmp_path):
    """기존 툴 둘 이상인 그룹의 보류 — 적재 끝까지: 레지스트리에 'ansysfluent'·'fluent' 가 둘 다 활성이면 통합하지 않고
    tool_review.csv 에 사유 '제조사 접두' 행이 실린다. 사람이 '통합' 으로 판정해 apply-review 하면 다음 적재에서 한 툴이 된다."""
    d = _copy(tmp_path)
    _set_cells(d / STR, "SW기본정보", {"STR-01": {H_NAME: "ANSYS Fluent", H_VENDOR: ""}})
    _add_usage(d / STR, "STR-90", "Fluent", "ANSYS")
    cfg = _config(tmp_path, tool_aliases={"aliases": {}, "distinct": [["ansysfluent", "fluent"]]})   # 1회차: 별개로 두 툴을 만든다
    one = _load(d, tmp_path, config_dir=cfg)
    assert {"ansysfluent", "fluent"} <= set(one.result.tools)
    (cfg / "tool_aliases.yaml").write_text(yaml.safe_dump({"aliases": {}, "distinct": []}), encoding="utf-8")   # 2회차: 판정을 지움
    two = _load(d, tmp_path, config_dir=cfg)
    assert {"ansysfluent", "fluent"} <= set(two.result.tools)
    assert any(w.startswith("제조사 접두 흡수 보류: 기존 툴 둘 이상 (ansysfluent, fluent)") for w in two.result.warnings)
    rows, _ = read_csv_rows(two.out_dir / "tool_review.csv")
    held = [r for r in rows if r["사유"] == "제조사 접두"]
    assert [(r["툴A_키"], r["툴B_키"]) for r in held] == [("ansysfluent", "fluent")] and held[0]["툴A_표기"] == "ANSYS Fluent"
    rows_dict = {(r["툴A_키"], r["툴B_키"]): r for r in rows}
    rows_dict[("ansysfluent", "fluent")]["판정(통합/별개)"] = "통합"
    _write_csv(two.out_dir / "tool_review.csv", list(rows_dict.values()))
    apply_review(two.out_dir / "tool_review.csv", cfg)
    three = _load(d, tmp_path, config_dir=cfg)
    assert "fluent" not in three.result.tools and three.result.alias_map["fluent"] == "ansysfluent"
    assert not any(w.startswith("제조사 접두") for w in three.result.warnings)


def test_generic_vendor_is_not_a_prefix(tmp_path):
    """범용 제조사('자체개발')는 같은 행에서 떼지도, 다른 행의 접두 흡수·연계 SW명 해석에도 쓰지 않는다 (Leo Q3(b) — 자체개발 툴 자동 통합 금지)."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent / "golden"))
    import oracle
    norm = Normalizer.from_config()
    assert norm.tool_key("자체개발 유량계산기", "자체개발") == oracle.tool_key("자체개발 유량계산기", "자체개발") == "자체개발유량계산기"
    assert norm.tool_key("Ansys Fluent", "ANSYS") == oracle.tool_key("Ansys Fluent", "ANSYS") == "fluent"
    assert norm.survey_vendors(["자체개발", "ANSYS", "", None, "사내 개발", "in-house"]) == ["ansys"]
    assert norm.is_generic_vendor("자체개발") and norm.is_generic_vendor("") and not norm.is_generic_vendor("ANSYS")
    d = _copy(tmp_path)
    _set_cells(d / STR, "SW기본정보", {"STR-01": {H_NAME: "유량계산기", H_VENDOR: "자체개발"},
                                   "STR-02": {H_NAME: "자체개발 유량계산기", H_VENDOR: "자체개발"}})
    _set_cells(d / STR, "SW입출력", {"STR-01": {"연계 SW명": "자체개발 유량계산기"}})
    out = _load(d, tmp_path)
    keys = {u.sw_id: u.tool_key for u in out.result.usages}
    assert keys["STR-01"] == "유량계산기" and keys["STR-02"] == "자체개발유량계산기"            # 흡수하지 않는다
    assert not any(w.startswith("제조사 접두 흡수") for w in out.result.warnings)
    for x in (x for x in out.result.ios if x.sw_id == "STR-01"):
        assert x.partner_tools == {"자체개발유량계산기"} and x.partner_unresolved == []     # 키가 같은 툴로만 해석 (접두를 떼지 않는다)
    # 참조 계산도 같다
    r = oracle.compute(_oracle_spec([{"sw_id": "A-1", "name": "자체개발 유량계산기", "vendor": "자체개발"},
                                     {"sw_id": "A-2", "name": "유량계산기", "vendor": "자체개발"},
                                     {"sw_id": "A-3", "name": "ANSYS Fluent", "vendor": ""}, {"sw_id": "A-4", "name": "Fluent", "vendor": "ANSYS"}]),
                       REPO_ROOT)
    assert {u.sw_id: u.tool for u in r["usages"]} == {"A-1": "자체개발유량계산기", "A-2": "유량계산기", "A-3": "fluent", "A-4": "fluent"}


def _oracle_spec(usages):
    return {"template": "reference/SW조사양식_EnGenius_v1.0.xlsx", "file_name": "SW조사_{field}_{date}.xlsx", "file_date": "20260101",
            "extra_categories": [],
            "defaults": {"usage": {"purpose": "해석", "detail": "x", "phase": "전 단계", "task": "x", "env": "Windows PC", "airgap": "가능",
                                   "op": "GUI+CLI", "batch": "가능", "auto_if": "내장 스크립팅", "vv": "해당없음", "cert": "아니오", "wish": "x",
                                   "kind": "상용", "version": "1"}, "io": {"nature": "수치·표", "transfer": "파일 저장"}},
            "files": [{"field": "성능", "usages": usages, "ios": []}]}


def test_merge_config_rejects_wrong_types_with_file_and_key(tmp_path):
    """오버레이 값의 형식이 틀리면 파일·키 이름을 붙인 ValueError 로 멈춘다 — 조용히 무시하거나 AttributeError 로 죽지 않는다."""
    with pytest.raises(ValueError, match=r"data/real/config/tool_aliases.yaml aliases: 형식은"):
        merge_config("tool_aliases.yaml", {}, {"aliases": ["Excel"]})
    with pytest.raises(ValueError, match=r"tool_aliases.yaml aliases: 형식은"):
        merge_config("tool_aliases.yaml", {}, {"aliases": {"Excel": "엑셀"}})                 # 목록 자리에 문자열 (글자로 쪼개지면 안 된다)
    with pytest.raises(ValueError, match=r"tool_aliases.yaml distinct: 형식은"):
        merge_config("tool_aliases.yaml", {}, {"distinct": ["a", "b"]})
    with pytest.raises(ValueError, match=r"tool_aliases.yaml merge_keys: 형식은"):
        merge_config("tool_aliases.yaml", {}, {"merge_keys": [["b", "a"]]})
    with pytest.raises(ValueError, match=r"config/tool_aliases.yaml merge_pairs: 형식은"):
        merge_config("tool_aliases.yaml", {"merge_pairs": {"a": "b"}}, {})                  # 기준 파일도 검사
    with pytest.raises(ValueError, match=r"data/real/config/value_aliases.yaml \(파일 전체\): 형식은"):
        merge_config("value_aliases.yaml", {}, {"전달 방법": "메일"})
    with pytest.raises(ValueError, match=r"data/real/config/rules.yaml loader: 형식은 매핑"):
        merge_config("rules.yaml", {"loader": {"header_row": 2}}, {"loader": "x"})
    with pytest.raises(ValueError, match=r"rules.yaml loader.sheets.usage: 형식은 목록"):
        merge_config("rules.yaml", {"loader": {"sheets": {"usage": ["a"]}}}, {"loader": {"sheets": {"usage": "a"}}})
    with pytest.raises(ValueError, match=r"\(파일 전체\): 형식은 매핑"):
        merge_config("rules.yaml", {"a": 1}, ["x"])
    assert merge_config("tool_aliases.yaml", {"merge_pairs": [["a", "b"]], "merge_keys": {"b": "a"}},
                        {"merge_pairs": [["c", "d"]], "aliases": None, "labels": {"a": "A"}})["merge_pairs"] == [["a", "b"], ["c", "d"]]
    assert merge_config("rules.yaml", {"loader": {"x": None}}, {"loader": {"x": "v"}}) == {"loader": {"x": "v"}}
    over = tmp_path / "real_config"
    over.mkdir()
    (over / "tool_aliases.yaml").write_text("aliases: [Excel]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="tool_aliases.yaml aliases"):
        Loader(overlay_dir=over)


def test_merge_config_rejects_empty_valued_keys(tmp_path):
    """오버레이에서 값 없는 키(`loader:`·`manual_transfer_values:` — YAML None)가 매핑·목록 기본값을 None 으로 덮지 않는다 — ConfigError.
    스칼라 기본값은 None 으로 덮을 수 있고, tool_aliases 의 정해진 키(aliases 등)는 빈 값 = 빈 목록으로 본다."""
    with pytest.raises(cfgmod.ConfigError, match=r"data/real/config/rules.yaml loader: 값이 비어 있다 — 키를 지우거나 값을 적는다"):
        merge_config("rules.yaml", {"loader": {"header_row": 2}}, {"loader": None})
    with pytest.raises(cfgmod.ConfigError, match=r"rules.yaml manual_transfer_values: 값이 비어 있다"):
        merge_config("rules.yaml", {"manual_transfer_values": ["메일"]}, {"manual_transfer_values": None})
    with pytest.raises(cfgmod.ConfigError, match=r"rules.yaml loader.sheets: 값이 비어 있다"):
        merge_config("rules.yaml", {"loader": {"sheets": {"usage": ["a"]}}}, {"loader": {"sheets": None}})
    assert merge_config("rules.yaml", {"hub_top_n": 10}, {"hub_top_n": None}) == {"hub_top_n": None}
    assert merge_config("tool_aliases.yaml", {"aliases": {"Excel": ["엑셀"]}}, {"aliases": None, "labels": None})["aliases"] == {"Excel": ["엑셀"]}
    over = tmp_path / "real_config"
    over.mkdir()
    (over / "rules.yaml").write_text("manual_transfer_values:\n", encoding="utf-8")
    with pytest.raises(cfgmod.ConfigError, match="manual_transfer_values: 값이 비어 있다"):
        Loader(overlay_dir=over)
    assert issubclass(cfgmod.ConfigError, ValueError)                       # 옛 호출부의 except ValueError 도 잡는다


def test_yaml_syntax_error_is_config_error_without_values(tmp_path):
    """오버레이(또는 저장소 설정)의 YAML 문법 오류는 traceback 대신 ConfigError — 실제 파일 경로와 행·열만, 줄 내용·값은 없다."""
    over = tmp_path / "real_config"
    over.mkdir()
    (over / "rules.yaml").write_text("hub_top_n: 3\nmanual_transfer_values: [비밀툴명\nloader:\n  x: 1\n", encoding="utf-8")
    where = str((over / "rules.yaml").resolve())
    with pytest.raises(cfgmod.ConfigError, match=r"\d+행 \d+열: YAML 문법 오류 — 들여쓰기·괄호·콜론 뒤 공백을 확인") as e:
        cfgmod.load_config("rules.yaml", overlay_dir=over)
    assert str(e.value).startswith(where) and "비밀툴명" not in str(e.value)
    with pytest.raises(cfgmod.ConfigError, match="YAML 문법 오류"):
        Loader(overlay_dir=over)
    with pytest.raises(cfgmod.ConfigError, match="YAML 문법 오류"):
        Normalizer.from_config(overlay_dir=over)
    (over / "rules.yaml").write_text("- a\n- b\n", encoding="utf-8")                    # 매핑이 아닌 파일
    with pytest.raises(cfgmod.ConfigError, match=r"\(파일 전체\): 형식은 매핑"):
        cfgmod.load_config("rules.yaml", overlay_dir=over)
    (over / "rules.yaml").write_text("", encoding="utf-8")                              # 빈 파일은 빈 매핑
    assert cfgmod.load_config("rules.yaml", overlay_dir=over)[1] is True
    # 오류 문구의 경로는 실제 오버레이 폴더 (저장소 안이면 상대 경로)
    assert cfgmod.config_where(CONFIG_DIR / "rules.yaml") == "config/rules.yaml" and cfgmod.config_where(over / "x.yaml") == str((over / "x.yaml").resolve())
    (over / "rules.yaml").write_text("loader: x\n", encoding="utf-8")
    with pytest.raises(cfgmod.ConfigError, match="loader: 형식은 매핑") as e:
        cfgmod.load_config("rules.yaml", overlay_dir=over)
    assert str(e.value).startswith(where)
    # 저장소 config/ 쪽(기준 파일)도 실제 경로 — 테스트 사본은 절대 경로
    cfg = _config(tmp_path)
    (cfg / "tool_aliases.yaml").write_text("aliases: [Excel]\n", encoding="utf-8")
    with pytest.raises(cfgmod.ConfigError) as e:
        Loader(config_dir=cfg)                                                           # 오버레이 없어도 tool_aliases 형식은 검사
    assert str(e.value).startswith(str((cfg / "tool_aliases.yaml").resolve()) + " aliases: 형식은")


def test_merge_pairs_chained_across_files_recomputes_merge_keys(tmp_path):
    """3차 재검토(낮음): 저장소와 오버레이 양쪽에 merge_pairs 가 있고 사슬로 이어지면(gridgen=gridgenpro / pointwise=gridgen) 키별 덮어쓰기는
    깊이 1 이 깨져 '손으로 고친 merge_pairs' 경고가 영구히 났다. 수리: 합친 merge_pairs 에서 merge_keys 를 다시 계산 — 경고 0, amap 옳음."""
    base = {"merge_pairs": [["gridgen", "gridgenpro"]], "merge_keys": {"gridgenpro": "gridgen"}}
    over = {"merge_pairs": [["pointwise", "gridgen"]], "merge_keys": {"gridgen": "pointwise"}}
    got = merge_config("tool_aliases.yaml", base, over)
    assert got["merge_pairs"] == [["gridgen", "gridgenpro"], ["pointwise", "gridgen"]]
    assert got["merge_keys"] == {"gridgenpro": "pointwise", "gridgen": "pointwise"}
    # merge_pairs 키가 없는 쪽(옛 파일)의 merge_keys 는 쌍으로 승격해 섞는다; 양쪽 다 없으면 옛 방식(키별 덮어쓰기, merge_pairs 키 없음)
    got = merge_config("tool_aliases.yaml", {"merge_keys": {"b": "a"}}, {"merge_pairs": [["c", "a"]]})
    assert got["merge_pairs"] == [["a", "b"], ["c", "a"]] and got["merge_keys"] == {"b": "c", "a": "c"}
    got = merge_config("tool_aliases.yaml", {"merge_keys": {"b": "a"}}, {"merge_keys": {"d": "c"}})
    assert "merge_pairs" not in got and got["merge_keys"] == {"b": "a", "d": "c"}
    cfg = _config(tmp_path, tool_aliases=base)
    overd = tmp_path / "real_config"
    overd.mkdir()
    (overd / "tool_aliases.yaml").write_text(yaml.safe_dump(over), encoding="utf-8")
    w: list = []
    amap, _ = Loader(config_dir=cfg, overlay_dir=overd)._alias_map(w)
    assert w == [] and {k: amap[k] for k in ("gridgenpro", "gridgen")} == {"gridgenpro": "pointwise", "gridgen": "pointwise"}
    # 오버레이 파일의 merge_keys 가 자기 이력과 다르면(손으로 고침) 합쳐도 경고 1
    (overd / "tool_aliases.yaml").write_text(yaml.safe_dump({"merge_pairs": [["pointwise", "gridgen"]], "merge_keys": {}}), encoding="utf-8")
    w = []
    amap, _ = Loader(config_dir=cfg, overlay_dir=overd)._alias_map(w)
    assert len(w) == 1 and w[0].startswith("손으로 고친 merge_pairs") and amap["gridgen"] == "pointwise"


def test_empty_merge_pairs_means_no_merges(tmp_path):
    """3차 재검토(낮음): `merge_pairs: []` 로 비운 파일은 키가 있으므로 merge_keys 로 되돌아가지 않는다 — 통합 0, merge_keys 가 남아 있으면
    경고 1. 승격(옛 파일 호환)은 merge_pairs 키가 아예 없을 때만 (read_merge_pairs·apply-review 도 같은 규칙)."""
    from engenius_onto.normalize import read_merge_pairs
    assert read_merge_pairs({"merge_pairs": [], "merge_keys": {"b": "a"}}) == []
    assert read_merge_pairs({"merge_pairs": None, "merge_keys": {"b": "a"}}) == []
    assert read_merge_pairs({"merge_keys": {"b": "a"}}) == [["a", "b"]]
    cfg = _config(tmp_path, tool_aliases={"aliases": {}, "merge_pairs": [], "merge_keys": {"hypermesh": "nastran"}})
    w: list = []
    amap, _ = Loader(config_dir=cfg)._alias_map(w)
    assert "hypermesh" not in amap and w == ["손으로 고친 merge_pairs — merge_keys 재계산 (다음 apply-review 가 파일을 맞춘다)"]
    d = _copy(tmp_path)
    out = _load(d, tmp_path, config_dir=cfg)
    assert {"hypermesh", "nastran"} <= set(out.result.tools)
    _write_csv(tmp_path / "r.csv", [_row("mechanical", "nastran", "통합")])
    apply_review(tmp_path / "r.csv", cfg)
    saved = _aliases(cfg)
    assert saved["merge_pairs"] == [["mechanical", "nastran"]] and saved["merge_keys"] == {"nastran": "mechanical"}   # 옛 merge_keys 는 승격되지 않는다
    w = []
    assert Loader(config_dir=cfg)._alias_map(w)[0].get("nastran") == "mechanical" and w == []


def test_apply_review_normalizer_uses_overlay_rules(tmp_path, monkeypatch):
    """3차 재검토(낮음): apply-review 의 Normalizer 가 오버레이 rules.yaml(tool_token_map 등)을 읽지 않아 사슬 검사 키가 적재기와 달랐다.
    수리: 오버레이에 쓸 때(data/real/config 또는 --with-public-aliases)는 적재기처럼 그 폴더의 rules.yaml 을 config/ 위에 덮는다."""
    over = tmp_path / "real_config"
    over.mkdir()
    (over / "rules.yaml").write_text("tool_token_map:\n  f77: fortran77\n", encoding="utf-8")
    (over / "tool_aliases.yaml").write_text(yaml.safe_dump({"aliases": {"Fortran 77": ["F77"]}}, allow_unicode=True), encoding="utf-8")
    norm = Normalizer.from_config(overlay_dir=over)
    assert norm.tool_key("F77") == "fortran77" and norm.tool_key("C++") == "cpp"            # 오버레이 토큰 + 저장소 토큰 (키 단위 병합)
    _write_csv(tmp_path / "r.csv", [_row("f77", "fortran77", "별개")])
    r = apply_review(tmp_path / "r.csv", target_dir=over, overlay=True)
    assert (r.kept, r.undone) == (1, 0) and _aliases(over)["aliases"] == {"Fortran 77": ["F77"]}   # 오버레이 키로는 F77 = fortran77, 지울 변형이 없다
    assert ["f77", "fortran77"] in _aliases(over)["distinct"]
    copy = tmp_path / "copy"
    copy.mkdir()
    (copy / "tool_aliases.yaml").write_text(yaml.safe_dump({"aliases": {"Fortran 77": ["F77"]}}, allow_unicode=True), encoding="utf-8")
    r = apply_review(tmp_path / "r.csv", target_dir=copy)                                 # 독립 사본(rules 없음)은 저장소 규칙 — 'f77' 변형을 지운다
    assert (r.kept, r.undone) == (1, 1) and _aliases(copy)["aliases"] == {"Fortran 77": []}
    # CLI: --config-dir 가 사내 오버레이 폴더면 자동으로 그 rules.yaml 을 쓴다
    real = tmp_path / "real2"
    shutil.copytree(over, real)
    import engenius_onto.survey_load as sl
    from engenius_onto.cli import main
    monkeypatch.setattr(cfgmod, "REAL_CONFIG_DIR", real)
    monkeypatch.setattr(sl, "REAL_CONFIG_DIR", real)
    assert main(["apply-review", str(tmp_path / "r.csv"), "--config-dir", str(real)]) == 0
    assert _aliases(real)["aliases"] == {"Fortran 77": ["F77"]}


def test_installed_version_bom_and_full_hash_are_normalised(tmp_path, monkeypatch):
    """표식 파일에 BOM 과 40자 전체 해시가 있어도 commit 은 앞 7자 (commit_full 은 그대로); load_log 에만 전체 해시, diag 는 7자."""
    (tmp_path / "offline").mkdir()
    full = "0123456789abcdef0123456789abcdef01234567"
    (tmp_path / "offline" / "installed_commit.txt").write_bytes(b"\xef\xbb\xbf" + f"{full}\r\n61\r\n".encode("utf-8"))   # 메모장 BOM + CRLF
    v = installed_version(tmp_path)
    assert (v.commit, v.commit_full, v.number, v.source, str(v)) == ("0123456", full, 61, "installed_commit.txt", "0123456 (#61)")
    (tmp_path / "offline" / "installed_commit.txt").write_text("87881eb\n60\n", encoding="utf-8")
    assert installed_version(tmp_path) == cfgmod.InstalledVersion("87881eb", 60, "installed_commit.txt", "87881eb")
    if (REPO_ROOT / ".git").exists():
        g = installed_version(REPO_ROOT)
        assert len(g.commit) == 7 and g.commit_full.startswith(g.commit) and len(g.commit_full) == 40
    (tmp_path / "offline" / "installed_commit.txt").write_text(f"{full}\n61\n", encoding="utf-8")
    import engenius_onto.survey_load as sl
    orig = sl.installed_version
    monkeypatch.setattr(sl, "installed_version", lambda: orig(tmp_path))
    reg = tmp_path / "registry"
    copy_registry(REGISTRY_DIR, reg)
    out = run_load(registry_dir=reg, out_root=tmp_path / "out", shacl=False)
    assert out.log["installed_version"] == {"commit": "0123456", "commit_full": full, "number": 61, "source": "installed_commit.txt"}
    text = diag_text(out.out_dir)
    assert "· 설치 판 0123456 (#61) ·" in text and full not in text


REVIEW_COLS = ["툴A_키", "툴A_표기", "툴B_키", "툴B_표기", "유사도", "사유", "판정(통합/별개)", "대표 이름(통합 시)"]


def _row(a, b, verdict, rep=""):
    return dict(zip(REVIEW_COLS, [a, a, b, b, "0.9", "포함", verdict, rep]))


def _aliases(cfg: Path) -> dict:
    return yaml.safe_load((cfg / "tool_aliases.yaml").read_text(encoding="utf-8"))


def test_review_chain_in_one_csv_and_latest_label_wins(tmp_path):
    """한 CSV 의 A=B, B=C 는 한 그룹 (깊이 1), 대표 이름은 라벨로만; 직접 쌍이 아닌 별개는 오류, 직접 쌍은 이력에서 지운다."""
    cfg = _config(tmp_path)
    p = tmp_path / "r.csv"
    _write_csv(p, [_row("gridgen", "gridgenpro", "통합", "Gridgen"), _row("gridgenpro", "gridgenpromax", "통합", "Gridgen Pro")])
    r = apply_review(p, cfg)
    assert (r.merged, r.kept, r.undone) == (2, 0, 0)
    saved = _aliases(cfg)
    assert saved["merge_pairs"] == [["gridgen", "gridgenpro"], ["gridgenpro", "gridgenpromax"]]      # 판정 이력 (A 생존)
    assert saved["merge_keys"] == {"gridgenpro": "gridgen", "gridgenpromax": "gridgen"}            # 이력에서 계산, 깊이 1
    assert saved["labels"] == {"gridgen": "Gridgen Pro"}                   # 같은 그룹 — 최신 라벨이 이김, 키는 gridgen 그대로
    assert tuple(apply_review(p, cfg)) == (2, 0, 0) and _aliases(cfg) == saved   # 멱등
    _write_csv(tmp_path / "x.csv", [_row("gridgen", "gridgenpromax", "별개")])
    with pytest.raises(ValueError, match="다른 키를 거쳐"):                   # 직접 쌍이 아니다 (gridgenpro 를 거친다)
        apply_review(tmp_path / "x.csv", cfg)
    assert _aliases(cfg) == saved                                           # 오류면 파일은 그대로
    _write_csv(tmp_path / "y.csv", [_row("gridgenpromax", "gridgenpro", "별개")])      # 반대 순서로 적어도 직접 쌍
    assert tuple(apply_review(tmp_path / "y.csv", cfg)) == (0, 1, 1)
    saved = _aliases(cfg)
    assert saved["merge_pairs"] == [["gridgen", "gridgenpro"]] and saved["merge_keys"] == {"gridgenpro": "gridgen"}
    assert ["gridgenpro", "gridgenpromax"] in saved["distinct"]
    # 적재기는 aliases + merge_pairs(있으면 거기서 merge_keys 재계산) 를 추이적으로 닫는다 — 손으로 고친 이력이 무시되지 않는다
    (cfg / "tool_aliases.yaml").write_text(yaml.safe_dump({"aliases": {"Gridgen": ["Pointwise Gridgen"]},
                                                           "merge_pairs": [["zzz", "yyy"], ["pointwise", "gridgen"]],
                                                           "merge_keys": {"gridgenpro": "gridgen"}}), encoding="utf-8")   # 파일의 merge_keys 는 낡음
    w: list = []
    amap, _ = Loader(config_dir=cfg)._alias_map(w)
    assert amap == {"yyy": "zzz", "gridgen": "pointwise", "pointwisegridgen": "pointwise"}
    assert w == ["손으로 고친 merge_pairs — merge_keys 재계산 (다음 apply-review 가 파일을 맞춘다)"]
    # 이력 없이 merge_keys 만 있는 옛 파일은 merge_keys 그대로, 경고 없음
    (cfg / "tool_aliases.yaml").write_text(yaml.safe_dump({"merge_keys": {"gridgenpro": "gridgen", "gridgen": "pointwise"}}), encoding="utf-8")
    w = []
    amap, _ = Loader(config_dir=cfg)._alias_map(w)
    assert amap == {"gridgenpro": "pointwise", "gridgen": "pointwise"} and w == []


def test_loader_reads_hand_edited_merge_pairs_in_overlay(tmp_path):
    """오버레이에 merge_pairs 만 적어도(merge_keys 없음) 적재에서 통합되고 경고 한 줄 — 다음 apply-review 저장이 merge_keys 를 맞춘다."""
    d = _copy(tmp_path)
    over = tmp_path / "real_config"
    over.mkdir()
    (over / "tool_aliases.yaml").write_text("merge_pairs:\n  - [nastran, hypermesh]\n", encoding="utf-8")
    out = _load(d, tmp_path, overlay_dir=over)
    assert "hypermesh" not in out.result.tools and out.result.alias_map["hypermesh"] == "nastran"
    assert sum(w.startswith("손으로 고친 merge_pairs") for w in out.result.warnings) == 1
    _write_csv(tmp_path / "r.csv", [_row("nastran", "hypermesh", "통합")])
    apply_review(tmp_path / "r.csv", target_dir=over)
    assert _aliases(over)["merge_keys"] == {"hypermesh": "nastran"}
    out = _load(d, tmp_path / "b", overlay_dir=over)
    assert not any(w.startswith("손으로 고친 merge_pairs") for w in out.result.warnings)


def test_review_distinct_after_two_merges_keeps_third_key_with_its_partner(tmp_path):
    """검토 지적: 통합(c=b) → 통합(a=c) → 별개(a/c) 뒤 b 는 c 와만 통합이었으니 {b: c} 가 남아야 한다 (평탄화 잔류 {b: a} 금지)."""
    cfg = _config(tmp_path)
    _write_csv(tmp_path / "1.csv", [_row("c", "b", "통합")])
    apply_review(tmp_path / "1.csv", cfg)
    assert _aliases(cfg)["merge_keys"] == {"b": "c"}
    _write_csv(tmp_path / "2.csv", [_row("a", "c", "통합")])
    apply_review(tmp_path / "2.csv", cfg)
    assert _aliases(cfg)["merge_keys"] == {"b": "a", "c": "a"} and _aliases(cfg)["merge_pairs"] == [["c", "b"], ["a", "c"]]
    _write_csv(tmp_path / "3.csv", [_row("a", "c", "별개")])
    assert tuple(apply_review(tmp_path / "3.csv", cfg)) == (0, 1, 1)
    saved = _aliases(cfg)
    assert saved["merge_keys"] == {"b": "c"} and saved["merge_pairs"] == [["c", "b"]] and saved["distinct"] == [["a", "c"]]
    # 같은 CSV 안의 통합 + 별개: 최신 판정(별개)이 이긴다 — 이력에 남지 않는다
    _write_csv(tmp_path / "4.csv", [_row("x", "y", "통합", "X"), _row("x", "y", "별개")])
    assert tuple(apply_review(tmp_path / "4.csv", cfg)) == (1, 1, 1)
    saved = _aliases(cfg)
    assert ["x", "y"] not in saved["merge_pairs"] and ["x", "y"] in saved["distinct"] and "y" not in saved["merge_keys"]
    # 별개 다음 통합: distinct 에서 빠지고 이력에 들어간다
    _write_csv(tmp_path / "5.csv", [_row("y", "x", "통합")])
    apply_review(tmp_path / "5.csv", cfg)
    saved = _aliases(cfg)
    assert ["x", "y"] not in saved["distinct"] and saved["merge_keys"]["x"] == "y"


def test_review_labels_stay_on_their_keys_and_loader_names_the_group(tmp_path):
    """라벨은 판정 당시의 키에 그대로 둔다 (apply-review 는 승계·이동하지 않는다). 그룹 이름은 적재기가 고른다 —
    labels[대표 키] → 이력에서 가장 최근에 A 키로 적힌 키의 라벨 → 키 정렬 순 → 다수결. 그래서 별개로 되돌리면 a 는 c 의 이름을
    받지 않고, c 그룹(b 포함)은 'Tool C' 로 돌아간다 (2차 검증 C 절 3단계)."""
    cfg = _config(tmp_path)
    _write_csv(tmp_path / "1.csv", [_row("c", "b", "통합", "Tool C")])
    apply_review(tmp_path / "1.csv", cfg)
    assert _aliases(cfg)["labels"] == {"c": "Tool C"}
    _write_csv(tmp_path / "2.csv", [_row("a", "c", "통합")])                 # 이름 없음 — 라벨은 c 에 그대로
    apply_review(tmp_path / "2.csv", cfg)
    assert _aliases(cfg)["labels"] == {"c": "Tool C"} and _aliases(cfg)["merge_keys"] == {"b": "a", "c": "a"}
    amap, labels = Loader(config_dir=cfg)._alias_map()
    assert {k: amap[k] for k in "abc" if k in amap} == {"b": "a", "c": "a"} and labels["a"] == "Tool C"   # 대표 a 에 라벨 없음 → 최근 A 키 순(a, c) 에서 c 의 라벨
    _write_csv(tmp_path / "3.csv", [_row("a", "c", "별개")])
    assert tuple(apply_review(tmp_path / "3.csv", cfg)) == (0, 1, 1)
    assert _aliases(cfg)["labels"] == {"c": "Tool C"} and _aliases(cfg)["merge_keys"] == {"b": "c"}
    amap, labels = Loader(config_dir=cfg)._alias_map()
    assert {k: amap[k] for k in "abc" if k in amap} == {"b": "c"} and "a" not in labels and labels["c"] == "Tool C"
    _write_csv(tmp_path / "4.csv", [_row("c", "b", "통합", "Tool CB")])      # 이미 같은 그룹 — 판정 당시의 대표 키(c)에 최신 라벨
    assert tuple(apply_review(tmp_path / "4.csv", cfg)) == (1, 0, 0)
    assert _aliases(cfg)["labels"] == {"c": "Tool CB"} and _aliases(cfg)["merge_pairs"] == [["c", "b"]]
    # 손으로 적은 비대표 키 라벨도 옮기지 않는다 (merge_keys 만 있는 옛 파일 — merge_pairs 로 승격해 읽는다); 적재기가 키 정렬 순으로 고른다
    (cfg / "tool_aliases.yaml").write_text(yaml.safe_dump({"merge_keys": {"b": "c"}, "labels": {"b": "Tool B"}}), encoding="utf-8")
    _write_csv(tmp_path / "5.csv", [_row("a", "c", "통합")])
    apply_review(tmp_path / "5.csv", cfg)
    saved = _aliases(cfg)
    assert saved["merge_pairs"] == [["c", "b"], ["a", "c"]] and saved["merge_keys"] == {"b": "a", "c": "a"} and saved["labels"] == {"b": "Tool B"}
    assert Loader(config_dir=cfg)._alias_map()[1]["a"] == "Tool B"
    # 적재 끝까지 (합성 STR 파일의 툴로): 통합 hypermesh=nastran 'Tool C' → 통합 mechanical=hypermesh 이름 없음 → 별개 mechanical/hypermesh
    d = _copy(tmp_path)
    cfg2 = _config(tmp_path / "c2")
    _write_csv(tmp_path / "m1.csv", [_row("hypermesh", "nastran", "통합", "Tool C")])
    apply_review(tmp_path / "m1.csv", cfg2)
    _write_csv(tmp_path / "m2.csv", [_row("mechanical", "hypermesh", "통합")])
    apply_review(tmp_path / "m2.csv", cfg2)
    out = _load(d, tmp_path / "o1", config_dir=cfg2)
    assert {"hypermesh", "nastran"}.isdisjoint(out.result.tools) and out.result.tools["mechanical"].pref_label == "Tool C"
    assert sorted(out.result.tools["mechanical"].names) == ["ANSYS Mechanical", "HyperMesh", "NASTRAN"]
    _write_csv(tmp_path / "m3.csv", [_row("mechanical", "hypermesh", "별개")])
    apply_review(tmp_path / "m3.csv", cfg2)
    out = _load(d, tmp_path / "o2", config_dir=cfg2)
    tools = out.result.tools
    assert tools["mechanical"].pref_label == "ANSYS Mechanical" and tools["mechanical"].names == ["ANSYS Mechanical"]   # 자기 이름(다수결)으로
    assert "nastran" not in tools and tools["hypermesh"].pref_label == "Tool C"                                       # c 그룹(b 포함)은 'Tool C'
    assert sorted(tools["hypermesh"].names) == ["HyperMesh", "NASTRAN"]
    # labels 만 손으로 적은 키가 B 쪽이어도 그룹 이름이 된다 (TOOL ID 는 생존 키 것)
    cfg3 = _config(tmp_path / "c3")
    _write_csv(tmp_path / "m.csv", [_row("nastran", "hypermesh", "통합")])
    (cfg3 / "tool_aliases.yaml").write_text(yaml.safe_dump({"labels": {"hypermesh": "HyperMesh (대표)"}}), encoding="utf-8")
    apply_review(tmp_path / "m.csv", cfg3)
    assert _aliases(cfg3)["labels"] == {"hypermesh": "HyperMesh (대표)"}
    out = _load(d, tmp_path / "o3", config_dir=cfg3)
    assert "hypermesh" not in out.result.tools and out.result.tools["nastran"].pref_label == "HyperMesh (대표)"


def test_distinct_on_public_alias_is_refused_only_with_overlay(tmp_path, monkeypatch):
    """저장소 config/ 의 공개 별칭(엑셀 → Excel)으로 이어진 쌍: 오버레이(data/real/config, 또는 --with-public-aliases)에 쓸 때만 오류.
    독립 설정 사본(--config-dir)은 공개 별칭을 섞지 않으므로 별개가 그냥 기록된다."""
    _write_csv(tmp_path / "r.csv", [dict(zip(REVIEW_COLS, ["excel", "Excel", "엑셀", "엑셀", "0.5", "유사도", "별개", ""]))])
    with pytest.raises(ValueError, match="공개 별칭"):
        apply_review(tmp_path / "r.csv", target_dir=tmp_path / "overlay", overlay=True)
    r = apply_review(tmp_path / "r.csv", target_dir=tmp_path / "copy")
    assert r.kept == 1 and _aliases(tmp_path / "copy")["distinct"] == [["excel", "엑셀"]]
    from engenius_onto.cli import main
    assert main(["apply-review", str(tmp_path / "r.csv"), "--config-dir", str(tmp_path / "copy2")]) == 0
    assert main(["apply-review", str(tmp_path / "r.csv"), "--config-dir", str(tmp_path / "copy3"), "--with-public-aliases"]) == 1
    assert not (tmp_path / "copy3" / "tool_aliases.yaml").is_file()
    with pytest.raises(SystemExit):                 # apply-review 의 옛 --overlay 는 없다 (load 의 --overlay <폴더> 와 뜻이 달라 이름을 바꿈)
        main(["apply-review", str(tmp_path / "r.csv"), "--config-dir", str(tmp_path / "copy3"), "--overlay"])
    over = tmp_path / "real_config"
    import engenius_onto.survey_load as sl
    monkeypatch.setattr(cfgmod, "REAL_CONFIG_DIR", over)
    monkeypatch.setattr(sl, "REAL_CONFIG_DIR", over)
    assert main(["apply-review", str(tmp_path / "r.csv"), "--config-dir", str(over)]) == 1     # 사내 오버레이 폴더면 자동으로 섞는다
    assert main(["apply-review", str(tmp_path / "r.csv")]) == 1                                  # 실행 폴더를 모르면 오버레이 (review_target_dir)
    assert not (over / "tool_aliases.yaml").is_file()


def test_review_csv_cp949_and_registry_cp949(tmp_path):
    """엑셀 '다른 이름으로 저장' 의 cp949 CSV 도 읽고(#15), 레지스트리 CSV 도 cp949 면 읽어 utf-8-sig 로 되돌린다."""
    cfg = _config(tmp_path)
    cols = ["툴A_키", "툴A_표기", "툴B_키", "툴B_표기", "유사도", "사유", "판정(통합/별개)", "대표 이름(통합 시)"]
    _write_csv(tmp_path / "r.csv", [dict(zip(cols, ["matlab", "MATLAB", "matlabsimulink", "MATLAB Simulink", "0.7", "포함", "통합", "매트랩"]))],
               encoding="cp949")
    r = apply_review(tmp_path / "r.csv", cfg)
    assert r.encoding == "cp949" and r.merged == 1
    reg = tmp_path / "registry"
    copy_registry(REGISTRY_DIR, reg)
    text = (reg / "tools.csv").read_text(encoding="utf-8-sig")
    (reg / "tools.csv").write_bytes(text.encode("cp949"))
    rows_utf8 = Registry(REGISTRY_DIR).rows("tool")
    rg = Registry(reg)
    assert rg.rows("tool") == rows_utf8 and any("cp949" in n for n in rg.notices)
    out = run_load(registry_dir=reg, out_root=tmp_path / "o", shacl=False)
    assert any(w.startswith("레지스트리 CSV 를 cp949 로 읽음") for w in out.result.warnings)
    assert (reg / "tools.csv").read_bytes().startswith("﻿".encode("utf-8"))
    (tmp_path / "bad.csv").write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(ValueError, match="CSV UTF-8"):
        read_csv_rows(tmp_path / "bad.csv")


# --------------------------------------------------------------------------- C. 적재 이슈 보강
def test_int_empty_tokens_are_blank_without_warning(tmp_path):
    """정수 열의 'NA'·'-'·'없음' 은 빈칸 — 정수 변환 실패 경고·원문 없음, 파일당 건수 한 줄 (docs/09 #21 2단)."""
    d = _copy(tmp_path)
    _set_cells(d / STR, "SW기본정보", {"STR-01": {H_USERS: "NA", H_QTY: "-"}, "STR-02": {H_USERS: "없음"}, "STR-04": {H_USERS: "약 3명"}})
    out = _load(d, tmp_path)
    u = {u.sw_id: u for u in out.result.usages}
    assert u["STR-01"].v["user_count"] is None and u["STR-01"].v["license_count"] is None and u["STR-01"].raw == {}
    assert u["STR-02"].v["user_count"] is None and u["STR-02"].raw == {}
    assert u["STR-04"].raw == {"user_count": "약 3명"}                            # 진짜 변환 실패는 그대로 경고·원문 보존
    bad = [w for w in out.result.warnings if "정수 변환 실패" in w]
    assert len(bad) == 1 and "STR-04" in bad[0]
    assert any(w.startswith("빈 값 표기 정수 칸") and "3칸" in w for w in out.result.warnings)


def test_usage_without_io_is_a_fix_request_row(tmp_path):
    """입출력이 하나도 없는 툴사용은 '입출력 없음' 수정 요청 행 (툴사용당 1건, 확인 요청 — 정상일 수 있음), 경고는 아니다."""
    reg = tmp_path / "registry"
    copy_registry(REGISTRY_DIR, reg)
    out = run_load(registry_dir=reg, out_root=tmp_path / "out", shacl=False)
    rows = [i for i in out.result.issues if i["kind"] == "입출력 없음"]
    assert [(i["part"], i["tool_id"]) for i in rows] == [("제어", "가상-제어로직툴")]           # 골든 P4 no_io
    assert rows[0]["hint"].startswith("확인 요청 — 정상일 수 있음") and rows[0]["sheet"] == "SW기본정보" and rows[0]["row"]
    assert not any("입출력 없음" in w for w in out.result.warnings)
    ws = openpyxl.load_workbook(out.out_dir / "fix_requests" / "SW조사_제어_20260924_수정요청.xlsx").active
    assert ["Tool 기본정보", "가상-제어로직툴", "입출력 없음"] in [[r[0].value, r[2].value, r[5].value] for r in ws.iter_rows(min_row=3)]
    assert "입출력 없음 · Tool 기본정보 · Tool ID: 1" in diag_text(out.out_dir)


# --------------------------------------------------------------------------- E. 설치 판 표식
def test_installed_version_sources(tmp_path):
    """offline/installed_commit.txt (1행 해시, 2행 번호) → git HEAD → '미상' 순."""
    (tmp_path / "offline").mkdir()
    (tmp_path / "offline" / "installed_commit.txt").write_text("87881eb\n60\n", encoding="utf-8")
    v = installed_version(tmp_path)
    assert (v.commit, v.number, v.source, str(v)) == ("87881eb", 60, "installed_commit.txt", "87881eb (#60)")
    (tmp_path / "offline" / "installed_commit.txt").write_text("abc1234\n", encoding="utf-8")
    assert str(installed_version(tmp_path)) == "abc1234"
    assert installed_version(tmp_path / "nowhere") == cfgmod.InstalledVersion("미상", None, "없음")
    if (REPO_ROOT / ".git").exists():
        v = installed_version(REPO_ROOT)
        assert v.source == "git" and v.commit != "미상" and v.number
    reg = tmp_path / "registry"
    copy_registry(REGISTRY_DIR, reg)
    out = run_load(registry_dir=reg, out_root=tmp_path / "out", shacl=False)
    assert out.log["installed_version"]["commit"] == installed_version().commit
    assert "· 설치 판 " + str(installed_version()) + " ·" in diag_text(out.out_dir)


def test_vendor_absorption_closes_alias_chain_for_partner_names(tmp_path):
    """4차 재검토(중간): 흡수 뒤 alias_map 이 '엑셀'→excel→microsoftexcel 2단 사슬이 되어 공개 별칭으로 적힌 연계 SW명이 미해석으로
    떨어졌다. 수리: 흡수를 구한 뒤 사슬을 다시 닫는다 — 연계 SW명 '엑셀'·'MS Excel'·'Excel' 전부 생존 키(레지스트리 ID 유지)로."""
    d = _copy(tmp_path)
    _set_cells(d / STR, "SW기본정보", {"STR-05": {H_NAME: "Microsoft Excel", H_VENDOR: ""}})
    one = _load(d, tmp_path)                                                      # 1회차: microsoftexcel 이 활성 레지스트리 키
    tid = _tool_rows(tmp_path / "registry")["microsoftexcel"]["id"]
    _add_usage(d / STR, "STR-90", "Excel", "Microsoft")                           # 2회차: 접두 없는 'Excel'/Microsoft 행
    _set_cells(d / STR, "SW입출력", {"STR-02": {"연계 SW명": "엑셀"}, "STR-03": {"연계 SW명": "MS Excel"}, "STR-04": {"연계 SW명": "Excel"}})
    two = _load(d, tmp_path)
    keys = {u.sw_id: u.tool_key for u in two.result.usages}
    assert keys["STR-05"] == keys["STR-90"] == "microsoftexcel" and "excel" not in two.result.tools
    assert _tool_rows(tmp_path / "registry")["microsoftexcel"]["id"] == tid
    amap = two.result.alias_map
    assert amap["excel"] == amap["엑셀"] == amap["msexcel"] == "microsoftexcel"     # 사슬이 한 단으로 닫혀 있다
    for x in two.result.ios:
        if x.sw_id in ("STR-02", "STR-03", "STR-04"):
            assert x.partner_tools == {"microsoftexcel"} and x.partner_unresolved == [], (x.sw_id, x.partner_tools, x.partner_unresolved)
    assert not any("알아보지 못" in w and "엑셀" in w for w in two.result.warnings)
    assert one.result.tools["microsoftexcel"].usages[0].sw_id == "STR-05"


def test_io_tool_id_fill_down(tmp_path):
    """I22 개정 (Leo 2026-10-09 "대부분 같은 ID 라 비워 뒀다"): 입출력 시트에서 Tool ID 가 빈 내용 행은 바로 위 행의 ID 를 이어받는다.
    빈 행이 끼면 이어받지 않는다 (합성 압축기 '형상 검토 메모'), rules.yaml io_id_fill_down: false 면 예전처럼 건너뛴다."""
    d = _copy(tmp_path)
    wb = openpyxl.load_workbook(d / STR)
    ws = wb["SW입출력"]
    rows = [r for r in ws.iter_rows(min_row=4) if r[0].value == "STR-02"]
    assert len(rows) >= 3
    for r in rows[1:]:                                                            # STR-02 의 둘째 행부터 ID 를 비운다
        r[0].value = None
    wb.save(d / STR)
    ld = Loader()
    res = ld.load(ld.discover(d))
    got = sorted(x.name for x in res.ios if x.owner is not None and x.owner.sw_id == "STR-02")
    assert len(got) == len(rows)                                                 # 하나도 버리지 않고 STR-02 로
    inherited = [w for w in res.warnings if w.startswith("Tool ID 이어받음:")]
    assert len(inherited) == len(rows) - 1 and all("→ 'STR-02' (바로 위 행)" in w for w in inherited)
    assert not any(w.startswith("SW ID 없는 내용 행") for w in res.warnings)

    cfg = _config(tmp_path, rules={**yaml.safe_load((CONFIG_DIR / "rules.yaml").read_text(encoding="utf-8")),
                                   "loader": {**yaml.safe_load((CONFIG_DIR / "rules.yaml").read_text(encoding="utf-8"))["loader"],
                                              "io_id_fill_down": False}})
    off = Loader(config_dir=cfg)
    res = off.load(off.discover(d))
    assert sum(w.startswith("SW ID 없는 내용 행") for w in res.warnings) == len(rows) - 1
    assert not any(w.startswith("Tool ID 이어받음") for w in res.warnings)


def test_io_tool_id_fill_down_stops_at_blank_row():
    """합성 압축기 파일: '형상 검토 메모'(ID 없음) 위에 빈 행이 있어 이어받지 않고 건너뛴다 (골든 I22 그대로)."""
    ld = Loader()
    res = ld.load(ld.discover(DATA_SETS["synthetic"][0]))
    assert any(w.startswith("SW ID 없는 내용 행") and "형상 검토 메모" in w for w in res.warnings)
    assert not any(w.startswith("Tool ID 이어받음") for w in res.warnings)
