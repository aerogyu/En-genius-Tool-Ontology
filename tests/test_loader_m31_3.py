"""M3.1 2차 잔여 (docs/09 0장 '남음', Leo 결정 2026-10-12) — 묶음별 절.

- A. 확장자 정규화 (docs/09 #10) · 적재기 ↔ oracle 확장자 parity (docs/09 6장) · 인명 가림 헬퍼(Normalizer.looks_person·Loader._q)
- B. 파일 층 (docs/09 #1 잔여·#8 C4): 파일 간 같은 (파트, Tool ID) 구분 키(I36) · '(n)' 사본 파일명(I31·I33) · 같은 내용 파일 한 번만 ·
  규칙 밖 해시 이름 유일화 · 규칙 밖 고아 표시
- C. 예시와 거의 같은 행 (docs/09 #3, I15 개정): 정보 열 기준 유사 판별·경고 · 중복 Tool ID 면 예시 유사 행을 빼고 진짜 행 ·
  설정 낡음 점검(시트별) · rules 오버레이 문턱 · template_examples 오버레이·template-examples --overlay · 적재기 ↔ oracle 판별식
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
from engenius_onto.config import CONFIG_DIR, ConfigError, merge_config, read_csv_rows
from engenius_onto.loader import IO_SHEET, PERSON_MASK, USAGE_SHEET, FileReport, Loader, UsageRec
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


# --------------------------------------------------------------------------- C. 예시와 거의 같은 행 (docs/09 #3, I15 개정)
SAS = "SW조사_2차유로(SAS)_20260924.xlsx"
NEAR_W = "예시와 거의 같은 행"
SWAP_W = "중복 SW ID — 예시 유사 행 제외"
STALE_W = "예시 행 판별 설정 점검"
NEAR_HINT = "양식 예시와 거의 같습니다 — 남은 예시면 지우고, 실제 응답이면 예시 문구(비고 등)를 실제 내용으로 고쳐 주세요"


def _cols(ws) -> dict[str, int]:
    """헤더 → 열 번호 (헤더 끝의 ' *' 는 떼고 비교)."""
    return {str(c.value).rstrip(" *"): c.column for c in ws[2] if c.value}


def _set_row(path: Path, sheet: str, row: int, changes: dict[str, object]) -> None:
    """행 번호로 셀을 고친다 ({헤더: 값}) — SAS 파일은 예시 4행과 진짜 5행이 같은 SAS-01 이라 SW ID 로는 행을 못 고른다."""
    wb = openpyxl.load_workbook(path)
    ws = wb[sheet]
    col = _cols(ws)
    for h, v in changes.items():
        ws.cell(row, col[h.rstrip(" *")]).value = v
    wb.save(path)


def _clear_row(path: Path, sheet: str, row: int) -> None:
    wb = openpyxl.load_workbook(path)
    ws = wb[sheet]
    for c in range(1, ws.max_column + 1):
        ws.cell(row, c).value = None
    wb.save(path)


def _append_row(path: Path, sheet: str, values: dict[str, object]) -> int:
    """마지막 내용 행 바로 아래에 한 행을 쓴다 ({헤더: 값}) → 행 번호."""
    wb = openpyxl.load_workbook(path)
    ws = wb[sheet]
    col = _cols(ws)
    row = max(r[0].row for r in ws.iter_rows(min_row=4) if r[0].value is not None) + 1
    for h, v in values.items():
        ws.cell(row, col[h.rstrip(" *")]).value = v
    wb.save(path)
    return row


def _row_values(path: Path, sheet: str, row: int) -> dict[str, object]:
    wb = openpyxl.load_workbook(path)
    ws = wb[sheet]
    out = {h: ws.cell(row, c).value for h, c in _cols(ws).items()}
    wb.close()
    return out


def _rows_of(path: Path, sheet: str, sw_id: str) -> list[int]:
    wb = openpyxl.load_workbook(path, read_only=True)
    rows = [i for i, r in enumerate(wb[sheet].iter_rows(min_row=1, values_only=True), start=1) if r and r[0] == sw_id]
    wb.close()
    return rows


def _usage(res, key: str):
    return next(u for u in res.usages if u.key == key)


@pytest.fixture(scope="module")
def sas_base(tmp_path_factory):
    """손대지 않은 SAS 파일만 적재한 기준 (파일 통계 비교용)."""
    tmp = tmp_path_factory.mktemp("sas_base")
    return _load(_copy(tmp, (SAS,)), tmp)


@pytest.mark.parametrize("edit, why", [({"사용 인원수": 7}, "29/30 열 같음, 비고가 예시 문구"), ({"비고": None}, "29/30 열 같음")],
                         ids=["users-6to7", "note-cleared"])
def test_near_example_row_swapped_for_real_row(tmp_path, sas_base, edit, why):
    """#3 A: 예시 행(4행)을 한 칸 고쳐 남기면 — 예시 유사 경고, 같은 SAS-01 의 진짜 5행을 쓰고 4행은 사유와 함께 제외.
    (고치기 전: SANTA(4행)가 SAS-01 로 적재되고 진짜 5행이 '중복 SW ID' 로 빠졌다 — 입출력도 전부 SANTA 에 붙음, 예시 언급 경고 0)"""
    d = _copy(tmp_path, (SAS,))
    _set_row(d / SAS, "SW기본정보", 4, edit)
    out = _load(d, tmp_path)
    res = out.result
    u = _usage(res, "2차유로(SAS)/SAS-01")
    assert (u.v["reported_tool_name"], u.row, u.near_example) == ("가상-1D네트워크", 5, None)
    near = [w for w in res.warnings if w.startswith(NEAR_W)]
    assert near == [f"예시와 거의 같은 행: {SAS} SW기본정보 4행 ({why}) — 응답으로 적재, 양식 예시가 남은 것인지 확인"]
    assert [w for w in res.warnings if w.startswith(SWAP_W)] == [
        f"중복 SW ID — 예시 유사 행 제외: {SAS} SAS-01 — 4행(예시와 {why}) 제외, '가상-1D네트워크'(5행) 사용"]
    assert not [w for w in res.warnings if w.startswith("중복 SW ID:")]
    ex4 = [r for r in res.excluded_rows if r["sheet"] == "SW기본정보" and r["row"] == 4]
    assert len(ex4) == 1 and "예시" in ex4[0]["reason"] and not ex4[0]["reason"].startswith("템플릿 예시 행")
    assert ex4[0]["reason"] == "SW ID 중복 — 예시와 거의 같은 행이라 제외 (5행 사용, #3)"
    owners = {x.owner.row for x in res.ios if x.sw_id == "SAS-01"}
    assert owners == {5}
    assert "santa" not in res.tools and "가상1d네트워크" in res.tools
    # 시트별 설정 점검: 기본정보는 정확한 예시 0·유사 1 → 경고 (예시를 고쳐 남긴 경우에도 난다 — 문구가 그 경우를 먼저 든다), 입출력은 예시 3행이 정확
    assert [w for w in res.warnings if w.startswith(STALE_W)] == [
        f"예시 행 판별 설정 점검: {SAS} SW기본정보 — 예시와 정확히 같은 행 0, 거의 같은 행 1 → 예시를 고쳐 남긴 것이 아니면 "
        "config/template_examples.yaml 이 이 파일의 양식과 다를 수 있음 (양식판 확인 · template-examples --form <양식> --overlay)"]
    f, f0 = res.files[0], sas_base.result.files[0]
    assert (f.usage_rows, f.io_rows, f.excluded) == (f0.usage_rows, f0.io_rows, f0.excluded)
    assert f.warnings == f0.warnings + 3
    row4 = [(i["kind"], i["value"], i["column"]) for i in res.issues if i["sheet"] == "SW기본정보" and i["row"] == 4]
    assert row4 == [("예시 행 남음", "", "")]                       # 유사 행 요청이 교체 뒤 '예시 행 남음' 하나로 바뀐다
    diag = (out.out_dir / "diag.txt").read_text(encoding="utf-8")
    assert f"  {NEAR_W}: 1" in diag and f"  {SWAP_W}: 1" in diag and "| 예시 유사" in diag
    assert next(ln for ln in diag.splitlines() if ln.startswith("  2차유로(SAS) |")).endswith(" | 1")
    assert "SANTA" not in diag and "1D네트워크" not in diag


def test_near_example_sole_row_loaded_with_warning(tmp_path):
    """진짜 SAS-01 이 없으면 고친 예시 행은 응답으로 적재 (I15 — 일부만 같으면 응답) + 경고·수정 요청 '예시와 거의 같은 행'."""
    d = _copy(tmp_path, (SAS,))
    _set_row(d / SAS, "SW기본정보", 4, {"사용 인원수": 7})
    _clear_row(d / SAS, "SW기본정보", 5)
    res = _load(d, tmp_path).result
    u = _usage(res, "2차유로(SAS)/SAS-01")
    assert (u.v["reported_tool_name"], u.row, u.near_example) == ("SANTA", 4, "29/30 열 같음, 비고가 예시 문구")
    assert len([w for w in res.warnings if w.startswith(NEAR_W)]) == 1
    assert not [w for w in res.warnings if w.startswith(("중복 SW ID", SWAP_W))]
    assert {x.owner.row for x in res.ios if x.sw_id == "SAS-01"} == {4}
    assert "santa" in res.tools
    iss = [i for i in res.issues if i["kind"] == NEAR_W]
    assert [(i["sheet"], i["row"], i["tool_id"], i["value"], i["hint"]) for i in iss] == [("SW기본정보", 4, "SAS-01", "", NEAR_HINT)]


def test_near_example_after_real_row_keeps_first(tmp_path):
    """고친 예시 행이 진짜 행 **뒤**에 있으면 '먼저 나온 행' 규칙 그대로 — 진짜 행 유지, 뒤 행은 기존 '중복 SW ID' 사유로 제외."""
    d = _copy(tmp_path, (SAS,))
    vals = _row_values(d / SAS, "SW기본정보", 4)
    vals["사용 인원수"] = 7
    row = _append_row(d / SAS, "SW기본정보", vals)
    res = _load(d, tmp_path).result
    assert _usage(res, "2차유로(SAS)/SAS-01").row == 5
    assert [w for w in res.warnings if w.startswith(NEAR_W)] == [
        f"예시와 거의 같은 행: {SAS} SW기본정보 {row}행 (29/30 열 같음, 비고가 예시 문구) — 응답으로 적재, 양식 예시가 남은 것인지 확인"]
    assert [w for w in res.warnings if w.startswith("중복 SW ID")] == [
        f"중복 SW ID: {SAS} SAS-01 — 먼저 나온 행 사용, 'SANTA' 행 제외"]
    assert [r["reason"] for r in res.excluded_rows if r["row"] == row] == ["중복 SW ID SAS-01 (먼저 나온 5행 사용)"]
    assert not [w for w in res.warnings if w.startswith(STALE_W)]          # 4행 예시가 정확히 남아 있다


def test_near_example_io_row_keeps_fill_down(tmp_path):
    """입출력 예시를 고쳐 남긴 행도 경고 후 응답으로 적재하고, 이어받기(I22)를 끊지 않는다 — 아래 행이 Tool ID 를 이어받는다."""
    d = _copy(tmp_path, (SAS,))
    _set_row(d / SAS, "SW입출력", 4, {"전달 방법": "메일·수기 전달"})
    _set_row(d / SAS, "SW입출력", 5, {"SW ID": None})
    res = _load(d, tmp_path).result
    near = [w for w in res.warnings if w.startswith(NEAR_W)]
    assert near == [f"예시와 거의 같은 행: {SAS} SW입출력 4행 (11/12 열 같음) — 응답으로 적재, 양식 예시가 남은 것인지 확인",
                    f"예시와 거의 같은 행: {SAS} SW입출력 5행 (11/12 열 같음) — 응답으로 적재, 양식 예시가 남은 것인지 확인"]
    assert f"Tool ID 이어받음: {SAS} SW입출력 '경계조건(압력·온도)' → 'SAS-01' (바로 위 행)" in res.warnings
    x4, x5 = (next(x for x in res.ios if x.row == r) for r in (4, 5))
    assert x4.near_example == x5.near_example == "11/12 열 같음" and x4.owner.row == x5.owner.row == 5
    assert not [w for w in res.warnings if w.startswith(STALE_W)]          # 입출력 6행 예시가 정확히 남아 있다


def test_dup_warnings_mask_person_like(tmp_path):
    """C5: 중복 SW ID 경고 두 종류 모두 Tool ID·툴명이 인명 유사면 가린다 (값은 '가나다 책임' 같은 가상 자리표시)."""
    d = _copy(tmp_path, (SAS, STR))
    _set_row(d / SAS, "SW기본정보", 4, {"사용 인원수": 7})
    _set_row(d / SAS, "SW기본정보", 5, {"SW명(정식)": "가나다 책임 매크로"})
    second = _rows_of(d / STR, "SW기본정보", "STR-03")[1]
    _set_row(d / STR, "SW기본정보", second, {"SW명(정식)": "가나다 책임 툴"})
    res = _load(d, tmp_path).result
    dup = [w for w in res.warnings if w.startswith("중복 SW ID")]
    assert dup == [f"중복 SW ID — 예시 유사 행 제외: {SAS} SAS-01 — 4행(예시와 29/30 열 같음, 비고가 예시 문구) 제외, '{PERSON_MASK}'(5행) 사용",
                   f"중복 SW ID: {STR} STR-03 — 먼저 나온 행 사용, '{PERSON_MASK}' 행 제외"]
    assert not any("가나다" in w for w in dup)


def test_na_heavy_real_rows_are_not_near(tmp_path):
    """정보 열 기준 (2026-10-12): NA·모름 투성이 실제 응답은 v1.1 TA-01 예시와 빈 값 칸이 같아도 예시 유사가 아니다."""
    d = _copy(tmp_path)
    _append_row(d / STR, "SW입출력", {"SW ID": "STR-01", "방향": "입력(소비)", "데이터/산출물 명칭": "가상 하중조건",
                                       "분류": "해석-입력데이터", "파일 형식/확장자": "NA", "포맷 표준성": "모름", "데이터 성격": "수치·표",
                                       "전달 방법": "메일·수기 전달", "연계 SW명": "NA", "보안등급": "미정"})
    res = _load(d, tmp_path).result
    assert not [w for w in res.warnings if w.startswith((NEAR_W, STALE_W))]       # 정보 열 5/7 = 0.71 (빈 값 칸까지 세면 8/10 = 0.80 — 걸렸다)
    ld = Loader()
    ta = dict(next(e for e in ld.examples[USAGE_SHEET] if e["source_key"] == "TA-01"))
    ta.update(source_key="TA-07", reported_tool_name="가상-터빈 리그 계산표", purpose_detail="가상 용도", task_summary="가상 업무",
              note="가상 비고")
    present = {c.slot for c in ld.spec.columns[USAGE_SHEET]}
    assert ld._example_similarity(USAGE_SHEET, ta, present) == (10, 15)          # 예시의 비지 않은 열 전부로 세면 24/29 = 0.83 — 걸렸다
    assert ld._near_example(USAGE_SHEET, ta, present) is None


def _near_cases() -> list[tuple[str, str, dict, set | None]]:
    """(이름, 시트, 행, present | None=전체 열) — 적재기·oracle 대조용."""
    ld = Loader()
    out = []
    for sheet in (USAGE_SHEET, IO_SHEET):
        for i, ex in enumerate(ld.examples[sheet]):
            row = dict(ex)
            k = "reported_tool_name" if sheet == USAGE_SHEET else "data_name"     # 모든 예시의 정보 열
            row[k] = "가상-다른값"
            out.append((f"{sheet}-{i}-one-cell", sheet, row, None))
            out.append((f"{sheet}-{i}-exact", sheet, dict(ex), None))
    sas = dict(ld.examples[USAGE_SHEET][0])
    out.append(("float-int-cell", USAGE_SHEET, {**sas, "user_count": 6.0, "license_count": 10.0, "version": "v4.3"}, None))
    out.append(("note-only", USAGE_SHEET, {"source_key": "X-1", "reported_tool_name": "가상", "note": sas["note"]}, None))
    out.append(("note-NFC-space", USAGE_SHEET, {"source_key": "X-1", "note": "  " + sas["note"] + " "}, None))
    out.append(("note-absent-column", USAGE_SHEET, {"source_key": "X-1", "note": sas["note"]},
                {c.slot for c in ld.spec.columns[USAGE_SHEET]} - {"note"}))
    ta_io = dict(next(e for e in ld.examples[IO_SHEET] if e["owner_source_key"] == "TA-01"))
    out.append(("na-heavy-io", IO_SHEET, {**ta_io, "owner_source_key": "STR-01", "data_name": "가상 하중조건"}, None))
    out.append(("few-columns-present", USAGE_SHEET, dict(sas), {"source_key", "reported_tool_name", "version", "note"}))
    out.append(("half-present", USAGE_SHEET, {**sas, "version": "v9"},
                {"source_key", "reported_tool_name", "version", "reported_vendor", "reported_kind", "purpose_class", "phase"}))
    return out


@pytest.mark.parametrize("name, sheet, row, present", _near_cases(), ids=[c[0] for c in _near_cases()])
def test_example_similarity_matches_oracle(name, sheet, row, present):
    """I15 개정 판별식 — 적재기 Loader._example_similarity·_near_example ↔ oracle.example_similarity·example_near (독립 구현)."""
    ld = Loader()
    present = present if present is not None else {c.slot for c in ld.spec.columns[sheet]}
    examples = ld.examples[sheet]
    got = ld._example_similarity(sheet, row, present)
    assert got == oracle.example_similarity(row, examples, present)
    assert (ld._near_example(sheet, row, present) is not None) == oracle.example_near(row, examples, present, sheet == USAGE_SHEET)
    if name.endswith("-one-cell"):
        eq, n = got
        assert n and eq == n - 1 and eq / n >= 0.8, name                    # 예시 한 칸 수정은 모두 잡힌다
    if name == "few-columns-present":
        assert got == (0, 0)                                                # 정보 열 4 < example_near_min_cols 5 — 비고 대조만 남는다
        assert ld._near_example(sheet, row, present) == "비고가 예시 문구"
    if name == "note-only":
        assert ld._near_example(sheet, row, present).endswith("비고가 예시 문구")


def test_example_near_ratio_from_rules_overlay(tmp_path):
    """rules.yaml loader.example_near_ratio 는 사내 오버레이로 조정 — 0.6 이면 골든 SAS 5행(19/30 = 0.633)이 걸린다. 틀린 값은 ConfigError."""
    d = _copy(tmp_path, (SAS,))
    over = tmp_path / "real_config"
    over.mkdir()
    (over / "rules.yaml").write_text(yaml.safe_dump({"loader": {"example_near_ratio": 0.6}}), encoding="utf-8")
    ld = Loader(overlay_dir=over)
    assert (ld.near_ratio, ld.near_min_cols) == (0.6, 5) and "rules.yaml" in ld.overlay_files
    res = ld.load(ld.discover(d))
    assert [w for w in res.warnings if w.startswith(NEAR_W)] == [
        f"예시와 거의 같은 행: {SAS} SW기본정보 5행 (19/30 열 같음) — 응답으로 적재, 양식 예시가 남은 것인지 확인"]
    assert not [w for w in res.warnings if w.startswith(STALE_W)]          # 4행이 정확한 예시
    assert Loader().near_ratio == 0.8
    for bad in ({"example_near_ratio": 1.5}, {"example_near_ratio": "abc"}, {"example_near_ratio": 0}, {"example_near_ratio": True},
                {"example_near_min_cols": 0}, {"example_near_min_cols": 2.5}):
        (over / "rules.yaml").write_text(yaml.safe_dump({"loader": bad}), encoding="utf-8")
        with pytest.raises(ConfigError, match="example_near_"):
            Loader(overlay_dir=over)


def test_stale_template_examples_warned_per_sheet(tmp_path):
    """#3c: 설정의 기본정보 예시가 양식과 다르면(버전 v4.2 → v4.3, template-examples 재실행 안 함) 적재 8개 파일 모두 기본정보 시트에
    '예시 행 판별 설정 점검' 1건 — 입출력 예시는 정확히 맞아 파일 단위 조건(docs/09 원안)으로는 0/8 이었다. SAS 파일은 진짜 SAS-01 로 교체,
    다른 7개 파일의 '<파트>/SAS-01' 은 예시 유사 경고와 함께 응답으로 적재되고 키는 파트마다 따로 (Leo #3 A 의 동작 고정)."""
    cfg = tmp_path / "config"
    shutil.copytree(CONFIG_DIR, cfg)
    ex = yaml.safe_load((cfg / "template_examples.yaml").read_text(encoding="utf-8"))
    for r in ex[USAGE_SHEET]:
        if r.get("version") == "v4.2":
            r["version"] = "v4.3"
    (cfg / "template_examples.yaml").write_text(yaml.safe_dump(ex, allow_unicode=True, sort_keys=False), encoding="utf-8")
    res = run_load(registry_dir=tmp_path / "registry", out_root=tmp_path / "out", shacl=False, config_dir=cfg).result
    loaded = [f.name for f in res.loaded_files]
    assert len(loaded) == 8
    stale = [w for w in res.warnings if w.startswith(STALE_W)]
    assert sorted(w.split(" — ")[0] for w in stale) == sorted(f"{STALE_W}: {f} SW기본정보" for f in loaded)
    assert not any(" SW입출력 — " in w for w in stale)
    assert _usage(res, "2차유로(SAS)/SAS-01").v["reported_tool_name"] == "가상-1D네트워크"
    sas01 = [u for u in res.usages if u.sw_id == "SAS-01"]
    assert len({u.key for u in sas01}) == len(sas01) == 8
    assert all(u.near_example for u in sas01 if u.field != "2차유로(SAS)")
    perf = next(w for w in stale if "성능" in w)
    assert "거의 같은 행 2" in perf                                          # 성능 파일은 예시 복사본(9행)까지


def test_template_examples_overlay_union(tmp_path):
    """#3d: 사내 오버레이 template_examples.yaml 은 저장소 예시와 시트별 합집합 — 그 행이 정확한 예시로 제외되고 저장소 예시도 계속 제외."""
    d = _copy(tmp_path)
    row = _append_row(d / STR, "SW기본정보", {"SW ID": "STR-90", "SW명(정식)": "가상-사내예시툴", "버전": "v1", "비고": "(사내 양식 예시)"})
    over = tmp_path / "real_config"
    over.mkdir()
    extra = {"source_key": "STR-90", "reported_tool_name": "가상-사내예시툴", "version": "v1", "note": "(사내 양식 예시)"}
    (over / "template_examples.yaml").write_text(yaml.safe_dump({USAGE_SHEET: [extra]}, allow_unicode=True), encoding="utf-8")
    out = run_load(input_dir=d, registry_dir=tmp_path / "registry", out_root=tmp_path / "out", shacl=False, overlay_dir=over)
    ex = {(r["sheet"], r["row"]): r["reason"] for r in out.result.excluded_rows}
    assert ex[(USAGE_SHEET, row)] == ex[(USAGE_SHEET, 4)] == "템플릿 예시 행 (내용 일치, I15)"
    assert "STR-90" not in {u.sw_id for u in out.result.usages}
    assert "template_examples.yaml" in out.log["config_overlay"]["files"]
    plain = run_load(input_dir=d, registry_dir=tmp_path / "reg2", out_root=tmp_path / "out2", shacl=False)   # 오버레이 없으면 응답
    assert "STR-90" in {u.sw_id for u in plain.result.usages}
    base = yaml.safe_load((CONFIG_DIR / "template_examples.yaml").read_text(encoding="utf-8"))
    merged = merge_config("template_examples.yaml", base, {USAGE_SHEET: [extra, base[USAGE_SHEET][0]], IO_SHEET: []})
    assert merged[USAGE_SHEET] == base[USAGE_SHEET] + [extra] and merged[IO_SHEET] == base[IO_SHEET]
    with pytest.raises(ConfigError, match="예시 행은 매핑"):
        merge_config("template_examples.yaml", base, {USAGE_SHEET: ["문자열"]})
    with pytest.raises(ConfigError, match="목록"):
        merge_config("template_examples.yaml", base, {USAGE_SHEET: {"a": 1}})


def test_template_examples_cli_overlay_writes_real_config(tmp_path, monkeypatch):
    """#3d: template-examples --form <사내 양식> --overlay 는 저장소 config 를 건드리지 않고 data/real/config 에 **새 예시만 더한다** (다시 돌려도 0)."""
    import engenius_onto.config as cfgmod
    from engenius_onto.cli import main

    real = tmp_path / "real_config"
    monkeypatch.setattr(cfgmod, "REAL_CONFIG_DIR", real)
    form = tmp_path / "사내양식_v1.2.xlsx"
    shutil.copy(REPO / "reference" / "Tool조사양식_EnGenius_v1.1.xlsx", form)
    wb = openpyxl.load_workbook(form)
    ws = wb["Tool 기본정보"]
    assert ws.cell(5, 2).value == "SAS-01"
    ws.cell(5, _cols(ws)["버전"]).value = "v9.9"                           # 사내 양식판의 예시가 조금 다르다
    wb.save(form)
    repo_bytes = (CONFIG_DIR / "template_examples.yaml").read_bytes()
    assert main(["template-examples", "--overlay"]) == 1                    # --form 없이는 거부
    assert main(["template-examples", "--form", str(form), "--overlay"]) == 0
    assert (CONFIG_DIR / "template_examples.yaml").read_bytes() == repo_bytes
    data = yaml.safe_load((real / "template_examples.yaml").read_text(encoding="utf-8"))
    assert [r["version"] for r in data[USAGE_SHEET]] == ["v9.9"] and data[IO_SHEET] == []
    assert "사내 전용" in (real / "template_examples.yaml").read_text(encoding="utf-8")
    assert main(["template-examples", "--form", str(form), "--overlay"]) == 0
    assert yaml.safe_load((real / "template_examples.yaml").read_text(encoding="utf-8")) == data
    ld = Loader(overlay_dir=real)
    assert "template_examples.yaml" in ld.overlay_files and len(ld.examples[USAGE_SHEET]) == len(Loader().examples[USAGE_SHEET]) + 1
