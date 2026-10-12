"""M3.1 2차 잔여 (docs/09 0장 '남음', Leo 결정 2026-10-12) — 묶음별 절.

- A. 확장자 정규화 (docs/09 #10) · 적재기 ↔ oracle 확장자 parity (docs/09 6장) · 인명 가림 헬퍼(Normalizer.looks_person·Loader._q)
합성 파일 사본만 쓴다 (공개 상용 툴 이름·가상 이름). 인명 시험 값은 가상 자리표시('가나다 책임')만.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import openpyxl
import pytest
import yaml

from engenius_onto import synth
from engenius_onto.loader import PERSON_MASK, Loader
from engenius_onto.normalize import Normalizer
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
