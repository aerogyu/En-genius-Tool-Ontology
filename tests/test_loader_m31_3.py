"""M3.1 2차 잔여 (docs/09 0장 '남음', Leo 결정 2026-10-12) — 묶음별 절.

- A. 확장자 정규화 (docs/09 #10) · 적재기 ↔ oracle 확장자 parity (docs/09 6장) · 인명 가림 헬퍼(Normalizer.looks_person·Loader._q)
- B. 파일 층 (docs/09 #1 잔여·#8 C4): 파일 간 같은 (파트, Tool ID) 구분 키(I36) · '(n)' 사본 파일명(I31·I33) · 같은 내용 파일 한 번만 ·
  규칙 밖 해시 이름 유일화 · 규칙 밖 고아 표시
합성 파일 사본만 쓴다 (공개 상용 툴 이름·가상 이름). 인명 시험 값은 가상 자리표시('가나다 책임')만.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import openpyxl
import pytest
import yaml
from rdflib import RDF, Graph

from engenius_onto import synth
from engenius_onto.config import CONFIG_DIR, read_csv_rows
from engenius_onto.loader import PERSON_MASK, FileReport, Loader, UsageRec
from engenius_onto.normalize import Normalizer
from engenius_onto.rdf_writer import SchemaTerms
from engenius_onto.survey_load import DATA_SETS, run_load

sys.path.insert(0, str(Path(__file__).parent / "golden"))
sys.path.insert(0, str(Path(__file__).parent))
import oracle  # noqa: E402
from test_oracle_rules import REPO, _spec  # noqa: E402

SURVEY_DIR, REGISTRY_DIR = DATA_SETS["synthetic"]
STR = "SW조사_구조_20260924.xlsx"
H_EXT = "파일 형식/확장자 *"


def _copy(tmp: Path, names=(STR,)) -> Path:
    d = tmp / "survey"
    d.mkdir(parents=True)
    for n in names:
        shutil.copy(SURVEY_DIR / n, d / n)
    return d


def _load(survey: Path, tmp: Path, **kw):
    return run_load(input_dir=survey, registry_dir=tmp / "registry", out_root=tmp / "out", shacl=False, **kw)


def _set_io_cells(path: Path, changes: dict[tuple[str, str], dict[str, object]]) -> None:
    """입출력 시트에서 {(SW ID, 데이터 명칭): {헤더: 값}} 로 셀을 고친다 (같은 SW ID 가 여러 행이라 명칭까지 본다)."""
    wb = openpyxl.load_workbook(path)
    ws = wb["SW입출력"]
    col = {c.value: c.column for c in ws[2] if c.value}
    hit = set()
    for r in ws.iter_rows(min_row=4):
        k = (r[0].value, r[col["데이터/산출물 명칭 *"] - 1].value)
        if k in changes:
            hit.add(k)
            for h, v in changes[k].items():
                ws.cell(r[0].row, col[h]).value = v
    assert hit == set(changes), f"고칠 행을 못 찾음: {set(changes) - hit}"
    wb.save(path)


# --------------------------------------------------------------------------- A. 확장자 (docs/09 #10) · parity · 인명 가림
# (원문, 정규화 확장자, 사내 표기, 매핑 못 한 토큰) — 적재기와 oracle 이 모두 이 답을 내야 한다 (한쪽만 바꾸면 실패).
EXT_CASES = [
    # 잠긴 사례 (tests/test_oracle_rules.py — I12·I16·I17)
    ("n/a", [], False, []),
    ("N/A", [], False, []),
    ("해당 없음", [], False, []),
    (".dat(ASCII)", ["dat"], False, []),               # 점 없는 괄호 = 주석
    ("STEP(AP214)", ["stp"], False, []),
    ("dat(사내용)", ["dat"], True, []),
    (".dat (사내 포맷)", ["dat"], True, []),
    ("비사내 csv", ["csv"], False, ["비사내"]),
    ("csvㆍxlsx", ["csv", "xlsx"], False, []),
    ("csv・xlsx", ["csv", "xlsx"], False, []),
    ("tar.gz", ["tar.gz"], False, []),
    ("cas.h5, dat.h5", ["cas.h5", "dat.h5"], False, []),
    # 형식명(.확장자) — 괄호 안 확장자를 쓰고 앞 한 단어(공백 허용)는 버린다
    ("Excel(.xlsx)", ["xlsx"], False, []),
    ("Parasolid(.x_t)", ["x_t"], False, []),
    ("Parasolid (.x_t)", ["x_t"], False, []),
    ("STEP(.stp)", ["stp"], False, []),
    ("csv, Excel(.xlsx, .xls)", ["csv", "xls", "xlsx"], False, []),
    ("Excel(.xlsx .xls)", ["xls", "xlsx"], False, []),
    ("Excel(*.xlsx)", ["xlsx"], False, []),
    ("NASTRAN(.bdf, .f06)", ["bdf", "f06"], False, []),
    ("Fluent(.cas.h5)", ["cas.h5"], False, []),
    ("Tecplot (.plt)", ["plt"], False, []),
    ("Excel（.xlsx）", ["xlsx"], False, []),            # 전각 괄호 — NFKC
    ("Excel(.xlsx)\nParasolid(.x_t)", ["x_t", "xlsx"], False, []),
    ("사내(.dat)", ["dat"], True, []),                  # 버린 형식명의 '사내' 는 사내 표기로 남는다
    ("사내 포맷(.dat)", ["dat"], True, []),
    ("dat(사내) Excel(.xlsx)", ["dat", "xlsx"], True, []),
    ("Excel(xlsx)", ["xlsx"], False, []),               # 점 없는 괄호는 주석 — 남은 excel 이 별칭으로 xlsx
    ("Parasolid(x_t)", [], False, ["parasolid"]),       # 점 없는 괄호는 주석 (결정 A) — 형식명만 남아 경고
    ("Microsoft Excel (.xlsx)", ["microsoft", "xlsx"], False, []),   # 한계 고정: 여러 단어 형식명은 앞 단어가 남는다
    ("stp igs Parasolid(.x_t)", ["igs", "stp", "x_t"], False, []),   # 앞 목록은 보존
    ("csv (.dat)", ["dat"], False, []),                 # 한계 고정: 공백 허용 한 단어 (Leo 2026-10-12 C)
    ("(.dat)", ["dat"], False, []),
    ("Excel(.xlsx", [], False, ["excel(.xlsx"]),        # 닫히지 않은 괄호는 매핑 실패
    ("Parasolid(.x_t,)", [], False, ["parasolid"]),     # 괄호 안이 '.확장자' 목록만이 아니면 주석
    ("a((.x))", ["a"], False, []),                      # 안쪽 괄호부터
    # 영문 별칭·비확장자 말·숫자만 있는 토큰
    ("Word", ["docx"], False, []),
    ("PowerPoint", ["pptx"], False, []),
    ("STEP AP214", ["stp"], False, ["ap214"]),
    ("STEP AP 214", ["stp"], False, ["ap", "214"]),     # 숫자만 있는 토큰은 확장자가 아니다 (Leo 2026-10-12)
    ("csv or xlsx", ["csv", "xlsx"], False, ["or"]),
    ("csv 또는 엑셀", ["csv", "xlsx"], False, ["또는"]),   # 골든 TEST-05 그대로
    ("txt ascii", ["txt"], False, ["ascii"]),
    ("Parasolid", [], False, ["parasolid"]),
    (".001", [], False, ["001"]),
    ("dat.001", ["dat.001"], False, []),                # 숫자 조각이 든 다중 점은 숫자만이 아니다 (다중 점 경고 대상)
    # 다중 점 — 값은 그대로 (경고는 unknown_compound)
    ("model.stp", ["model.stp"], False, []),
    # 구분자: 설정 separators + 모든 공백 문자 (docs/09 6장 parity — CR·VT 에서 적재기·oracle 이 갈렸다)
    ("xlsx\rcsv", ["csv", "xlsx"], False, []),
    ("xlsx\r\ncsv", ["csv", "xlsx"], False, []),
    ("xlsx\x0bcsv", ["csv", "xlsx"], False, []),
    ("xlsx　csv", ["csv", "xlsx"], False, []),
    ("xlsx csv", ["csv", "xlsx"], False, []),
]


@pytest.fixture(scope="module")
def norm() -> Normalizer:
    return Normalizer.from_config()          # 오버레이 없음 — data/real/config 를 읽지 않는다


@pytest.mark.parametrize("raw, exts, inhouse, bad", EXT_CASES)
def test_extension_normalization_loader_parity(norm, raw, exts, inhouse, bad):
    """I12: 적재기 Normalizer.extensions == oracle.normalize_extensions == 기대 (docs/09 #10 + 6장 parity)."""
    assert norm.extensions(raw) == (exts, inhouse, bad)
    assert oracle.normalize_extensions(raw) == (exts, inhouse, bad)


def test_extension_spec_values_parity(norm):
    """합성 명세(survey_spec.yaml)의 모든 확장자 값에서 함수끼리 같다 (엑셀을 거치지 않는 보완) — 다중 점 경고 대상은 없다."""
    vals = sorted({str(io["ext"]) for f in synth.load_spec()["files"] for io in f.get("ios", []) if "ext" in io})
    assert len(vals) >= 30
    for raw in vals:
        got = norm.extensions(raw)
        assert got == oracle.normalize_extensions(raw), raw
        assert norm.unknown_compound(got[0]) == [] == oracle.unknown_compound(got[0]), raw


def test_unknown_compound_parity(norm):
    """다중 점 토큰은 compound_extensions 밖이면 경고 대상 (값은 그대로) — Q2."""
    exts = ["model.stp", "tar.gz", "cas.h5", "x_t", "tar.bz2", "dat.001"]
    assert norm.unknown_compound(exts) == ["model.stp", "dat.001"] == oracle.unknown_compound(exts)


def test_format_name_feed_and_multi_dot_warning_oracle():
    """oracle: 'Parasolid(.x_t)' 출력 ↔ '.x_t' 입력이 Feed 로 이어지고(지금까지는 parasolid 로 끊겼다), 'model.stp' 는 값 그대로 + 경고."""
    r = oracle.compute(_spec(
        [{"sw_id": "A-1", "name": "가상-툴A", "vendor": "v"}, {"sw_id": "A-2", "name": "가상-툴B", "vendor": "v"}],
        [{"sw_id": "A-1", "dir": "out", "name": "d", "cat": "해석-결과", "ext": "Parasolid(.x_t)"},
         {"sw_id": "A-2", "dir": "in", "name": "d", "cat": "해석-결과", "ext": ".x_t"},
         {"sw_id": "A-2", "dir": "in", "name": "e", "cat": "해석-결과", "ext": "model.stp"}]), REPO)
    feeds = [(f.matched, f.confidence) for f in r["feeds"]]
    assert feeds == [(["x_t"], "보통")]
    e = next(x for x in r["ios"] if x.name == "e")
    assert e.exts == ["model.stp"]
    assert [w for w in r["warnings"] if w.startswith("확장자")] == [
        "확장자 다중 점 확인: SW조사_성능_20260101.xlsx A-2 'e' 토큰 ['model.stp'] — 그대로 사용 "
        "(묶음 확장자면 extensions.yaml compound_extensions 에 추가)"]


def test_extension_notations_e2e(tmp_path):
    """적재기 끝까지: 형식명(.확장자)·형식명 단독·다중 점·인명 유사 칸 — 경고·수정 요청표·TTL 원문 보존."""
    d = _copy(tmp_path)
    _set_io_cells(d / STR, {("STR-01", "익형 형상"): {H_EXT: "Excel(.xlsx)"},
                            ("STR-01", "해석 메시"): {H_EXT: "Parasolid"},
                            ("STR-01", "구조 메시"): {H_EXT: "model.stp"},
                            ("STR-02", "블레이드 형상"): {H_EXT: "dat 가나다 책임"}})
    out = _load(d, tmp_path)
    by = {(x.sw_id, x.name): x for x in out.result.ios}
    assert by[("STR-01", "익형 형상")].exts == ["xlsx"]
    assert by[("STR-01", "해석 메시")].exts == []
    assert by[("STR-01", "구조 메시")].exts == ["model.stp"]
    assert by[("STR-02", "블레이드 형상")].exts == ["dat"]
    w = out.result.warnings
    fail = [x for x in w if x.startswith("확장자 매핑 실패")]
    assert f"확장자 매핑 실패: {STR} STR-01 '해석 메시' 토큰 ['parasolid'] — 원문 보존" in fail
    multi = [x for x in w if x.startswith("확장자 다중 점 확인")]
    assert multi == [f"확장자 다중 점 확인: {STR} STR-01 '구조 메시' 토큰 ['model.stp'] — 그대로 사용 "
                     "(묶음 확장자면 extensions.yaml compound_extensions 에 추가)"]
    person = [x for x in fail if "STR-02" in x]
    assert person == [f"확장자 매핑 실패: {STR} STR-02 '블레이드 형상' 토큰 {PERSON_MASK} — 원문 보존"]
    assert not any("가나다" in x for x in w)                                         # 경고에 값이 옮겨지지 않는다
    assert any(x.startswith("인명 유사 패턴:") and "STR-02" in x and H_EXT in x for x in w)
    issues = [i for i in out.result.issues if i["kind"] == "확장자 확인"]
    assert sorted((i["tool_id"], i["value"]) for i in issues) == [("STR-01", "Parasolid"), ("STR-01", "model.stp"), ("STR-02", "")]
    assert all(i["column"] == "파일 형식/확장자" and i["sheet"] == "SW입출력" for i in issues)
    assert not any("가나다" in str(i["value"]) for i in out.result.issues)
    assert '"Excel(.xlsx)"' in out.turtle                                                  # 원문 보존 (IO 해시 ID 도 원문 기준)
    log_text = (out.out_dir / "load_log.json").read_text(encoding="utf-8")
    diag = (out.out_dir / "diag.txt").read_text(encoding="utf-8")
    assert "확장자 다중 점 확인" in diag and "model.stp" not in diag and "Parasolid" not in diag
    assert "확장자 다중 점 확인" in log_text


def test_extension_warnings_on_synthetic_unchanged(tmp_path):
    """합성 전체 적재: 확장자 경고는 골든 TEST-05 '또는' 1건 그대로, 수정 요청표에는 그 칸의 '확장자 확인' 1행이 더해진다."""
    reg = tmp_path / "registry"
    shutil.copytree(REGISTRY_DIR, reg)
    out = run_load(registry_dir=reg, out_root=tmp_path / "out", shacl=False, save_registry=False)
    ext_w = [x for x in out.result.warnings if x.startswith("확장자")]
    assert len(ext_w) == 1 and "['또는']" in ext_w[0]
    rows = [i for i in out.result.issues if i["kind"] == "확장자 확인"]
    assert [(i["tool_id"], i["value"]) for i in rows] == [("TEST-05", "csv 또는 엑셀")]


def test_extensions_overlay(tmp_path):
    """사내 오버레이 extensions.yaml: aliases 는 키별로 합쳐지고 별칭이 비확장자 목록보다 먼저, 목록 키는 통째 교체."""
    over = tmp_path / "real_config"
    over.mkdir()
    (over / "extensions.yaml").write_text(yaml.safe_dump({"aliases": {"parasolid": "x_t"}, "non_extension_tokens": ["or"]},
                                                         allow_unicode=True), encoding="utf-8")
    n = Normalizer.from_config(overlay_dir=over)
    assert n.extensions("Parasolid") == (["x_t"], False, [])            # 별칭 우선 (기본 목록에 parasolid 가 있어도)
    assert n.extensions("STEP AP214") == (["ap214", "stp"], False, [])  # 목록은 통째 교체 — ap214 는 이제 확장자
    assert n.extensions("csv or xlsx") == (["csv", "xlsx"], False, ["or"])
    assert n.extensions("Excel") == (["xlsx"], False, [])               # 기본 별칭은 그대로 (키별 병합)
    ld = Loader(overlay_dir=over)
    assert "extensions.yaml" in ld.overlay_files and ld.norm.extensions("Parasolid")[0] == ["x_t"]


def test_person_mask_helpers(norm):
    """공통 인명 가림 헬퍼: Normalizer.looks_person(person_pattern·person_patterns_all) ↔ Loader._looks_person 위임 ↔ Loader._q."""
    for s in ("가나다 책임", "책임(내선", "내선 1234", "010-1234-5678", "가나다 파트장님"):
        assert norm.looks_person(s), s
    for s in ("", None, "익형 형상", "Excel(.xlsx)", "STEP AP 214"):
        assert not norm.looks_person(s), s
    ld = Loader()
    assert ld._looks_person("dat 가나다 책임") and not ld._looks_person("dat")
    assert ld._q("dat 가나다 책임") == PERSON_MASK == "[인명 유사 — 값 생략]"
    assert ld._q("익형 형상") == "익형 형상" and ld._q(None) == ""


# --------------------------------------------------------------------------- B. 파일 층 (docs/09 #1 잔여 · #8 C4)
TURB = "SW조사_터빈_20260924.xlsx"
H_NAME = "SW명(정식) *"
OFF_RULE_TAG = re.compile(r"@file-[0-9a-f]{10}$")


def _place(survey: Path, src: str, name: str) -> Path:
    """합성 파일 src 를 survey 폴더에 name 으로 복사."""
    survey.mkdir(parents=True, exist_ok=True)
    shutil.copy(SURVEY_DIR / src, survey / name)
    return survey / name


def _rename_ids(path: Path, ids: dict[str, str]) -> None:
    """두 시트의 Tool ID 를 바꾼다 ({옛 ID: 새 ID})."""
    wb = openpyxl.load_workbook(path)
    for sheet in ("SW기본정보", "SW입출력"):
        for row in wb[sheet].iter_rows(min_row=4):
            if row[0].value in ids:
                row[0].value = ids[row[0].value]
    wb.save(path)


def _set_names(path: Path, names: dict[str, str]) -> None:
    """기본정보 시트의 SW명을 바꾼다 ({Tool ID: 새 이름}) — 두 번 나오는 STR-03 은 쓰지 않는다."""
    wb = openpyxl.load_workbook(path)
    ws = wb["SW기본정보"]
    col = {c.value: c.column for c in ws[2] if c.value}
    for r in ws.iter_rows(min_row=4):
        if r[0].value in names:
            ws.cell(r[0].row, col[H_NAME]).value = names[r[0].value]
    wb.save(path)


def _parts_config(tmp: Path) -> Path:
    """묶음 파일 MDX(= MDA + MDB) 설정 사본 (test_loader_m31.py 묶음 시험과 같은 가상 파트)."""
    cfg = tmp / "config"
    shutil.copytree(CONFIG_DIR, cfg)
    (cfg / "parts.yaml").write_text(yaml.safe_dump(
        {"parts": {"MDA": {"name": "가상 A 파트", "domains": ["구조"]}, "MDB": {"name": "가상 B 파트", "domains": ["구조"]}},
         "file_bundles": {"MDX": ["MDA", "MDB"]}}, allow_unicode=True), encoding="utf-8")
    return cfg


def _one_each(out) -> tuple[Graph, SchemaTerms]:
    """그래프 1:1 불변식 — 툴사용마다 usage_tool·reported_tool_name·loaded_in 하나, 입출력마다 loaded_in 하나, 툴사용 노드 = 행."""
    t = SchemaTerms.load()
    g = Graph().parse(data=out.turtle, format="turtle")
    uses = set(g.subjects(RDF.type, t.classes["ToolUsage"]))
    for s in uses:
        for p in ("usage_tool", "reported_tool_name", "loaded_in"):
            assert len(list(g.objects(s, t.props[p]))) == 1, (s, p)
    for s in g.subjects(RDF.type, t.classes["IOSpec"]):
        assert len(list(g.objects(s, t.props["loaded_in"]))) == 1, s
    assert len(uses) == len(out.result.usages)
    return g, t


def _bundle_and_split(survey: Path) -> None:
    """묶음 파일 MDX(MDA-1·MDA-2·MDB-1~3) + 분할된 전용 파일 MDA(MDA-1 은 이름이 바뀜)."""
    b = _place(survey, STR, "Tool조사_MDX_20260930.xlsx")
    _rename_ids(b, {"STR-01": "MDA-1", "STR-02": "MDA-2", "STR-03": "MDB-1", "STR-04": "MDB-2", "STR-05": "MDB-3"})
    s = _place(survey, STR, "Tool조사_MDA_20261005.xlsx")
    _rename_ids(s, {"STR-01": "MDA-1", "STR-02": "MDA-2"})
    _set_names(s, {"MDA-1": "가상-분할후툴"})


def _two_off_rule(survey: Path, names_b: dict[str, str] | None = None, names_both: dict[str, str] | None = None) -> None:
    """규칙 밖 이름(가상 인명 토큰 '가상인')의 구조 파일 사본 둘 — b 는 STR-01 이름을 바꿔 내용이 다르다."""
    a = _place(survey, STR, "Tool조사_구조_가상인_20260930.xlsx")
    b = _place(survey, STR, "Tool조사_가상인_구조_20260930.xlsx")
    _set_names(b, {"STR-01": "가상-다른툴", **(names_b or {})})
    for p in (a, b):
        if names_both:
            _set_names(p, names_both)


def _registry_rows(reg: Path) -> list[dict]:
    return read_csv_rows(reg / "usages.csv")[0]


def _blob(out, reg: Path) -> str:
    """산출물 전부 (그래프·로그·diag·레지스트리 CSV·수정 요청표 파일 이름)."""
    parts = [out.turtle, (out.out_dir / "load_log.json").read_text(encoding="utf-8"), (out.out_dir / "diag.txt").read_text(encoding="utf-8")]
    parts += [p.read_text(encoding="utf-8-sig") for p in sorted(reg.glob("*.csv"))]
    parts += [p.name for p in (out.out_dir / "fix_requests").iterdir()]
    return "\n".join(parts)


def test_cross_file_bundle_and_split_file_kept_apart(tmp_path):
    """I36: 묶음 파일 + 분할 전용 파일의 같은 (파트, Tool ID) — 둘 다 적재, 전용 파일 행만 원래 키(원래 USE ID), 묶음 행은 '@MDX'.
    (고치기 전: 툴사용 10행이 노드 8개, USE 하나에 usage_tool·loaded_in 2개 — 경고 없음)"""
    cfg = _parts_config(tmp_path)
    reg = tmp_path / "registry"
    first = tmp_path / "first"
    _rename_ids(_place(first, STR, "Tool조사_MDX_20260930.xlsx"),
                {"STR-01": "MDA-1", "STR-02": "MDA-2", "STR-03": "MDB-1", "STR-04": "MDB-2", "STR-05": "MDB-3"})
    before = run_load(input_dir=first, registry_dir=reg, out_root=tmp_path / "o1", shacl=False, config_dir=cfg)
    use_before = {u.sw_id: u.node_id for u in before.result.usages}
    survey = tmp_path / "survey"
    _bundle_and_split(survey)
    out = run_load(input_dir=survey, registry_dir=reg, out_root=tmp_path / "o2", shacl=False, config_dir=cfg)
    w = [x for x in out.result.warnings if x.startswith("파일 간 같은 (파트, Tool ID)")]
    assert w == ["파일 간 같은 (파트, Tool ID): MDA — Tool조사_MDA_20261005.xlsx ↔ Tool조사_MDX_20260930.xlsx 2건 "
                 "(예: MDA-1, MDA-2) — 둘 다 적재, 구분 키 Tool조사_MDX_20260930.xlsx 쪽 '@MDX'"]
    mda1 = {u.file: u for u in out.result.usages if u.sw_id == "MDA-1"}
    assert mda1["Tool조사_MDA_20261005.xlsx"].reg_tag == "" and mda1["Tool조사_MDX_20260930.xlsx"].reg_tag == "MDX"
    assert mda1["Tool조사_MDA_20261005.xlsx"].node_id == use_before["MDA-1"]           # 키 (MDA, MDA-1) 의 ID 는 전용 파일 행으로
    assert mda1["Tool조사_MDX_20260930.xlsx"].node_id not in use_before.values()       # 묶음 행은 새 ID
    keys = {r["source_key"] for r in _registry_rows(reg)}
    assert {"MDA-1", "MDA-1@MDX", "MDA-2", "MDA-2@MDX", "MDB-1"} <= keys
    _one_each(out)
    assert not any(x.startswith("규칙 밖 파일의 Tool ID") for x in out.result.warnings)
    again = run_load(input_dir=survey, registry_dir=reg, out_root=tmp_path / "o3", shacl=False, config_dir=cfg)
    assert {(u.file, u.sw_id): u.node_id for u in again.result.usages} == {(u.file, u.sw_id): u.node_id for u in out.result.usages}


def test_cross_file_off_rule_files_tagged_by_content_hash(tmp_path):
    """I36: 규칙 밖 파일끼리(파트 미상) 같은 Tool ID — 전용 파일이 없어 둘 다 '@file-<sha10>', 원래 파일명은 어디에도 없다 (C4).
    (고치기 전: ('', STR-xx) 키로 10행이 USE 5개에 병합)"""
    survey = tmp_path / "survey"
    _two_off_rule(survey)
    reg = tmp_path / "registry"
    out = run_load(input_dir=survey, registry_dir=reg, out_root=tmp_path / "out", shacl=False)
    w = [x for x in out.result.warnings if x.startswith("파일 간 같은 (파트, Tool ID)")]
    assert len(w) == 1 and w[0].startswith("파일 간 같은 (파트, Tool ID): (파트 미상) — Tool조사_규칙밖_") and " 5건 (예: STR-01, STR-02, STR-03)" in w[0]
    rows = _registry_rows(reg)
    assert len(rows) == len(out.result.usages) == 10
    assert all(OFF_RULE_TAG.search(r["source_key"]) for r in rows)
    shas = {f.sha256[:10] for f in out.result.files}
    assert {u.reg_tag for u in out.result.usages} == {f"file-{s}" for s in shas}
    _one_each(out)
    blob = _blob(out, reg)
    assert "가상인" not in blob


def test_generic_name_rows_not_merged_across_files(tmp_path):
    """I34·I36: 두 규칙 밖 파일의 '자체개발' 행은 행별 '미상:' 키도 구분 꼬리로 갈린다 (고치기 전: '미상:/STR-02' 하나로 합쳐짐)."""
    survey = tmp_path / "survey"
    _two_off_rule(survey, names_both={"STR-02": "자체개발"})
    out = _load(survey, tmp_path)
    generic = {k: g for k, g in out.result.tools.items() if k.startswith("미상:")}
    assert len(generic) == 2 and all(len(g.usages) == 1 for g in generic.values())
    assert all(re.fullmatch(r"미상:/STR-02@file-[0-9a-f]{10}", k) for k in generic)
    _one_each(out)


def test_off_rule_overlap_warning(tmp_path):
    """규칙 밖 사본(이름만 틀린 수정본)의 Tool ID 가 규칙 안 파일과 겹치면 경고 — 파트가 달라 병합은 없고 둘 다 적재."""
    survey = tmp_path / "survey"
    _place(survey, STR, STR)
    _set_names(_place(survey, STR, "SW조사_구조_20260924 - 복사본.xlsx"), {"STR-02": "가상-수정툴"})
    out = _load(survey, tmp_path)
    w = [x for x in out.result.warnings if x.startswith("규칙 밖 파일의 Tool ID")]
    assert len(w) == 1 and re.fullmatch(r"규칙 밖 파일의 Tool ID 가 다른 파일과 겹침: Tool조사_규칙밖_[0-9a-f]{10}\.xlsx ↔ "
                                        r"SW조사_구조_20260924\.xlsx 5개 — 재발송·사본이면 파일명을 규칙대로 고치세요 \(둘 다 적재\)", w[0])
    assert not any(x.startswith("파일 간 같은") for x in out.result.warnings)
    assert all(u.reg_tag == "" for u in out.result.usages)
    _one_each(out)


def _toy(ld: Loader, files: dict[str, tuple[str | None, str]], rows: list[tuple[str, str, str]]):
    """단위 시험용 레코드 — files: 기록 이름 → (약칭 | None, sha256), rows: (파일, 파트, Tool ID)."""
    reps = {n: FileReport(n, sha, code, None) for n, (code, sha) in files.items()}
    us = [UsageRec(f, files[f][0], i + 4, {"source_key": sid}, part=part or None) for i, (f, part, sid) in enumerate(rows)]
    return reps, us


TOY_FILES = {"Tool조사_MDA_20261005.xlsx": ("MDA", "1" * 64), "Tool조사_MDX_20260930.xlsx": ("MDX", "2" * 64),
             "Tool조사_규칙밖_aaaaaaaaaa.xlsx": (None, "a" * 64), "Tool조사_규칙밖_bbbbbbbbbb.xlsx": (None, "b" * 64),
             "Tool조사_구조_20260924.xlsx": ("구조", "3" * 64)}
TOY_ROWS = [("Tool조사_MDA_20261005.xlsx", "MDA", "MDA-1"), ("Tool조사_MDA_20261005.xlsx", "MDA", "MDA-2"),
            ("Tool조사_MDX_20260930.xlsx", "MDA", "MDA-1"), ("Tool조사_MDX_20260930.xlsx", "MDA", "MDA-02"),
            ("Tool조사_MDX_20260930.xlsx", "MDB", "MDB-1"),
            ("Tool조사_규칙밖_aaaaaaaaaa.xlsx", "", "STR-01"), ("Tool조사_규칙밖_aaaaaaaaaa.xlsx", "", "STR-02"),
            ("Tool조사_규칙밖_bbbbbbbbbb.xlsx", "", "STR-01"), ("Tool조사_규칙밖_bbbbbbbbbb.xlsx", "", "STR-9"),
            ("Tool조사_구조_20260924.xlsx", "구조", "STR-01"), ("Tool조사_구조_20260924.xlsx", "구조", "STR-02")]


def test_cross_file_tag_rule_matches_oracle():
    """I36 적재기 Loader._cross_file ↔ 참조 계산 oracle.cross_file_tags — 같은 레코드에 같은 꼬리·같은 경고 (독립 구현)."""
    ld = Loader()
    reps, us = _toy(ld, TOY_FILES, TOY_ROWS)
    w_loader: list[str] = []
    ld._cross_file(us, reps, w_loader)
    ous = [oracle.Usage(f, files_code, part, sid, "n", "v", "상용", None, None, None, None, None, None)
           for (f, part, sid), files_code in ((r, TOY_FILES[r[0]][0]) for r in TOY_ROWS)]
    w_oracle: list[str] = []
    per = {n: {"warnings": 0} for n in TOY_FILES}
    oracle.cross_file_tags(ous, TOY_FILES, w_oracle, per)
    assert w_loader == w_oracle
    assert [u.reg_tag for u in us] == [u.reg_tag for u in ous] == ["", "", "MDX", "", "", "file-aaaaaaaaaa", "", "file-bbbbbbbbbb", "", "", ""]
    assert [u.key for u in us] == [u.key for u in ous]
    assert {n: r.warnings for n, r in reps.items()} == {n: v["warnings"] for n, v in per.items()}
    assert w_loader == [
        "파일 간 같은 (파트, Tool ID): (파트 미상) — Tool조사_규칙밖_aaaaaaaaaa.xlsx ↔ Tool조사_규칙밖_bbbbbbbbbb.xlsx 1건 (예: STR-01) — 둘 다 적재, "
        "구분 키 Tool조사_규칙밖_aaaaaaaaaa.xlsx 쪽 '@file-aaaaaaaaaa', Tool조사_규칙밖_bbbbbbbbbb.xlsx 쪽 '@file-bbbbbbbbbb'",
        "파일 간 같은 (파트, Tool ID): MDA — Tool조사_MDA_20261005.xlsx ↔ Tool조사_MDX_20260930.xlsx 2건 (예: MDA-1, MDA-02=MDA-2) — 둘 다 적재, "
        "구분 키 Tool조사_MDX_20260930.xlsx 쪽 '@MDX'",
        "규칙 밖 파일의 Tool ID 가 다른 파일과 겹침: Tool조사_규칙밖_aaaaaaaaaa.xlsx ↔ Tool조사_구조_20260924.xlsx 2개 — 재발송·사본이면 파일명을 규칙대로 고치세요 (둘 다 적재)",
        "규칙 밖 파일의 Tool ID 가 다른 파일과 겹침: Tool조사_규칙밖_bbbbbbbbbb.xlsx ↔ Tool조사_구조_20260924.xlsx 1개 — 재발송·사본이면 파일명을 규칙대로 고치세요 (둘 다 적재)"]


def test_cross_file_notation_only_difference_warns_without_tag():
    """표기만 다른 Tool ID('MDA-01'/'MDA-1')는 레지스트리 키가 이미 달라 꼬리 없이 경고만."""
    ld = Loader()
    files = {"Tool조사_MDA_20261005.xlsx": ("MDA", "1" * 64), "Tool조사_MDX_20260930.xlsx": ("MDX", "2" * 64)}
    reps, us = _toy(ld, files, [("Tool조사_MDA_20261005.xlsx", "MDA", "MDA-1"), ("Tool조사_MDX_20260930.xlsx", "MDA", "MDA-01")])
    w: list[str] = []
    ld._cross_file(us, reps, w)
    assert [u.reg_tag for u in us] == ["", ""]
    assert w == ["파일 간 같은 (파트, Tool ID): MDA — Tool조사_MDA_20261005.xlsx ↔ Tool조사_MDX_20260930.xlsx 1건 (예: MDA-01=MDA-1) — "
                 "둘 다 적재 (Tool ID 표기가 달라 키는 이미 다름)"]


def test_cross_file_warning_masks_person_like_id():
    """C5: 겹친 Tool ID 칸이 인명 유사면 경고에 값 대신 가림 문구 (꼬리는 파일 해시라 인명이 없다)."""
    ld = Loader()
    files = {"Tool조사_규칙밖_aaaaaaaaaa.xlsx": (None, "a" * 64), "Tool조사_규칙밖_bbbbbbbbbb.xlsx": (None, "b" * 64)}
    reps, us = _toy(ld, files, [("Tool조사_규칙밖_aaaaaaaaaa.xlsx", "", "가나다 책임"), ("Tool조사_규칙밖_bbbbbbbbbb.xlsx", "", "가나다 책임")])
    w: list[str] = []
    ld._cross_file(us, reps, w)
    assert len(w) == 1 and f"(예: {PERSON_MASK})" in w[0] and "가나다" not in w[0]
    assert [u.reg_tag for u in us] == ["file-aaaaaaaaaa", "file-bbbbbbbbbb"]


def test_copy_suffix_joins_resend_rule(tmp_path):
    """I31·I33: 브라우저 사본 '(1)'·' (2)' 는 규칙 안 이름 — 같은 날짜면 사본 번호가 큰 쪽이 최신 (원본·'(1)' 은 재발송으로 대체).
    파트 키라서 USE ID 는 원본만 적재했을 때와 같다. (고치기 전: 사본은 규칙 밖으로 따로 적재, 툴사용 2배)"""
    reg = tmp_path / "registry"
    base = tmp_path / "base"
    _place(base, STR, STR)
    before = run_load(input_dir=base, registry_dir=reg, out_root=tmp_path / "o1", shacl=False)
    survey = tmp_path / "survey"
    _place(survey, STR, STR)
    _set_names(_place(survey, STR, "SW조사_구조_20260924(1).xlsx"), {"STR-01": "가상-사본1툴"})
    _set_names(_place(survey, STR, "SW조사_구조_20260924 (2).xlsx"), {"STR-02": "가상-사본2툴"})
    out = run_load(input_dir=survey, registry_dir=reg, out_root=tmp_path / "o2", shacl=False)
    assert [f.name for f in out.result.loaded_files] == ["SW조사_구조_20260924 (2).xlsx"]
    resend = sorted(x for x in out.result.warnings if x.startswith("재발송으로 대체"))
    assert resend == ["재발송으로 대체: SW조사_구조_20260924(1).xlsx → SW조사_구조_20260924 (2).xlsx (적재 안 함)",
                      "재발송으로 대체: SW조사_구조_20260924.xlsx → SW조사_구조_20260924 (2).xlsx (적재 안 함)"]
    assert "가상-사본1툴" not in out.turtle and "가상-사본2툴" in out.turtle
    files = {f["name"]: f for f in out.log["files"]}
    assert set(files) == {STR, "SW조사_구조_20260924(1).xlsx", "SW조사_구조_20260924 (2).xlsx"}
    assert files["SW조사_구조_20260924 (2).xlsx"]["copy"] == 2 and files[STR]["copy"] == 0
    assert not any("규칙밖" in n or "규칙 밖" in x for n in files for x in out.result.warnings)
    assert {u.sw_id: u.node_id for u in out.result.usages} == {u.sw_id: u.node_id for u in before.result.usages}


def test_identical_in_rule_copy_is_resend_same_content(tmp_path):
    """C3 순서: 내용 같은 '(1)' 사본은 I33 이 먼저 처리 — '재발송으로 대체 … (내용 같음)', '같은 내용 파일' 경고는 없다."""
    survey = tmp_path / "survey"
    _place(survey, STR, STR)
    _place(survey, STR, "SW조사_구조_20260924(1).xlsx")
    out = _load(survey, tmp_path)
    assert [x for x in out.result.warnings if x.startswith(("재발송으로 대체", "같은 내용 파일"))] == [
        "재발송으로 대체: SW조사_구조_20260924.xlsx → SW조사_구조_20260924(1).xlsx (적재 안 함) (내용 같음)"]
    assert len(out.result.usages) == 5


def test_same_content_file_loaded_once(tmp_path):
    """I33 뒤 같은 내용(sha256) 파일은 한 번만 — 규칙 안 파일을 남기고 규칙 밖 사본은 '같은 내용 파일' (제외 건수에 넣지 않음).
    (고치기 전: 같은 내용이 두 번 적재돼 툴사용 2배)"""
    survey = tmp_path / "survey"
    _place(survey, STR, STR)
    _place(survey, STR, "SW조사_구조_20260924 - 복사본.xlsx")
    out = _load(survey, tmp_path)
    same = [x for x in out.result.warnings if x.startswith("같은 내용 파일")]
    assert len(same) == 1 and re.fullmatch(r"같은 내용 파일: Tool조사_규칙밖_[0-9a-f]{10}\.xlsx = SW조사_구조_20260924\.xlsx \(한 번만 적재\)", same[0])
    assert len(out.result.usages) == 5 and [f.name for f in out.result.loaded_files] == [STR]
    assert not any(x.startswith("규칙 밖 파일의 Tool ID") for x in out.result.warnings)
    g, t = _one_each(out)
    assert len(set(g.subjects(RDF.type, t.classes["SurveyLoad"]))) == 1
    dup = next(f for f in out.log["files"] if f["name"] != STR)
    assert dup["duplicate_of"] == STR and dup["load_id"] is None and dup["index"] in (1, 2)
    assert sum(f["excluded"] for f in out.log["files"]) == len(out.result.excluded_rows)
    diag = (out.out_dir / "diag.txt").read_text(encoding="utf-8")
    assert "파일 2 (적재 1 · 재발송 대체 0 · 같은 내용 1 · 읽지 못함 0)" in diag


def test_off_rule_identical_copies_get_unique_labels(tmp_path):
    """#8: 내용 같은 규칙 밖 사본 둘은 해시 이름이 같았다 — 둘째에 '-2' (LOAD ID 덮어쓰기·거짓 '완전 중복 입출력 행'·수정 요청표 덮어쓰기가 없어진다)."""
    survey = tmp_path / "survey"
    _place(survey, STR, "SW조사_구조_20260924 - 복사본.xlsx")
    _place(survey, STR, "SW조사_구조_20260924 - 복사본 (2).xlsx")
    out = _load(survey, tmp_path)
    names = [f.name for f in out.result.files]
    sha10 = out.result.files[0].sha256[:10]
    assert names == [f"Tool조사_규칙밖_{sha10}.xlsx", f"Tool조사_규칙밖_{sha10}-2.xlsx"]
    assert [f["index"] for f in out.log["files"]] == [1, 2]
    assert Loader().parse_name(names[1]) == (None, None, 0)                    # 유일화한 이름도 파일명 규칙 밖
    assert len(out.result.per_file()) == 2 and len(out.result.loaded_files) == 1
    assert not any(x.startswith("완전 중복 입출력 행") for x in out.result.warnings)
    assert len(list((out.out_dir / "fix_requests").iterdir())) == 1
    _one_each(out)


def test_off_rule_orphan_io_not_merged(tmp_path):
    """규칙 밖 파일 둘(내용 다름)의 고아 입출력은 서로 다른 노드, 표시 키는 '(파트 미상)/…(고아)' ('None/' 이 아니다)."""
    survey = tmp_path / "survey"
    _place(survey, TURB, "SW조사_터빈_20260924 - 복사본.xlsx")
    b = _place(survey, TURB, "SW조사_터빈_20260924 - 복사본 (2).xlsx")
    _set_names(b, {"TURB-01": "가상-다른툴"})              # 고아 행은 그대로, 파일 내용만 다르게 (같은 내용이면 한 번만 적재)
    out = _load(survey, tmp_path)
    orphans = [x for x in out.result.ios if x.owner is None]
    assert len(orphans) == 2 and len({x.node_id for x in orphans}) == 2
    assert all(x.key.startswith("(파트 미상)/TURB-9(고아)/") for x in orphans)
    assert "None/" not in json.dumps(out.log, ensure_ascii=False)
    assert not any(x.startswith("완전 중복 입출력 행") for x in out.result.warnings)
    _one_each(out)
