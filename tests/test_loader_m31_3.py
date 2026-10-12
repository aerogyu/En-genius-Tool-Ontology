"""M3.1 2차 잔여 (docs/09 0장 '남음', Leo 결정 2026-10-12) — 묶음별 절.

- A. 확장자 정규화 (docs/09 #10) · 적재기 ↔ oracle 확장자 parity (docs/09 6장) · 인명 가림 헬퍼(Normalizer.looks_person·Loader._q)
- B. 파일 층 (docs/09 #1 잔여·#8 C4): 파일 간 같은 (파트, Tool ID) 구분 키(I36) · '(n)' 사본 파일명(I31·I33) · 같은 내용 파일 한 번만 ·
  규칙 밖 해시 이름 유일화 · 규칙 밖 고아 표시
- C. 예시와 거의 같은 행 (docs/09 #3, I15 개정): 정보 열 기준 유사 판별·경고 · 중복 Tool ID 면 예시 유사 행을 빼고 진짜 행 ·
  설정 낡음 점검(시트별) · rules 오버레이 문턱 · template_examples 오버레이·template-examples --overlay · 적재기 ↔ oracle 판별식
- D. 값·엑셀 층 (묶음 values): header_map 오버레이(I30) · 엑셀 층 신호(I37 — 수식 오류 셀·캐시 없는 수식·숨긴 행·양식 밖 시트·툴사용 0건) ·
  만료 시기 텍스트·'영구'(docs/09 #21 3단, I16·I27) · 드롭다운 빈 값 토큰(I28 기록) · 자동화 판정 빈 값 토큰(Normalizer.automatable ↔ oracle·지도·MCP)
- E. 검토표·별칭·레지스트리 (묶음 review): 인명 유사 연계 조각 회귀(#20 (2)) · 검토표 CSV 수식 방지·apply-review 칸 검사(#25d) ·
  연계 Tool명 미해석 행·partner_missing(#17, I10·I35) · 별칭 미적용 경고·제조사 안 뗀 이름 별칭(#2 (3)·(4)) · 레지스트리 엑셀 손상(#15 (4))
- F. 식별자·실행 안전 (묶음 ids): 정식 이름 변경 회귀 · 약칭 개명 renamed_from(#25b, I31 — 레지스트리 rekey·옛 약칭 파일명·재발송·묶음 앞부분·보류·설정 오류) ·
  '파트 신규·폐기 동시' 휴리스틱 · 동시 적재 잠금 · 같은 초 두 실행 (docs/09 7장)
- 2차 잔여 검토 수리 (2026-10-12) — 각 절에: A 값 인용 경고 전부 가림·'.확장자(.확장자)' · B 대체된 옛 회신의 사본 · D 빈 문자열 캐시 수식·먼 서식 칸·옛 rules.yaml ·
  E 승인 인명 패턴 보충·검토표 표기 칸 가림·열 모자란 레지스트리 행·잠금 없는 레지스트리 복사 · F 같은 날짜 옛·새 약칭 파일·범용 이름 툴 키 개명
- 재검토 수리 (2026-10-12) — A 제외 행(Tool ID 없음·수식 오류·빈 행 뒤)·정수 열 원문 인명 검사(↔ oracle)·툴 키 인용 경고·속성 충돌 값·SHACL 메시지 가림 ·
  D 선택지 시트 먼 서식 칸 · E 연계 행 힌트 키 가림·레지스트리 빈 상태 · F 옛 약칭 '(n)' 사본 vs 새 약칭 파일·사본 번호는 같은 이름끼리만
- 재검토 수리 2 (2026-10-12) — A 스키마 검증 메시지 가림·SHACL 메시지의 이스케이프된 줄바꿈·탭·툴 키 인용은 보고 이름까지(_qk) ·
  E 레지스트리 빈 줄 버림·키 있는 줄의 빈 ID 는 적재 중지(rc 2)·상태 칸 공백·오타
합성 파일 사본만 쓴다 (공개 상용 툴 이름·가상 이름). 인명 시험 값은 가상 자리표시('가나다 책임')만.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

import openpyxl
import pytest
import yaml
from rdflib import RDF, Graph

from engenius_onto import synth
from engenius_onto.config import CONFIG_DIR, ConfigError, merge_config, read_csv_rows
from engenius_onto.loader import IO_SHEET, PERSON_MASK, PERSON_ROW_HINT, PERSON_TAIL_HINT, USAGE_SHEET, FileReport, Loader, UsageRec
from engenius_onto.normalize import Normalizer
from engenius_onto.rdf_writer import SchemaTerms
from engenius_onto.registry import copy_registry
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
    # 괄호 앞 단어가 '.확장자' 자체면 형식 이름이 아니다 — 둘 다 확장자 (2026-10-12 검토 수리: 전에는 앞 확장자가 경고 없이 사라졌다)
    (".cas(.dat)", ["cas", "dat"], False, []),
    (".bdf (.dat)", ["bdf", "dat"], False, []),
    ("*.stp(.igs)", ["igs", "stp"], False, []),
    (".x_t(.x_b)", ["x_b", "x_t"], False, []),
    ("stp, .x_t(.x_b)", ["stp", "x_b", "x_t"], False, []),
    ("x_t(.x_b)", ["x_b"], False, []),                  # 한계 고정: 점 없는 단어는 형식 이름으로 본다 ('csv (.dat)' 와 같다)
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
    copy_registry(REGISTRY_DIR, reg)
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
    # #20 1-A 승인 목록에서 빠졌던 두 꼴 (2026-10-12 검토 수리) — 직급+에게·께, 이름(직급)
    for s in ("가나다 선임에게 메일", "가나다 책임께", "가나다(책임)", "가나다 (수석)"):
        assert norm.looks_person(s), s
    assert not norm.looks_person("가상수명평가툴") and not norm.looks_person("구조 해석 결과")


PERSON_TOKENS = ("가나다", "나다라", "다라마", "라마바")       # 가상 인명 자리표시 (시험 전용)


def test_value_quoting_warnings_redact_person_like(tmp_path, capsys):
    """docs/09 #20 수리 계획 2)·C5 — 값을 인용하는 모든 경고가 _q 를 거친다: 행 경고의 위치 문구(Tool ID·데이터명)·선택지 밖 값·담당 부서·
    정수 변환·SW ID 없는 행·고아·이어받기·방향·범용 이름·확장자·완전 중복 키·헤더 문구. 인명 유사 값은 경고·콘솔·수정 요청표에 원문이 없고
    가림 문구로 나온다 (2026-10-12 검토 수리: 전에는 '인명 유사 패턴' 경고가 자기가 잡은 데이터명을 그대로 실었다). 값은 그래프에 보존 (D6)."""
    d = _copy(tmp_path)
    p = d / STR
    _set_row(p, USAGE_SHEET, 6, {"담당 부서": "구조 가나다 책임"})                         # STR-02 — 선택지 밖·담당 부서·인명 유사
    _set_row(p, USAGE_SHEET, 9, {"사용 인원수": "가나다 책임 외 3"})                        # STR-04 — 정수 변환 실패
    _set_row(p, USAGE_SHEET, 11, {"SW ID": "작성: 가나다 책임", "만료 시기": "2027.03"})    # 표 아래 꼬리말이 Tool ID 칸에 (C8)
    _set_row(p, USAGE_SHEET, 12, {"SW명(정식)": "문의: 라마바 책임(내선 0000)"})            # Tool ID 없는 내용 행
    _set_row(p, IO_SHEET, 8, {"데이터/산출물 명칭": "가나다 책임 메모", "데이터 성격": "아무값"})
    _set_row(p, IO_SHEET, 9, {"방향": "나다라 선임에게"})
    _set_row(p, IO_SHEET, 21, {"SW ID": "STR-99", "방향": "입력(소비)", "데이터/산출물 명칭": "다라마 책임 전달본"})
    foot = {"SW ID": "작성: 가나다 책임", "방향": "출력(생산)", "데이터/산출물 명칭": "꼬리말 자료", "분류": "해석-결과",
            "파일 형식/확장자": "model.stp", "데이터 성격": "정형(표·수치)", "전달 방법": "공유폴더"}
    _set_row(p, IO_SHEET, 23, foot)
    _set_row(p, IO_SHEET, 24, {"방향": "출력(생산)", "데이터/산출물 명칭": "나다라 책임 사본"})   # 바로 위 행 ID 이어받기
    _set_row(p, IO_SHEET, 25, foot)                                                         # 23행과 완전 중복
    wb = openpyxl.load_workbook(p)
    ws = wb[USAGE_SHEET]
    ws.cell(2, ws.max_column + 1).value = "나다라 책임 메모"                                 # 헤더 칸에 적은 이름 (N3)
    wb.save(p)
    rc = cli.main(["load", "--input", str(d), "--registry", str(tmp_path / "registry"), "--out", str(tmp_path / "out"), "--no-shacl"])
    console = capsys.readouterr().out
    assert rc == 0
    run = next((tmp_path / "out").iterdir())
    log = json.loads((run / "load_log.json").read_text(encoding="utf-8"))
    texts = {"console": console, "warnings": "\n".join(log["warnings"]), "issues": json.dumps(log["issues"], ensure_ascii=False),
             "review": (run / "tool_review.csv").read_text(encoding="utf-8-sig"), "diag": (run / "diag.txt").read_text(encoding="utf-8")}
    for where, text in texts.items():
        assert not [t for t in PERSON_TOKENS if t in text], where
    masked = {w.split(":", 1)[0] for w in log["warnings"] if PERSON_MASK in w}
    assert {"인명 유사 패턴", "선택지 밖 값", "파일 분야 ≠ 담당 부서", "사용 인원수 정수 변환 실패", "필수값 누락", "만료 시기 표기 변환",
            "툴 이름 범용/비어 있음", "SW ID 없는 내용 행", "매핑 안 된 헤더", "방향 값 인식 못 함", "고아 입출력", "확장자 다중 점 확인",
            "Tool ID 이어받음", "완전 중복 입출력 행"} <= masked
    assert f"인명 유사 패턴: {STR} {IO_SHEET} STR-01 '{PERSON_MASK}' '데이터/산출물 명칭 *'" in log["warnings"]
    assert f"[경고] 인명 유사 패턴: {STR} {IO_SHEET} STR-01 '{PERSON_MASK}' '데이터/산출물 명칭 *'" in console
    assert any(i["tool_id"] == PERSON_MASK for i in log["issues"])                           # 수정 요청표 Tool ID 칸도 가림 (행 번호로 찾는다)
    ttl = (run / "survey.ttl").read_text(encoding="utf-8")
    assert "가나다 책임 메모" in ttl and "구조 가나다 책임" in ttl                                # 값은 보존 (D6)


def _no_tokens(*texts: str) -> bool:
    return not [t for t in PERSON_TOKENS if any(t in x for x in texts)]


def test_excluded_rows_person_scan_replaces_tool_id_request(tmp_path):
    """docs/09 #20 수리 계획 2 (I22·I29, 2026-10-12 재검토 수리) — 제외하는 내용 행(Tool ID 없음·Tool ID 수식 오류·빈 행 10개 뒤)도 인명 검사:
    걸린 칸마다 경고(행 번호로 — 값·ID 없음), 수정 요청은 그 행의 원래 요청('Tool ID 없음' 등) 대신 '인명 유사' 한 줄. 전에는 표 아래 연락처 꼬리말에
    'Tool ID 를 적어 주세요' 만 나가, 안내대로 ID 를 붙이면 다음 적재에서 인명이 그래프·레지스트리 라벨(영구)에 들어갔다. 사람 이름 없는 행은 그대로."""
    d = _copy(tmp_path)
    p = d / STR
    _set_row(p, USAGE_SHEET, 12, {"SW명(정식)": "문의: 라마바 책임(내선 0000)"})               # 표 아래 한 칸 띄운 꼬리말 (Tool ID 없음)
    _set_row(p, USAGE_SHEET, 13, {"SW명(정식)": "가상-번호없는툴"})                             # 대조 — 사람 이름 없는 Tool ID 없음 행
    _set_row(p, USAGE_SHEET, 30, {"비고": "작성: 다라마 책임"})                                  # 빈 행 16개 뒤 (시트 끝 뒤, #6)
    _set_row(p, IO_SHEET, 22, {"데이터/산출물 명칭": "작성: 가나다 책임"})                        # 21행이 빈 행 — 이어받지 않는다
    _set_row(p, IO_SHEET, 24, {"SW ID": "#N/A", "데이터/산출물 명칭": "나다라 선임에게 전달"})     # Tool ID 수식 오류 (I37)
    res = _load(d, tmp_path).result
    rows = {(USAGE_SHEET, 12), (USAGE_SHEET, 13), (USAGE_SHEET, 30), (IO_SHEET, 22), (IO_SHEET, 24)}
    got = sorted((i["sheet"], i["row"], i["kind"], i["column"]) for i in res.issues if (i["sheet"], i["row"]) in rows)
    assert got == sorted([(USAGE_SHEET, 12, "인명 유사", "SW명(정식)"), (USAGE_SHEET, 13, "Tool ID 없음", "Tool ID"),
                          (USAGE_SHEET, 30, "인명 유사", "비고"), (IO_SHEET, 22, "인명 유사", "데이터/산출물 명칭"),
                          (IO_SHEET, 24, "인명 유사", "데이터/산출물 명칭")])
    person = {(i["sheet"], i["row"]): (i["tool_id"], i["value"], i["hint"]) for i in res.issues
              if (i["sheet"], i["row"]) in rows and i["kind"] == "인명 유사"}
    assert person == {(USAGE_SHEET, 12): ("", "", PERSON_ROW_HINT), (IO_SHEET, 22): ("", "", PERSON_ROW_HINT),
                      (IO_SHEET, 24): ("", "", PERSON_ROW_HINT), (USAGE_SHEET, 30): ("", "", PERSON_TAIL_HINT)}
    assert "Tool ID 를 붙이지 마세요" in PERSON_ROW_HINT and "표로 옮기지 마세요" in PERSON_TAIL_HINT
    assert sorted(w for w in res.warnings if w.startswith("인명 유사 패턴:") and "행 (" in w) == sorted([
        f"인명 유사 패턴: {STR} {USAGE_SHEET} 12행 (Tool ID 없음) 'SW명(정식) *'",
        f"인명 유사 패턴: {STR} {USAGE_SHEET} 30행 (빈 행 뒤) '비고'",
        f"인명 유사 패턴: {STR} {IO_SHEET} 22행 (Tool ID 없음) '데이터/산출물 명칭 *'",
        f"인명 유사 패턴: {STR} {IO_SHEET} 24행 (Tool ID 수식 오류) '데이터/산출물 명칭 *'"])
    ex = {(r["sheet"], r["row"]): r["reason"] for r in res.excluded_rows}
    assert ex[(USAGE_SHEET, 12)] == ex[(IO_SHEET, 22)] == "SW ID 없음 (I22)" and ex[(IO_SHEET, 24)] == "Tool ID 수식 오류 (I37)"
    assert ex[(USAGE_SHEET, 30)].startswith("빈 행 뒤 내용 행")
    assert not [u for u in res.usages if u.row in (12, 13, 30)] and not [x for x in res.ios if x.row in (22, 24)]
    assert _no_tokens("\n".join(res.warnings), json.dumps(res.issues, ensure_ascii=False))


def test_int_column_and_excluded_row_person_scan_matches_oracle(tmp_path):
    """I29 '적재하는 모든 문자열 열' — 정수 열(사용 인원수·보유 수량)의 변환 못 한 원문도 인명 검사 (원문은 <슬롯>_raw 로 그래프에 적재된다;
    전에는 '정수 변환 실패' 경고만 내고 인명 경고·수정 요청이 없어 oracle 과 어긋났다 — 2026-10-12 재검토 수리). 건너뛰는 Tool ID 없는 행도 (I22).
    명세 → 합성 엑셀 → 적재기 경고와 oracle 경고가 같다."""
    spec = _spec([{"sw_id": "A-1", "name": "가상-툴A", "vendor": "v", "users": "가나다 책임 외 3"},
                  {"sw_id": "A-2", "name": "가상-툴B", "vendor": "v", "qty": "라마바 선임 관리 5"},
                  {"sw_id": None, "name": "문의: 라마바 책임(내선 0000)", "vendor": "v"}],
                 [{"sw_id": "A-1", "dir": "out", "name": "d", "cat": "해석-결과", "ext": "dat"},
                  {"blank": True},
                  {"sw_id": None, "dir": "in", "name": "작성: 가나다 책임", "cat": "해석-결과", "ext": "dat"}])
    r = oracle.compute(spec, REPO)
    d = tmp_path / "s"
    d.mkdir()
    f = "SW조사_성능_20260101.xlsx"
    (d / f).write_bytes(synth.build_workbook_bytes(spec, spec["files"][0]))
    ld = Loader()
    res = ld.load(ld.discover(d))
    person = lambda ws: sorted(w for w in ws if w.startswith("인명 유사 패턴"))  # noqa: E731
    assert person(res.warnings) == person(r["warnings"]) == sorted([
        f"인명 유사 패턴: {f} SW기본정보 A-1 '사용 인원수'", f"인명 유사 패턴: {f} SW기본정보 A-2 '보유 수량'",
        f"인명 유사 패턴: {f} SW기본정보 7행 (Tool ID 없음) 'SW명(정식) *'",
        f"인명 유사 패턴: {f} SW입출력 9행 (Tool ID 없음) '데이터/산출물 명칭 *'"])
    assert sorted((i["sheet"], i["row"], i["column"]) for i in res.issues if i["kind"] == "인명 유사") == [
        (USAGE_SHEET, 5, "사용 인원수"), (USAGE_SHEET, 6, "보유 수량"), (USAGE_SHEET, 7, "SW명(정식)"), (IO_SHEET, 9, "데이터/산출물 명칭")]
    a1 = next(u for u in res.usages if u.sw_id == "A-1")
    assert a1.v["user_count"] is None and a1.raw == {"user_count": "가나다 책임 외 3"}           # 원문은 보존 (D6) — 경고에만 안 옮긴다
    assert _no_tokens("\n".join(res.warnings), json.dumps(res.issues, ensure_ascii=False))
    assert sum(1 for w in r["warnings"] if w.startswith("SW ID 없는 내용 행")) == 2             # oracle 도 기본정보 Tool ID 없는 행을 건너뛴다


def test_tool_key_warnings_mask_person_like(tmp_path):
    """C5 '값을 인용하는 경고 전부' — 툴 키를 인용하는 경고 넷(제조사 접두 흡수 보류·제조사 접두 흡수와 별개 판정 충돌·툴 별칭 순환·툴 별칭과 별개 판정
    충돌)도 _q (2026-10-12 재검토 수리: tool_key 는 괄호·버전·공백만 지워 '가나다 책임 v2' → '가나다책임' 이 인명 패턴에 그대로 걸린다)."""
    d = _copy(tmp_path / "held")
    _set_names(d / STR, {"STR-04": "Altair 가나다 책임", "STR-05": "가나다 책임 v2"})
    ld = Loader()
    res = ld.load(ld.discover(d), known_tool_keys={"altair가나다책임", "가나다책임"})       # 둘 다 기존 활성 툴 — 흡수 보류
    assert {"altair가나다책임", "가나다책임"} <= set(res.tools)
    held = _w(res, "제조사 접두 흡수 보류")
    assert held == [f"제조사 접두 흡수 보류: 기존 툴 둘 이상 ({PERSON_MASK}, {PERSON_MASK}) — 검토표에서 판정"]
    d2 = _copy(tmp_path / "clash")
    _set_row(d2 / STR, USAGE_SHEET, 7, {"SW명(정식)": "가나다 책임"})                         # STR-03 첫 행
    _set_names(d2 / STR, {"STR-04": "Altair 가나다 책임", "STR-05": "ANSYS 가나다 책임"})
    (tmp_path / "o1").mkdir()
    (tmp_path / "o2").mkdir()
    over = _overlay(tmp_path / "o1", tool_aliases={"distinct": [["altair가나다책임", "ansys가나다책임"]]})
    ld2 = Loader(overlay_dir=over)
    clash = _w(ld2.load(ld2.discover(d2)), "제조사 접두 흡수와 별개 판정이 충돌")
    assert clash == [f"제조사 접두 흡수와 별개 판정이 충돌: {PERSON_MASK} / {PERSON_MASK} — 흡수하지 않음"]
    over2 = _overlay(tmp_path / "o2", tool_aliases={"merge_keys": {"가나다책임": "라마바책임", "라마바책임": "가나다책임", "나다라책임": "다라마책임"},
                                                    "distinct": [["나다라책임", "다라마책임"]]})
    w: list[str] = []
    Loader(overlay_dir=over2)._alias_map(w)
    cyc = [x for x in w if x.startswith("툴 별칭 순환")]
    assert cyc and set(cyc) == {f"툴 별칭 순환: {PERSON_MASK} ↔ {PERSON_MASK} — 가장 작은 키 '{PERSON_MASK}' 를 대표로 (config/tool_aliases.yaml 확인)"}
    assert [x for x in w if x.startswith("툴 별칭과 별개 판정이 충돌")] == [
        f"툴 별칭과 별개 판정이 충돌: {PERSON_MASK} / {PERSON_MASK} — 통합이 적용됨 (config/tool_aliases.yaml distinct 확인)"]
    assert _no_tokens("\n".join(held + clash + w))


def test_attribute_conflicts_mask_person_like(tmp_path):
    """load_log tool_attribute_conflicts — 같은 툴의 제조사·구분 값이 갈릴 때 값 목록이 원문이었다 (vendor_key 가 괄호를 지워 'Microsoft(… 책임 구매)' 도
    같은 툴로 묶인다). 인명 유사 값은 PERSON_MASK 한 칸에 건수를 더하고, 다수결은 원문으로 정한 뒤 가린다 (2026-10-12 재검토 수리). 그래프에는 보존 (D6)."""
    survey = tmp_path / "survey"
    shutil.copytree(SURVEY_DIR, survey)
    _set_row(survey / STR, USAGE_SHEET, 10, {"제조사 / 개발주체": "Microsoft(나다라 책임 구매)", "구분": "상용(다라마 책임 관리)"})   # STR-05 Excel
    reg = copy_registry(REGISTRY_DIR, tmp_path / "registry")
    out = run_load(input_dir=survey, registry_dir=reg, out_root=tmp_path / "out", shacl=False, save_registry=False)
    key = next(u.tool_key for u in out.result.usages if u.sw_id == "STR-05")
    conf = out.log["tool_attribute_conflicts"][key]
    assert conf["vendor"]["majority"] == "Microsoft" and conf["vendor"]["values"][PERSON_MASK] == 1
    assert conf["kind"]["values"][PERSON_MASK] == 1 and sum(conf["vendor"]["values"].values()) == len(out.result.tools[key].usages)
    log_text = (out.out_dir / "load_log.json").read_text(encoding="utf-8")
    assert _no_tokens(log_text) and "Microsoft(나다라 책임 구매)" in out.turtle


def test_shacl_message_mask_unit():
    """docs/09 N5 — SHACL 결과 메시지의 인용 리터럴 가운데 인명 유사한 것만 가린다 (선택지 값 목록·형식 위반 값은 그대로). 인용 밖에 남으면 통째로."""
    from engenius_onto.survey_load import mask_shacl_message

    looks = Normalizer.from_config().looks_person
    assert not looks(PERSON_MASK)
    m = 'InConstraint["입력(소비)", "출력(생산)"] : RDF term "나다라 선임에게" not in expected values'
    assert mask_shacl_message(m, looks) == f'InConstraint["입력(소비)", "출력(생산)"] : RDF term "{PERSON_MASK}" not in expected values'
    keep = 'Pattern[^[0-9]{4}-[0-9]{2}$]: Does not match: "2027.03"'
    assert mask_shacl_message(keep, looks) == keep
    assert mask_shacl_message("Node 가나다 책임 bare", looks) == PERSON_MASK


@pytest.mark.shacl
def test_shacl_results_mask_person_like(tmp_path):
    """load_log shacl.results[].message 가 Jena sh:resultMessage 로 인명 유사 값을 그대로 옮겼다 (사내 load.bat 은 SHACL 이 켜진다 — env.bat 이
    FUSEKI_HOME·JAVA_HOME 을 둔다). 같은 값이 옆 '선택지 밖 값' 경고에서는 가려져 있었다 (2026-10-12 재검토 수리, docs/09 N5)."""
    from engenius_onto.shacl_check import find_tools

    if not find_tools():
        pytest.skip("FUSEKI_HOME/JAVA 없음")
    d = _copy(tmp_path)
    _set_row(d / STR, IO_SHEET, 9, {"방향": "나다라 선임에게"})
    _set_row(d / STR, IO_SHEET, 10, {"전달 방법": "가나다 책임 메일"})
    _set_row(d / STR, USAGE_SHEET, 6, {"구분": "가나다(책임)"})
    out = run_load(input_dir=d, registry_dir=tmp_path / "registry", out_root=tmp_path / "out", shacl=True)
    sh = out.log["shacl"]
    assert sh["ran"] and not sh["conforms"] and sh["violations"] >= 3
    masked = [r for r in sh["results"] if PERSON_MASK in r["message"]]
    assert len(masked) >= 3 and all(r["focus"] and r["path"] for r in masked)
    assert _no_tokens(json.dumps(sh, ensure_ascii=False), (out.out_dir / "load_log.json").read_text(encoding="utf-8"))
    assert "나다라 선임에게" in out.turtle                                                       # 그래프 값은 보존 (D6)


def test_shacl_message_mask_escaped_literals_unit():
    """Jena 는 RDF term 의 줄바꿈·탭을 '\\r\\n'·'\\t' 두 글자로 보인다 — 이름과 직급 사이에 Alt+Enter·탭이 든 값은 인명 패턴의 \\s* 가 맞지 않아
    가려지지 않았다 (2026-10-12 재검토 수리). 판정만 이스케이프를 풀어서, 출력은 PERSON_MASK 아니면 원래 글 그대로 (정규식 '\\d' 등은 손대지 않음)."""
    from engenius_onto.survey_load import _nt_unescape, mask_shacl_message

    looks = Normalizer.from_config().looks_person
    bs = chr(92)                                                                 # 백슬래시 한 글자 (Jena 메시지에 실제로 든 모양)
    assert not looks(f"가나다{bs}r{bs}n책임") and _nt_unescape(f"가나다{bs}r{bs}n책임") == "가나다\r\n책임"
    for lit in (f"가나다{bs}r{bs}n책임", f"가나다{bs}n책임", f"가나다{bs}t책임 메일", f"{bs}uAC00{bs}uB098{bs}uB2E4 책임", f"가나다{bs}u0009책임"):
        m = f'InConstraint["입력(소비)", "출력(생산)"] : RDF term "{lit}" not in expected values'
        assert mask_shacl_message(m, looks) == f'InConstraint["입력(소비)", "출력(생산)"] : RDF term "{PERSON_MASK}" not in expected values', lit
    keep = f'Pattern[^{bs}d{{4}}-{bs}d{{2}}$]: Does not match: "2027.03{bs}t"'
    assert mask_shacl_message(keep, looks) == keep
    assert _nt_unescape(f"a{bs}q{bs}{bs}b{bs}uZZZZ") == f"a{bs}q{bs}b{bs}uZZZZ"                   # 모르는 이스케이프는 그대로, \\\\ 는 하나로


@pytest.mark.shacl
def test_shacl_results_mask_newline_tab_values(tmp_path):
    """엑셀 Alt+Enter 줄바꿈·탭이 이름과 직급 사이에 든 선택지 값 — 적재기 경고는 가렸는데 load_log shacl.results 에는 Jena 가 이스케이프한 원문
    ('RDF term \"가나다\\r\\n책임\"')이 남았다 (2026-10-12 재검토 수리)."""
    from engenius_onto.shacl_check import find_tools

    if not find_tools():
        pytest.skip("FUSEKI_HOME/JAVA 없음")
    d = _copy(tmp_path)
    _set_row(d / STR, IO_SHEET, 9, {"방향": "가나다\n책임"})
    _set_row(d / STR, IO_SHEET, 10, {"전달 방법": "가나다\t책임 메일"})
    out = run_load(input_dir=d, registry_dir=tmp_path / "registry", out_root=tmp_path / "out", shacl=True)
    sh = out.log["shacl"]
    assert sh["ran"] and not sh["conforms"]
    assert len([r for r in sh["results"] if PERSON_MASK in r["message"]]) >= 2
    assert any(w.startswith("선택지 밖 값:") and PERSON_MASK in w for w in out.result.warnings)
    assert _no_tokens((out.out_dir / "load_log.json").read_text(encoding="utf-8"))


def test_schema_issue_messages_mask_person_like(tmp_path):
    """load_log schema_issues[].message — 생성 Pydantic 모델의 형식 검사기가 값을 통째로 인용한다 ('Invalid license_expiry format: <원문>').
    '만료 시기 형식 아님' 값은 원문 그대로 모델에 가서 인명 유사 메모가 load_log 에 옮겨졌다 (옆 경고에서는 가려져 있었다 — N5 와 같은 종류,
    2026-10-12 재검토 수리). 메시지만 가리고 slot·행은 그대로, 그래프 값은 보존 (D6). key 는 C8 범위라 이 시험이 보지 않는다."""
    from engenius_onto.survey_load import mask_issue_message

    d = _copy(tmp_path)
    _set_row(d / STR, USAGE_SHEET, 5, {"만료 시기": "2027-03 (가나다 책임 확인)"})                  # STR-01
    out = _load(d, tmp_path)
    assert f"만료 시기 형식 아님: {STR} {USAGE_SHEET} STR-01 '{PERSON_MASK}' — 원문 보존 (YYYY-MM 으로)" in out.result.warnings
    got = [i for i in out.schema_issues if i["slot"] == "license_expiry"]
    assert [(i["row"], i["message"]) for i in got] == [(5, f"Value error, Invalid license_expiry format: {PERSON_MASK}")]
    log = json.loads((out.out_dir / "load_log.json").read_text(encoding="utf-8"))
    assert _no_tokens(json.dumps(log["schema_issues"], ensure_ascii=False), (out.out_dir / "load_log.json").read_text(encoding="utf-8"))
    assert "2027-03 (가나다 책임 확인)" in out.turtle
    looks = Normalizer.from_config().looks_person
    assert mask_issue_message("Value error, Invalid extensions format: 가나다 책임", ["dat", "가나다 책임"], looks) == \
        f"Value error, Invalid extensions format: {PERSON_MASK}"                                  # 목록 값은 조각마다
    assert mask_issue_message("Value error, Invalid id format: egid:X 1", "egid:X 1", looks) == "Value error, Invalid id format: egid:X 1"
    assert mask_issue_message("Input should be a valid integer 가나다 책임", 3, looks) == PERSON_MASK   # 값과 따로 남으면 통째로


def test_tool_key_quotes_mask_names_with_text_after_rank(tmp_path):
    """툴 키는 공백을 지워 '가나다 책임 해석툴' → '가나다책임해석툴' — 직급 뒤에 한글이 이어져 키만으로는 인명 패턴에 안 걸린다 (원문은 걸린다).
    키를 인용하는 경고(흡수 보류·흡수)와 검토표 '비슷한 키' 힌트는 그 키를 낸 보고 이름까지 판정한다 (Loader._qk, 2026-10-12 재검토 수리 —
    전에는 '인명 유사 패턴' 경고가 같은 이름을 잡는 적재에서 키가 원문대로 나갔다)."""
    ld = Loader()
    assert ld._looks_person("가나다 책임 해석툴") and not ld._looks_person("가나다책임해석툴") and not ld._looks_person("altair가나다책임해석툴")
    d = _copy(tmp_path / "held")
    _set_names(d / STR, {"STR-04": "Altair 가나다 책임 해석툴", "STR-05": "가나다 책임 해석툴"})
    res = ld.load(ld.discover(d), known_tool_keys={"altair가나다책임해석툴", "가나다책임해석툴"})   # 둘 다 기존 활성 — 흡수 보류
    assert any(w.startswith("인명 유사 패턴:") for w in res.warnings)
    assert _w(res, "제조사 접두 흡수 보류") == [f"제조사 접두 흡수 보류: 기존 툴 둘 이상 ({PERSON_MASK}, {PERSON_MASK}) — 검토표에서 판정"]
    ld2 = Loader()
    res2 = ld2.load(ld2.discover(d))                                                          # 기존 툴 없음 — 흡수
    assert _w(res2, "제조사 접두 흡수:") == [f"제조사 접두 흡수: {STR} STR-04 '{PERSON_MASK}' → '{PERSON_MASK}' (제조사 접두를 뗀 키)"]
    assert _no_tokens("\n".join(res.warnings + res2.warnings))
    d2 = _copy(tmp_path / "hint")
    _set_names(d2 / STR, {"STR-01": "가나다 책임 해석툴"})
    _set_io_cells(d2 / STR, {("STR-02", "익형 형상"): {H_PARTNER: "가나다해석"}})
    out = _load(d2, tmp_path / "hint")
    rows = [r for r in _review_rows(out) if r["사유"] == PARTNER and r["툴B_키"] == "가나다해석"]
    assert len(rows) == 1 and rows[0]["툴A_키"] == ""
    assert rows[0]["툴A_표기"] == f"(기존 툴이면 툴A_키에 그 툴 키를 적는다 — 비슷한 키: {PERSON_MASK} 0.77)"
    assert "가나다책임해석툴" not in (out.out_dir / "tool_review.csv").read_text(encoding="utf-8-sig")
    plain = Loader()                                                                          # 대조 — 보고 이름이 인명 유사가 아니면 키 그대로
    plain._key_names = {"hypermesh": {"HyperMesh"}}
    assert plain._qk("hypermesh") == "hypermesh" and plain._qk("가나다책임") == PERSON_MASK


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


def test_copy_of_superseded_file_not_loaded(tmp_path):
    """I33: 재발송으로 대체된 옛 회신과 내용이 같은 사본(탐색기 '- 복사본'·다른 약칭으로 저장한 규칙 안 파일)도 적재하지 않는다 — 옛 데이터가
    사본으로 다시 들어와 툴사용이 두 번 잡히지 않게 (2026-10-12 검토 수리: 전에는 대체된 파일이 '같은 내용' 대조에서 빠져 사본이 적재됐다)."""
    one = _load(_survey(tmp_path, "one", {TURB: TURB}), tmp_path / "one")
    n = len(one.result.usages)
    survey = tmp_path / "survey"
    _place(survey, TURB, "SW조사_터빈_20260901.xlsx")
    _place(survey, TURB, "SW조사_터빈_20260901 - 복사본.xlsx")
    _set_names(_place(survey, TURB, "SW조사_터빈_20260915.xlsx"), {"TURB-01": "가상-새회신툴"})
    _place(survey, TURB, "SW조사_압축기_20260901.xlsx")                     # 다른 약칭으로 잘못 저장한 옛 터빈 회신
    out = _load(survey, tmp_path)
    assert [f.name for f in out.result.loaded_files] == ["SW조사_터빈_20260915.xlsx"]
    assert len(out.result.usages) == n and "가상-새회신툴" in out.turtle
    same = sorted(x for x in out.result.warnings if x.startswith("같은 내용 파일"))
    tail = "(SW조사_터빈_20260901.xlsx 은 재발송으로 대체됨 — 적재 안 함)"
    assert len(same) == 2
    assert same[0] == f"같은 내용 파일: SW조사_압축기_20260901.xlsx = SW조사_터빈_20260901.xlsx {tail} — 약칭이 다르다, 어느 파트 파일인지 확인"
    assert re.fullmatch(rf"같은 내용 파일: Tool조사_규칙밖_[0-9a-f]{{10}}\.xlsx = SW조사_터빈_20260901\.xlsx {re.escape(tail)}", same[1])
    dup = {f["name"]: f["duplicate_of"] for f in out.log["files"] if f["duplicate_of"]}
    assert set(dup.values()) == {"SW조사_터빈_20260901.xlsx"} and len(dup) == 2
    assert not any(x.startswith(("규칙 밖 파일의 Tool ID", "파일 분야 ≠ 담당 부서")) for x in out.result.warnings)
    # 대체된 옛 회신과 같은 내용인 최신 파일 자신(내용 같은 재발송)은 정상 — 그 사본만 한 번만 (기존 동작)
    s2 = tmp_path / "s2"
    _place(s2, TURB, "SW조사_터빈_20260901.xlsx")
    _place(s2, TURB, "SW조사_터빈_20260915.xlsx")
    _place(s2, TURB, "SW조사_터빈_20260915 - 복사본.xlsx")
    out2 = _load(s2, tmp_path / "t2")
    assert [f.name for f in out2.result.loaded_files] == ["SW조사_터빈_20260915.xlsx"] and len(out2.result.usages) == n
    assert [x for x in out2.result.warnings if x.startswith(("재발송으로 대체", "같은 내용 파일"))][0] == \
        "재발송으로 대체: SW조사_터빈_20260901.xlsx → SW조사_터빈_20260915.xlsx (적재 안 함) (내용 같음)"
    assert any(re.fullmatch(r"같은 내용 파일: Tool조사_규칙밖_[0-9a-f]{10}\.xlsx = SW조사_터빈_20260915\.xlsx \(한 번만 적재\)", x)
               for x in out2.result.warnings)


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


# --------------------------------------------------------------------------- D. 값·엑셀 층 (묶음 values, 2026-10-12)
from engenius_onto.form_spec import load_form_spec  # noqa: E402
from test_loader_m31 import _to_v11  # noqa: E402

EXP = "만료 시기"
ERR_W, NOCACHE_W, HIDDEN_W, COPY_W, OFF_W, ZERO_W = "수식 오류 셀", "캐시 없는 수식", "숨긴 행", "양식 사본 시트", "양식 밖 시트", "툴사용 0건"
ERR_TAIL = " — 빈칸으로 봄 (#N/A·#REF! 등 수식 결과 오류, 수정 요청표에 행별로)"
NOCACHE_TAIL = " — 값을 읽지 못함 (엑셀에서 열어 저장하면 읽힘)"


def _w(res, prefix: str) -> list[str]:
    return [w for w in res.warnings if w.startswith(prefix)]


def _overlay(tmp: Path, **files) -> Path:
    """사내 설정 오버레이 폴더 흉내 (data/real/config 대신 tmp 아래) — {이름: YAML 데이터}."""
    over = tmp / "real_config"
    over.mkdir(exist_ok=True)
    for name, data in files.items():
        (over / f"{name}.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return over


# ---- D1. header_map 오버레이 (I30)
def test_merge_config_header_map_union():
    """시트·슬롯별 문구 합집합 — 저장소 문구 먼저, 같은 문구는 한 번. 문자열 하나는 글자 단위로 매핑되지 않게 형식 오류."""
    base = {USAGE_SHEET: {"source_key": ["Tool ID"]}}
    over = {USAGE_SHEET: {"source_key": ["SW 식별번호", "Tool ID"]}, IO_SHEET: {"extensions_raw": ["확장자"]}}
    assert merge_config("header_map.yaml", base, over) == {USAGE_SHEET: {"source_key": ["Tool ID", "SW 식별번호"]},
                                                           IO_SHEET: {"extensions_raw": ["확장자"]}}
    with pytest.raises(ConfigError, match="문구 목록"):
        merge_config("header_map.yaml", base, {IO_SHEET: {"note": "비고2"}})
    with pytest.raises(ConfigError, match="매핑"):
        merge_config("header_map.yaml", base, {IO_SHEET: ["note"]})


def test_header_map_overlay_maps_internal_header(tmp_path):
    """사내 양식 헤더('확장자')는 오버레이 header_map.yaml 에 더한다 — 시트 키는 v1.1 이름('Tool 입출력')도, 저장소 문구('Tool ID')는 그대로."""
    base = _load(_copy(tmp_path / "a"), tmp_path / "a").result
    d = _copy(tmp_path / "b")
    wb = openpyxl.load_workbook(d / STR)
    next(c for c in wb[IO_SHEET][2] if c.value == H_EXT).value = "확장자"
    wb.save(d / STR)
    plain = _load(d, tmp_path / "b").result
    assert f"매핑 안 된 헤더: {STR} {IO_SHEET} '확장자'" in plain.warnings
    assert _w(plain, f"양식 열 없음: {STR} {IO_SHEET}")
    over = _overlay(tmp_path, header_map={"Tool 입출력": {"extensions_raw": ["확장자"]}})
    assert load_form_spec(overlay_dir=over).by_header(IO_SHEET)["확장자"].slot == "extensions_raw"
    out = _load(d, tmp_path / "c", overlay_dir=over)
    sig = lambda res: sorted((x.key, tuple(x.exts)) for x in res.ios)  # noqa: E731
    assert sig(out.result) == sig(base)
    assert not [w for w in out.result.warnings if w.startswith(("매핑 안 된 헤더", "양식 열 없음"))]
    assert "header_map.yaml" in out.log["config_overlay"]["files"]
    d2 = _copy(tmp_path / "v11")
    new = d2 / "Tool조사_구조_20260930.xlsx"
    (d2 / STR).rename(new)
    _to_v11(new)
    v11 = _load(d2, tmp_path / "v11", overlay_dir=over).result                 # 합집합 — 저장소의 v1.1 문구 'Tool ID' 도 매핑
    assert len(v11.usages) == len(base.usages) and len(v11.ios) == len(base.ios)
    assert not [w for w in v11.warnings if w.startswith(("매핑 안 된 헤더", "양식 열 없음"))]


@pytest.mark.parametrize("data, match", [
    ({IO_SHEET: {"note": "비고2"}}, "문구 목록"),
    ({"없는 시트": {"note": ["메모란"]}}, "알 수 없는 시트"),
    ({USAGE_SHEET: {"없는슬롯": ["메모란"]}}, "알 수 없는 슬롯"),
    ({USAGE_SHEET: {"note": ["실무 문의처(선택)"]}}, "제외 열"),
    ({USAGE_SHEET: {"note": ["실무 문의처"]}}, "제외 열"),
    ({"Tool 기본정보": {"note": ["담당자 연락처"]}}, "제외 열"),
    ({IO_SHEET: {"note": ["SW명(자동)"]}}, "제외 열"),
    ({USAGE_SHEET: {"note": ["버전"]}}, "가로챌"),
    ({USAGE_SHEET: {"note": ["메모란"], "roadmap_note": ["메모란"]}}, "같은 문구"),
    ({USAGE_SHEET: {"note": ["Tool ID"]}}, "같은 문구"),
], ids=["string", "sheet", "slot", "contact", "contact-short", "person-words", "formula-col", "default-phrase", "two-slots", "repo-clash"])
def test_header_map_overlay_rejects_bad_entries(tmp_path, data, match):
    """설정 오류(ConfigError) — 오버레이 파일 경로가 붙고 헤더 문구는 오류 문구에 넣지 않는다. 문의처 열 매핑 금지 = 절대 규칙 5."""
    over = _overlay(tmp_path, header_map=data)
    with pytest.raises(ConfigError, match=match) as e:
        Loader(overlay_dir=over)
    msg = str(e.value)
    assert str((over / "header_map.yaml").resolve()) in msg
    phrases = [p for slots in data.values() for v in slots.values() for p in (v if isinstance(v, list) else [v])]
    assert not any(p in msg for p in phrases), msg


def test_header_map_overlay_error_stops_cli_load(tmp_path):
    """cli load 는 오버레이 header_map 오류를 traceback 없이 '[NG] 설정 오류' 로 — rc 2 (load.bat '시작 못 함')."""
    from engenius_onto.cli import main

    d = _copy(tmp_path)
    over = _overlay(tmp_path, header_map={USAGE_SHEET: {"note": ["실무 문의처(선택)"]}})
    rc = main(["load", "--input", str(d), "--registry", str(tmp_path / "registry"), "--out", str(tmp_path / "out"),
               "--no-shacl", "--overlay", str(over)])
    assert rc == 2 and not (tmp_path / "out").exists()


# ---- D2. 엑셀 층 신호 (I37)
def test_error_cells_blank_with_one_warning_per_column(tmp_path):
    """수식 오류 셀은 빈칸 — 열마다 경고 1줄, 행마다 수정 요청. '#N/A' 가 툴 이름 'na' 로 레지스트리에 영구 행을 만들지 않는다."""
    d = _copy(tmp_path)
    _set_row(d / STR, USAGE_SHEET, 9, {"SW명(정식)": "#N/A"})            # STR-04
    _set_row(d / STR, USAGE_SHEET, 5, {"담당 부서": "#REF!"})            # STR-01
    _set_row(d / STR, USAGE_SHEET, 6, {"담당 부서": "#REF!"})            # STR-02 — 같은 열 두 칸은 한 줄
    res = _load(d, tmp_path).result
    assert _w(res, ERR_W) == [f"수식 오류 셀: {STR} {USAGE_SHEET} 'SW명(정식)' 1칸{ERR_TAIL}",
                              f"수식 오류 셀: {STR} {USAGE_SHEET} '담당 부서' 2칸{ERR_TAIL}"]
    u4 = _usage(res, "구조/STR-04")
    assert u4.v["reported_tool_name"] is None and u4.tool_key.startswith("미상:")
    assert "na" not in res.tools and "na" not in {r["key"] for r in read_csv_rows(tmp_path / "registry" / "tools.csv")[0]}
    assert _usage(res, "구조/STR-01").v["reported_domain"] is None
    iss = sorted((i["row"], i["column"], i["value"]) for i in res.issues if i["kind"] == ERR_W)
    assert iss == [(5, "담당 부서", "#REF!"), (6, "담당 부서", "#REF!"), (9, "SW명(정식)", "#N/A")]
    assert f"필수값 누락: {STR} {USAGE_SHEET} STR-04 'SW명(정식) *'" in res.warnings          # 경고는 그대로, 수정 요청은 한 행만
    assert not [i for i in res.issues if i["kind"] == "필수값 누락" and i["row"] in (5, 6, 9)]


def test_error_tool_id_row_excluded_not_filled_down(tmp_path):
    """Tool ID 칸이 수식 오류면 행 제외 — 입출력은 위 행 ID 를 이어받지도(빈칸으로만 보면 붙었다), 아래 행에 넘겨주지도 않는다 (I22 보호)."""
    d = _copy(tmp_path)
    _set_row(d / STR, USAGE_SHEET, 10, {"SW ID": "#VALUE!"})            # STR-05
    _set_row(d / STR, IO_SHEET, 9, {"SW ID": "#N/A"})                   # STR-01 '구조 메시' — 바로 위 8행은 STR-01
    _set_row(d / STR, IO_SHEET, 10, {"SW ID": None})                    # 오류 행 바로 아래 빈 ID
    res = _load(d, tmp_path).result
    assert not {"#VALUE!", "STR-05"} & {u.sw_id for u in res.usages}
    ex = {(r["sheet"], r["row"]): r["reason"] for r in res.excluded_rows}
    assert ex[(USAGE_SHEET, 10)] == ex[(IO_SHEET, 9)] == "Tool ID 수식 오류 (I37)"
    assert ex[(IO_SHEET, 10)] == "SW ID 없음 (I22)"
    assert not _w(res, "Tool ID 이어받음")
    assert not [x for x in res.ios if x.row in (9, 10)]
    assert _w(res, ERR_W) == [f"수식 오류 셀: {STR} {USAGE_SHEET} 'SW ID' 1칸{ERR_TAIL}", f"수식 오류 셀: {STR} {IO_SHEET} 'SW ID' 1칸{ERR_TAIL}"]
    iss = [(i["sheet"], i["row"], i["tool_id"], i["column"], i["value"]) for i in res.issues if i["kind"] == ERR_W]
    assert iss == [(USAGE_SHEET, 10, "", "SW ID", "#VALUE!"), (IO_SHEET, 9, "", "SW ID", "#N/A")]


def test_formula_without_cache_warns(tmp_path):
    """캐시 없는 수식(openpyxl 로 저장한 수식 — 엑셀이 계산해 저장하지 않음)은 적재 열마다 경고. 무시 열(SW명(자동))의 수식은 세지 않는다."""
    d = _copy(tmp_path)
    _set_row(d / STR, USAGE_SHEET, 9, {"SW명(정식)": "=A1"})
    _set_row(d / STR, USAGE_SHEET, 6, {"사용 인원수": "=1+2"})
    res = _load(d, tmp_path).result
    assert _w(res, NOCACHE_W) == [f"캐시 없는 수식: {STR} {USAGE_SHEET} 'SW명(정식)' 1칸{NOCACHE_TAIL}",
                                  f"캐시 없는 수식: {STR} {USAGE_SHEET} '사용 인원수' 1칸{NOCACHE_TAIL}"]
    assert not _w(res, ERR_W) and _usage(res, "구조/STR-02").v["user_count"] is None


def test_formula_scan_failure_keeps_loading(tmp_path, monkeypatch):
    """수식 검사(시트 XML 직접 읽기)가 실패해도 적재는 계속 — 경고 '수식 검사 못 함' 한 줄 (값·경로 없이 예외 종류만)."""
    from engenius_onto import loader as loader_mod

    def fake(path, *a, **kw):
        raise OSError("가상 실패")

    d = _copy(tmp_path)
    base = len(_load(d, tmp_path / "a").result.usages)
    monkeypatch.setattr(loader_mod, "formula_cells_without_cache", fake)
    res = _load(d, tmp_path / "b").result
    assert _w(res, "수식 검사 못 함") == [f"수식 검사 못 함: {STR} — OSError (캐시 없는 수식 경고를 내지 않음, 적재는 계속)"]
    assert len(res.usages) == base == 5


def test_hidden_rows_loaded_with_warning(tmp_path):
    """숨긴 행(필터·그룹 접기 포함)은 응답으로 적재하고 시트마다 경고 1줄 + 행마다 수정 요청. 숨긴 예시 행은 세지 않는다."""
    d = _copy(tmp_path)
    wb = openpyxl.load_workbook(d / STR)
    wb[USAGE_SHEET].row_dimensions[6].hidden = True                     # STR-02
    wb[USAGE_SHEET].row_dimensions[4].hidden = True                     # 예시 행
    wb[IO_SHEET].row_dimensions[12].hidden = True
    wb[IO_SHEET].row_dimensions[13].hidden = True
    wb.save(d / STR)
    res = _load(d, tmp_path).result
    assert "STR-02" in {u.sw_id for u in res.usages} and len({x.row for x in res.ios if x.row in (12, 13)}) == 2
    assert _w(res, HIDDEN_W) == [f"숨긴 행: {STR} {USAGE_SHEET} 1행 — 응답으로 적재함 (첫 행 6)",
                                 f"숨긴 행: {STR} {IO_SHEET} 2행 — 응답으로 적재함 (첫 행 12)"]
    assert {(i["sheet"], i["row"]) for i in res.issues if i["kind"] == HIDDEN_W} == {(USAGE_SHEET, 6), (IO_SHEET, 12), (IO_SHEET, 13)}


def test_copied_form_sheet_and_zero_usage_warn(tmp_path):
    """응답을 'SW기본정보 (2)' 사본 시트에 적고 원래 시트에는 예시만 — 사본은 읽지 않고 '양식 사본 시트'·'툴사용 0건' 경고(+ 수정 요청).
    헤더가 양식과 다른 시트는 '양식 밖 시트' 경고만, 빈 시트는 경고 없음, 시트 이름이 인명 유사면 가린다. rules 오버레이 other_sheets 로 끈다."""
    d = _copy(tmp_path)
    wb = openpyxl.load_workbook(d / STR)
    cp = wb.copy_worksheet(wb[USAGE_SHEET])
    cp.title, cp.sheet_state = "SW기본정보 (2)", "hidden"
    ws = wb[USAGE_SHEET]
    for r in range(5, ws.max_row + 1):
        for c in range(1, ws.max_column + 1):
            ws.cell(r, c).value = None
    wb.create_sheet("메모")["A1"] = "가상 메모"
    wb.create_sheet("빈 시트")
    wb.create_sheet("가나다 책임 메모")["B3"] = "가상"
    wb.save(d / STR)
    res = _load(d, tmp_path).result
    assert not res.usages
    assert _w(res, COPY_W) == [f"양식 사본 시트: {STR} 'SW기본정보 (2)' (숨김) — {USAGE_SHEET} 와 같은 헤더, 내용 7행, 적재하지 않음"]
    off = " — 읽지 않음 (아는 시트면 rules.yaml loader.other_sheets 에 추가)"
    assert _w(res, OFF_W) == [f"양식 밖 시트: {STR} '메모'{off}", f"양식 밖 시트: {STR} '{PERSON_MASK}'{off}"]
    assert not any("가나다" in w for w in res.warnings)
    assert _w(res, ZERO_W) == [f"툴사용 0건: {STR} — 기본정보 시트에서 적재한 행이 없음 (예시만 남았거나 시트·헤더가 양식과 다름)"]
    kinds = Counter(i["kind"] for i in res.issues)
    assert (kinds[COPY_W], kinds[ZERO_W], kinds[OFF_W]) == (1, 1, 0)
    iss = next(i for i in res.issues if i["kind"] == COPY_W)
    assert (iss["sheet"], iss["value"]) == (USAGE_SHEET, "SW기본정보 (2)")
    over = _overlay(tmp_path, rules={"loader": {"other_sheets": ["작성안내", "메모"]}})
    ld = Loader(overlay_dir=over)
    res2 = ld.load(ld.discover(d))
    assert _w(res2, OFF_W) == [f"양식 밖 시트: {STR} '{PERSON_MASK}'{off}"] and len(_w(res2, COPY_W)) == 1


def _patch_cell_xml(path: Path, ref: str, new_xml: str) -> None:
    """xlsx 안 시트 XML 에서 칸 하나(<c r="ref" …>…</c>)를 통째로 바꾼다 — 그 칸에 openpyxl 로 먼저 'MARK' 가 든 수식을 넣어 두고 그 시트를 찾는다
    (엑셀이 저장한 모양을 openpyxl 없이 흉내 — 2026-10-12 검토: 엑셀 실측 '<c t="str"><f>…</f><v/></c>')."""
    import zipfile

    with zipfile.ZipFile(path) as z:
        items = [(i, z.read(i.filename)) for i in z.infolist()]
    hit = 0
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in items:
            if info.filename.startswith("xl/worksheets/") and b"MARK" in data:
                data, k = re.subn(rf'<c r="{ref}"[^>]*>.*?</c>'.encode(), new_xml.encode(), data, count=1)
                hit += k
            z.writestr(info, data)
    assert hit == 1


@pytest.mark.parametrize("cell, warned", [
    ('<c r="{ref}" t="str"><f>IFERROR(VLOOKUP(A5,Z:Z,1,0),"")</f><v/></c>', False),   # 엑셀 저장본 — 캐시된 빈 문자열
    ('<c r="{ref}" t="str"><f>IF(1=1,"","")</f><v></v></c>', False),                  # LibreOffice 저장본
    ('<c r="{ref}"><f>IF(1=1,"","")</f></c>', True),                                   # <v> 없음 — 캐시 없음
    ('<c r="{ref}"><f>IF(1=1,"","")</f><v/></c>', True),                               # openpyxl 저장본 (형식 n + 빈 <v>) — 캐시 없음
    ('<c r="{ref}" t="str"><f>IF(1=1,"x","")</f><v>x</v></c>', False),
], ids=["excel-v-selfclose", "libreoffice-v-empty", "no-v", "openpyxl", "cached-text"])
def test_formula_empty_string_cache_not_warned(tmp_path, cell, warned):
    """I37 ②: 빈 문자열을 돌려주는 수식(=IFERROR(…,""))을 엑셀은 t="str" + 빈 <v> 로 저장한다 — 캐시가 있는 칸이라 '캐시 없는 수식' 이 아니다
    (2026-10-12 검토 수리: openpyxl 은 셋을 모두 None 으로 읽어 다시 저장해도 사라지지 않는 거짓 경고가 났다 — 시트 XML 을 직접 본다)."""
    from openpyxl.utils import get_column_letter

    d = _copy(tmp_path)
    _set_row(d / STR, USAGE_SHEET, 5, {"비고": '="MARK"'})
    ref = get_column_letter(_cols(openpyxl.load_workbook(d / STR)[USAGE_SHEET])["비고"]) + "5"
    _patch_cell_xml(d / STR, ref, cell.format(ref=ref))                                     # 칸 글(text)의 " 는 XML 에서 그대로 둬도 된다
    res = _load(d, tmp_path).result
    want = [f"캐시 없는 수식: {STR} {USAGE_SHEET} '비고' 1칸{NOCACHE_TAIL}"] if warned else []
    assert _w(res, NOCACHE_W) == want
    assert len(res.usages) == 5


def _choices_rectangle(ws) -> dict[str, list[str]]:
    """선택지 시트를 직사각형(ws.cell)으로 읽는 옛 방식 — 있는 칸만 읽는 _read_choices 와 결과가 같아야 한다 (비교용)."""
    from engenius_onto.form_spec import norm_header as nh
    from engenius_onto.normalize import nfc_strip

    out = {}
    for c in range(1, ws.max_column + 1):
        col = [ws.cell(r, c).value for r in range(2, ws.max_row + 1)]
        vals = [nfc_strip(v) for v in col if v is not None and not (isinstance(v, str) and not v.strip())]
        if vals:
            out[nh(vals[0])] = vals[1:]
    return out


def test_far_styled_cells_do_not_blow_up(tmp_path):
    """서식만 있는 먼 칸(엑셀 Ctrl+End 가 튀는 칸) — 양식 밖 시트 검사·시트 행 읽기·선택지 읽기가 max_row × max_column 직사각형을 만들지 않는다
    (2026-10-12 검토 수리, docs/09 C7: '개정이력' 시트 (100000행, 30열) 칸 하나에 8~18초·730MB 였다; 선택지 시트(_read_choices)는 재검토 수리).
    있는 칸만 훑어 결과는 같다."""
    from openpyxl.styles import Border, Side

    d = _copy(tmp_path)
    wb = openpyxl.load_workbook(d / STR)
    extra = wb.create_sheet("개정이력")
    extra["A1"] = "가상 개정 이력"
    thin = Border(left=Side(style="thin"))
    extra.cell(100000, 30).border = thin
    wb[IO_SHEET].cell(100000, 30).border = thin
    wb[USAGE_SHEET].cell(100000, 30).border = thin
    wb["선택지"].cell(100000, 30).border = thin
    wb.save(d / STR)
    base = _load(_copy(tmp_path / "base"), tmp_path / "base").result
    ld = Loader()
    wb0 = openpyxl.load_workbook(SURVEY_DIR / STR, data_only=True)
    want_choices = _choices_rectangle(wb0["선택지"])
    assert ld._read_choices(wb0) == want_choices and len(want_choices) > 10
    wb0.close()
    wb = openpyxl.load_workbook(d / STR, data_only=True)
    sizes = {ws.title: len(ws._cells) for ws in wb.worksheets}
    rep = FileReport(STR, "0" * 64, "구조", "20260924", path=d / STR)
    w: list[str] = []
    ld._used_sheets = {USAGE_SHEET, IO_SHEET}
    ld._formula_cells = {}
    assert ld._read_choices(wb) == want_choices
    ld._extra_sheets(wb, rep, w)
    assert w == [f"양식 밖 시트: {STR} '개정이력' — 읽지 않음 (아는 시트면 rules.yaml loader.other_sheets 에 추가)"]
    ld._read_sheet(wb, IO_SHEET, rep, [], [])
    ld._read_sheet(wb, USAGE_SHEET, rep, [], [])
    grown = {ws.title: len(ws._cells) - sizes[ws.title] for ws in wb.worksheets}
    assert grown["개정이력"] == 0 and grown["선택지"] == 0 and grown[IO_SHEET] < 2000 and grown[USAGE_SHEET] < 2000, grown
    wb.close()
    t0 = time.perf_counter()
    res = _load(d, tmp_path).result
    assert time.perf_counter() - t0 < 6                                                      # 고치기 전 15초 이상
    assert sorted(x.key for x in res.ios) == sorted(x.key for x in base.ios) and len(res.usages) == len(base.usages)
    assert _w(res, OFF_W) == w


def test_old_rules_without_new_loader_keys(tmp_path):
    """사내 rules.yaml 이 로컬 수정이라 업데이트가 rules.yaml.new 로만 남긴 상태(새 키 month_blank_values·other_sheets 없음) — 코드 기본값이
    배포 값과 같아 '작성안내' 가 '양식 밖 시트' 로 쏟아지지 않고 '영구' 도 빈칸 (2026-10-12 검토 수리). 키를 빈 목록으로 적으면 그 뜻대로."""
    d = _copy(tmp_path)
    _set_row(d / STR, USAGE_SHEET, 10, {EXP: "영구"})                                     # STR-05
    cfg = _cfg_copy(tmp_path)
    rules = yaml.safe_load((cfg / "rules.yaml").read_text(encoding="utf-8"))
    for k in ("month_blank_values", "other_sheets"):
        rules["loader"].pop(k)
    (cfg / "rules.yaml").write_text(yaml.safe_dump(rules, allow_unicode=True), encoding="utf-8")
    res = _load(d, tmp_path, config_dir=cfg).result
    assert not _w(res, OFF_W) and not _w(res, "만료 시기 형식 아님")
    assert _usage(res, "구조/STR-05").v["license_expiry"] is None and _w(res, "빈 값 표기 만료 시기")
    assert not [i for i in res.issues if i["kind"] == "만료 시기 형식"]
    rules["loader"].update(month_blank_values=[], other_sheets=[])
    (cfg / "rules.yaml").write_text(yaml.safe_dump(rules, allow_unicode=True), encoding="utf-8")
    res2 = _load(d, tmp_path / "b", config_dir=cfg).result
    assert _w(res2, OFF_W) == [f"양식 밖 시트: {STR} '작성안내' — 읽지 않음 (아는 시트면 rules.yaml loader.other_sheets 에 추가)"]
    assert _usage(res2, "구조/STR-05").v["license_expiry"] == "영구" and _w(res2, "만료 시기 형식 아님")


# ---- D3. 만료 시기 텍스트·'영구' (docs/09 #21 3단, I16·I27)
def test_expiry_text_normalized(tmp_path):
    """텍스트 날짜는 YYYY-MM + 경고 — 스키마 패턴 위반(Pydantic schema_issues)도 사라진다. 이미 YYYY-MM 인 텍스트는 경고 없음."""
    d = _copy(tmp_path)
    for row, val in ((5, "2027.03"), (6, "2027-03-31"), (9, "2027년 3월"), (10, "2027. 3. 31."), (7, "2027-03")):
        _set_row(d / STR, USAGE_SHEET, row, {EXP: val})
    out = _load(d, tmp_path)
    res = out.result
    assert {u.sw_id: u.v["license_expiry"] for u in res.usages} == dict.fromkeys(["STR-01", "STR-02", "STR-03", "STR-04", "STR-05"], "2027-03")
    assert _w(res, "만료 시기") == [f"만료 시기 표기 변환: {STR} {USAGE_SHEET} STR-01 '2027.03' → '2027-03'",
                                   f"만료 시기 표기 변환: {STR} {USAGE_SHEET} STR-02 '2027-03-31' → '2027-03'",
                                   f"만료 시기 표기 변환: {STR} {USAGE_SHEET} STR-04 '2027년 3월' → '2027-03'",
                                   f"만료 시기 표기 변환: {STR} {USAGE_SHEET} STR-05 '2027. 3. 31.' → '2027-03'"]
    assert not [i for i in out.schema_issues if i["slot"] == "license_expiry"]


def test_expiry_blank_tokens(tmp_path):
    """'영구'(양식 안내 '영구면 공란', v1.1 예시 행 값)와 빈 값 토큰은 빈칸 — 원문도 남기지 않고 파일당 한 줄, 수정 요청 없음."""
    d = _copy(tmp_path)
    for row, val in ((5, "영구"), (6, "없음"), (7, "-"), (9, "NA")):
        _set_row(d / STR, USAGE_SHEET, row, {EXP: val})
    out = _load(d, tmp_path)
    res = out.result
    assert all(u.v.get("license_expiry") is None and "license_expiry" not in u.raw for u in res.usages)
    assert _w(res, "빈 값 표기 만료 시기") == [f"빈 값 표기 만료 시기: {STR} 4칸 — 빈칸으로 봄 ('영구'·NA·- 등, docs/09 #21)"]
    assert not _w(res, "만료 시기") and not [i for i in res.issues if i["kind"] == "만료 시기 형식"]
    assert "license_expiry" not in out.turtle                                   # 구조 파일은 원래 만료 시기가 비어 있다 (라이선스 형태 '영구' 는 다른 열)


def test_expiry_unrecognized_text_kept(tmp_path):
    """그 밖 텍스트는 원문 보존(D4) + 경고 + 수정 요청 '만료 시기 형식' — 스키마 층은 계속 위반. 인명 유사 값은 경고·수정 요청에 옮기지 않는다."""
    d = _copy(tmp_path)
    _set_row(d / STR, USAGE_SHEET, 5, {EXP: "2027년 상반기"})
    _set_row(d / STR, USAGE_SHEET, 6, {EXP: "가나다 책임 확인"})
    out = _load(d, tmp_path)
    res = out.result
    assert _usage(res, "구조/STR-01").v["license_expiry"] == "2027년 상반기"
    tail = " — 원문 보존 (YYYY-MM 으로)"
    assert _w(res, "만료 시기 형식 아님") == [f"만료 시기 형식 아님: {STR} {USAGE_SHEET} STR-01 '2027년 상반기'{tail}",
                                         f"만료 시기 형식 아님: {STR} {USAGE_SHEET} STR-02 '{PERSON_MASK}'{tail}"]
    assert not any("가나다" in w for w in res.warnings)
    iss = [(i["row"], i["tool_id"], i["column"], i["value"]) for i in res.issues if i["kind"] == "만료 시기 형식"]
    assert iss == [(5, "STR-01", EXP, "2027년 상반기"), (6, "STR-02", EXP, "")]
    assert ("구조/STR-01", "license_expiry") in {(i["key"], i["slot"]) for i in out.schema_issues}


def test_expiry_value_alias_applies_to_original_text(tmp_path):
    """값 대응표(value_aliases)에 원문 그대로 적은 만료 시기는 경고 없이 대응표가 바꾼다 — 만료 시기 규칙보다 먼저."""
    d = _copy(tmp_path)
    _set_row(d / STR, USAGE_SHEET, 5, {EXP: "2027년 상반기"})
    _set_row(d / STR, USAGE_SHEET, 6, {EXP: "영구"})
    over = _overlay(tmp_path, value_aliases={EXP: {"2027년 상반기": "2027-06", "영구": "2099-12"}})
    res = _load(d, tmp_path, overlay_dir=over).result
    assert (_usage(res, "구조/STR-01").v["license_expiry"], _usage(res, "구조/STR-02").v["license_expiry"]) == ("2027-06", "2099-12")
    assert not _w(res, "만료 시기") and not _w(res, "빈 값 표기 만료 시기")
    assert f"값 대응표 적용: {STR} 2건 (config/value_aliases.yaml)" in res.warnings


EXPIRY_CASES = ["2027.03", "2027-3", "2027/03", "2027-03-31", "2027.03.31", "2027. 3. 31.", "2027년 3월", "2027년 3월 31일", "2027년3월",
                "2027-03", "２０２７．０３", " 2027.03 ", "2027.1", "2027-13", "2027-03-00", "2027-03-32", "2027년 상반기", "27.03", "2027",
                "영구", "NA", "-", "해당 없음", "없음", 2027.1, 2027, 2027.0, dt.date(2027, 3, 31), dt.datetime(2027, 3, 1)]


@pytest.mark.parametrize("raw", EXPIRY_CASES, ids=[repr(c) for c in EXPIRY_CASES])
def test_expiry_text_parity_with_oracle(raw):
    """만료 시기 칸 — 적재기 Loader._convert ↔ oracle.cell_to_text (독립 구현): 값·경고 문구·빈 값 표기 건수가 같다.
    실수 셀 2027.1 은 문자열 정규화를 타지 않는다 ('2027.1' + 엑셀 숫자 변환 가능성 — 골든 D5-expiry-float)."""
    ld = Loader()
    col = next(c for c in ld.spec.columns[USAGE_SHEET] if c.slot == "license_expiry")
    rep = FileReport("f.xlsx", "", None, None)
    ld.issues, ld._na_month_cells = [], 0
    w1, w2, counts = [], [], Counter()
    got, raw_back = ld._convert(col, raw, "W", w1, rep, 5, "X-1")
    exp = oracle.cell_to_text("expiry", raw, "W", w2, counts)
    assert (got, w1, ld._na_month_cells) == (exp, w2, counts["na_month"])
    assert raw_back is None and rep.warnings == len(w1)
    if raw == 2027.1:
        assert got == "2027.1"
    if isinstance(raw, str) and w1 and w1[0].startswith("만료 시기 형식 아님"):
        assert [i["kind"] for i in ld.issues] == ["만료 시기 형식"]


@pytest.mark.parametrize("val, warn, na", [("NA", False, 1), ("-", False, 1), ("ＮＡ", False, 1), ("해당 없음", False, 1),
                                           ("API 있음", True, 0), ("모름", False, 0)])
def test_dropdown_empty_token_parity(val, warn, na):
    """I28 기록 (docs/09 #21 1단): 드롭다운 목록 밖 빈 값 토큰은 선택지 밖 경고 대신 파일당 건수 — 적재기 _check ↔ oracle.check_row."""
    choices = ["없음", "모름", "COM·OLE"]
    w_o, c = [], Counter()
    oracle.check_row({"auto_if": ("자동화 인터페이스 *", "자동화IF", True)}, {"auto_if": val}, {"자동화IF": choices}, "W", w_o, USAGE_SHEET, c)
    ld = Loader()
    ld.issues, ld._na_cells = [], 0
    w_l = []
    ld._check(USAGE_SHEET, {"automation_if": val}, {"automation_if"}, {"자동화IF": choices}, "W", w_l, FileReport("f.xlsx", "", None, None),
              5, "X-1", set())
    assert w_l == w_o and (ld._na_cells, c["na_choice"]) == (na, na)
    assert bool(w_l) == warn


# ---- D4. 자동화 판정의 빈 값 토큰 (docs/02 7.4, I16) — Normalizer.automatable 하나 ↔ oracle · 지도 · MCP
AUTO_CASES = [("GUI 전용", "NA", False), ("GUI 전용", "-", False), ("GUI 전용", "해당없음", False), ("GUI 전용", "n/a", False),
              ("GUI 전용", "N/A", False), ("GUI 전용", " NA ", False), ("GUI 전용", "ＮＡ", False), ("GUI 전용", "없음", False),
              ("GUI 전용", "모름", False), ("GUI 전용", "", False), ("GUI 전용", None, False), ("GUI 전용", "COM·OLE", True),
              ("GUI 전용", "API 있음", True), ("CLI 지원", "NA", True), ("GUI+CLI", None, True), ("GUI+CLI(일부)", "NA", False)]


@pytest.mark.parametrize("op, aif, want", AUTO_CASES)
def test_automatable_parity(norm, op, aif, want):
    u = oracle.Usage("f.xlsx", "p", "p", "X-1", "가상", "가상", "상용", op, aif, "가능", None, None, None)
    assert norm.automatable(op, aif) == u.automatable == want


def test_automatable_na_in_store_and_viewer(tmp_path):
    """자동화 IF 'NA' 인 툴사용은 MCP(onto_store)·3D 지도(graph_view3d) 모두 '자동화 불가' — 전에는 둘 다 가능으로 보였다."""
    from engenius_onto.onto_store import OntologyStore

    sys.path.insert(0, str(REPO / "scripts"))
    import graph_view3d

    d = _copy(tmp_path)
    _set_row(d / STR, USAGE_SHEET, 5, {"조작 방식": "GUI 전용", "자동화 인터페이스": "NA"})        # STR-01
    out = _load(d, tmp_path)
    assert _usage(out.result, "구조/STR-01").v["automation_if"] == "NA"                        # 원문 보존 (I28)
    store = OntologyStore(run=out.out_dir)
    autos = {u["sw_id"]: u["auto"] for u in store.snapshot().usages.values()}
    assert (autos["STR-01"], autos["STR-02"]) == (False, True)
    assert {r["tool_id"]: r["auto"] for r in store.part_tools("구조")["usages"]}["STR-01"] is False
    data, _ = graph_view3d.build(out.out_dir)
    nodes = {n["sw_id"]: n["auto"] for n in data["nodes"] if n.get("type") == "u"}
    assert (nodes["STR-01"], nodes["STR-02"]) == (False, True)


# --------------------------------------------------------------------------- E. 검토표·별칭·레지스트리 (묶음 review, 2026-10-12)
from types import SimpleNamespace  # noqa: E402

from engenius_onto.config import config_where  # noqa: E402
from engenius_onto.registry import Registry, excel_explains  # noqa: E402
from engenius_onto.survey_load import apply_review, write_fix_requests, write_review  # noqa: E402
from test_loader_m31_2 import _add_usage  # noqa: E402

PARTNER = "연계SW 미해석"
H_PARTNER = "연계 SW명"
REVIEW_COLS = ["툴A_키", "툴A_표기", "툴B_키", "툴B_표기", "유사도", "사유", "판정(통합/별개)", "대표 이름(통합 시)"]
UNUSED_W = "별칭 미적용"
UNUSED_TAIL = " — 이번 적재의 툴·연계 Tool명 어디에도 없음 (툴 이름 키 규칙이 바뀌었거나 그 툴이 이번 회신에 없다; 지우기 전에 확인)"
AGG = yaml.safe_load((REPO / "tests" / "golden" / "expected.yaml").read_text(encoding="utf-8"))["aggregates"]


def _review_rows(out) -> list[dict]:
    return read_csv_rows(out.out_dir / "tool_review.csv")[0]


def _write_rows(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REVIEW_COLS)
        w.writeheader()
        w.writerows(rows)


def _cfg_copy(tmp: Path) -> Path:
    cfg = tmp / "config"
    shutil.copytree(CONFIG_DIR, cfg)
    return cfg


def _aliases_of(cfg: Path) -> dict:
    return yaml.safe_load((cfg / "tool_aliases.yaml").read_text(encoding="utf-8"))


def _tool_ids(reg: Path) -> dict[str, str]:
    return {r["key"]: r["id"] for r in read_csv_rows(reg / "tools.csv")[0]}


# ---- E1. 인명 유사 연계 조각 (docs/09 #20 (2) — 1차 구현의 회귀 테스트)
def test_person_like_partner_not_missing_tool(tmp_path):
    """인명처럼 보이는 연계 Tool명 조각은 조사 누락 후보(CQ09)·검토표 연계 행에 오르지 않는다 — 경고 1건(값 없음), 원문은 그래프에 보존 (D6, C9)."""
    d = _copy(tmp_path)
    _set_io_cells(d / STR, {("STR-01", "해석 메시"): {H_PARTNER: "가나다 책임(메일 전달)"}})
    out = _load(d, tmp_path)
    assert "가나다책임" not in out.log["unresolved_partners"]
    for name in ("tool_review.csv", "load_log.json", "diag.txt"):
        assert "가나다" not in (out.out_dir / name).read_text(encoding="utf-8-sig"), name
    assert _w(out.result, "연계 Tool명이 인명처럼 보임") == [f"연계 Tool명이 인명처럼 보임: {STR} STR-01 '해석 메시' — 조사 누락 후보에서 뺌"]
    assert "가나다 책임(메일 전달)" in out.turtle
    assert not [c for c in out.result.partner_candidates if "가나다" in c["b"]]


def test_person_like_partner_widened_patterns_never_reach_partner_missing(tmp_path):
    """#20 1-A 승인 목록의 '직급+에게·께'·'이름(직급)' (2026-10-12 검토 수리 — 전에는 빠져 '가나다선임에게메일'·'가나다' 키가 조사 누락 후보·
    검토표 연계 행에 올랐고, '별개' 판정이면 partner_missing 에 영구 기록돼 적재마다 '별칭 미적용' 으로 다시 인용됐다)."""
    d = _copy(tmp_path)
    _set_io_cells(d / STR, {("STR-01", "해석 메시"): {H_PARTNER: "가나다 선임에게 메일"},
                            ("STR-01", "구조 메시"): {H_PARTNER: "가나다(책임)"}})
    out = _load(d, tmp_path)
    assert not [k for k in out.log["unresolved_partners"] if "가나다" in k]
    rows = _review_rows(out)
    assert not [r for r in rows if "가나다" in "".join(r.values())]
    assert len(_w(out.result, "연계 Tool명이 인명처럼 보임")) == 2 and not [w for w in out.result.warnings if "가나다" in w]
    # 연계 행이 없으니 '별개' 판정으로 partner_missing 에 들어갈 길도 없다 — 검토표 전체를 별개로 판정해도 그 키는 안 생긴다
    p = out.out_dir / "tool_review.csv"
    _write_rows(p, [{**r, "판정(통합/별개)": "별개"} for r in rows if r["사유"] == PARTNER and not r["툴A_키"]])
    cfg = _cfg_copy(tmp_path)
    apply_review(p, cfg)
    assert not [k for k in _aliases_of(cfg)["partner_missing"] if "가나다" in k]
    assert "가나다 선임에게 메일" in out.turtle and "가나다(책임)" in out.turtle                    # 원문은 그래프에 (D6)


def test_review_name_cells_mask_person_like(tmp_path):
    """C5 '검토표 표기 칸도 가림' — 툴A_표기·툴B_표기(보고 이름)가 인명 유사면 PERSON_MASK (키 칸은 apply-review 가 쓰므로 그대로).
    (2026-10-12 검토 수리: 연계 행·통합 후보 행의 보고 이름이 원문으로 실렸다)"""
    d = _copy(tmp_path)
    _set_names(d / STR, {"STR-04": "가상-수명평가툴 (가나다 책임 개발)", "STR-05": "가상-수명평가툴 Pro"})
    _set_io_cells(d / STR, {("STR-01", "해석 메시"): {H_PARTNER: "가상수명평가툴프로"}})
    out = _load(d, tmp_path)
    rows = _review_rows(out)
    partner = [r for r in rows if r["사유"] == PARTNER and r["툴B_키"] == "가상수명평가툴프로"]
    assert len(partner) == 1 and partner[0]["툴A_키"] == "가상수명평가툴" and partner[0]["툴A_표기"] == PERSON_MASK
    cand = [r for r in rows if r["사유"] != PARTNER and {r["툴A_키"], r["툴B_키"]} == {"가상수명평가툴", "가상수명평가툴pro"}]
    assert len(cand) == 1 and PERSON_MASK in (cand[0]["툴A_표기"], cand[0]["툴B_표기"])
    assert "가나다" not in (out.out_dir / "tool_review.csv").read_text(encoding="utf-8-sig")
    assert not [c for c in out.log["tool_merge_candidates"] if "가나다" in json.dumps(c, ensure_ascii=False)]


def test_review_partner_hint_keys_mask_person_like(tmp_path):
    """연계 행 툴A_표기의 '비슷한 키' 힌트도 가린다 (apply-review 는 표기 칸을 읽지 않는다 — 2026-10-12 재검토 수리). '키는 공백·괄호가 빠져 인명
    패턴에 거의 안 걸린다' 는 틀렸다 — tool_key 는 괄호·버전·공백만 지워 '가나다 책임 v2' 가 '가나다책임' 으로 남고 P2·P6 패턴에 걸린다."""
    d = _copy(tmp_path)
    _set_names(d / STR, {"STR-01": "가나다 책임 v2"})
    _set_io_cells(d / STR, {("STR-02", "익형 형상"): {H_PARTNER: "가나다툴"}})
    out = _load(d, tmp_path)
    assert "가나다책임" in out.result.tools and Loader()._looks_person("가나다책임")
    rows = [r for r in _review_rows(out) if r["사유"] == PARTNER and r["툴B_키"] == "가나다툴"]
    assert len(rows) == 1 and rows[0]["툴A_키"] == ""
    assert rows[0]["툴A_표기"] == f"(기존 툴이면 툴A_키에 그 툴 키를 적는다 — 비슷한 키: {PERSON_MASK} 0.67)"
    assert "가나다책임" not in (out.out_dir / "tool_review.csv").read_text(encoding="utf-8-sig")


# ---- E2. 검토표 CSV·수정 요청표의 엑셀 수식 방지 (docs/09 #25d)
def test_review_csv_neutralizes_formula_cells(tmp_path):
    """표기 칸이 = + - @ 탭으로 시작하면 앞에 ' (엑셀이 수식으로 읽지 않게) — 키 칸은 [0-9a-z가-힣] 라 그대로. 연계 행 표기도 같다."""
    res = SimpleNamespace(
        merge_candidates=[{"a": "aa", "b": "bb", "names_a": ["=1+1"], "names_b": ["+X", "-Y"], "similarity": 0.9, "reason": "유사도"},
                          {"a": "cc", "b": "dd", "names_a": ["@RISK"], "names_b": ["\tTab"], "similarity": 0.9, "reason": "유사도"}],
        partner_candidates=[{"a": "ee", "b": "ff", "names_a": ["-Minus Tool"], "similarity": 0.9, "hints": [], "mentions": 1, "fields": ["P"]}])
    p = tmp_path / "r.csv"
    write_review(p, res)
    with p.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    assert [r[:6] for r in rows[1:]] == [["aa", "'=1+1", "bb", "'+X / -Y", "0.900", "유사도"], ["cc", "'@RISK", "dd", "'\tTab", "0.900", "유사도"],
                                         ["ee", "'-Minus Tool", "ff", "(연계 Tool명 · 언급 1회 · 파트 P)", "0.900", PARTNER]]
    write_review(p, SimpleNamespace(merge_candidates=[]))                  # 연계 행이 없는 옛 결과 객체도 쓴다
    assert p.read_text(encoding="utf-8-sig") == ",".join(REVIEW_COLS) + "\n"


def test_apply_review_strips_apostrophe_and_rejects_excel_errors(tmp_path, capsys):
    """apply-review: 키 칸 앞 ' 는 떼고 대표 이름 앞 ' 는 뒤가 수식 글자일 때만 뗀다. 엑셀 오류 값(#NAME?·#REF!·#N/A)·사람 이름처럼 보이는 대표 이름은
    '[NG] 검토표 <행>행: …' 로 멈추고 파일은 그대로 (같은 검토표의 앞 행 판정도 쓰지 않는다). 사람 이름은 오류 문구에 넣지 않는다 (절대 규칙 5)."""
    cfg = _cfg_copy(tmp_path)
    p = tmp_path / "r.csv"

    def row(a="matlab", b="matlabsimulink", verdict="통합", rep=""):
        return dict(zip(REVIEW_COLS, [a, "MATLAB", b, "MATLAB Simulink", "0.600", "포함", verdict, rep]))

    _write_rows(p, [row(a="'matlab", rep="'=Tool")])
    assert tuple(apply_review(p, cfg)) == (1, 0, 0)
    saved = _aliases_of(cfg)
    assert saved["merge_pairs"] == [["matlab", "matlabsimulink"]] and saved["labels"] == {"matlab": "=Tool"} and saved["partner_missing"] == []
    _write_rows(p, [row(rep="'Plain")])                                     # 수식 글자가 아닌 ' 는 이름의 일부
    apply_review(p, cfg)
    assert _aliases_of(cfg)["labels"] == {"matlab": "'Plain"}
    before = (cfg / "tool_aliases.yaml").read_bytes()
    for bad, match in ((row(rep="#NAME?"), r"'대표 이름\(통합 시\)' 이 엑셀 오류 값 #NAME\?"), (row(b="#REF!"), "'툴B_키' 이 엑셀 오류 값 #REF!"),
                       (row(a="'#n/a"), "'툴A_키' 이 엑셀 오류 값"), (row(rep="가나다 책임"), "대표 이름이 사람 이름처럼 보인다")):
        _write_rows(p, [row(rep="X"), bad])
        with pytest.raises(ValueError, match=match) as e:
            apply_review(p, cfg)
        assert str(e.value).startswith("검토표 3행: ") and "가나다" not in str(e.value)
        assert (cfg / "tool_aliases.yaml").read_bytes() == before
    from engenius_onto.cli import main
    assert main(["apply-review", str(p), "--config-dir", str(cfg)]) == 1
    err = capsys.readouterr().err
    assert err.startswith("[NG] 검토표 3행: 대표 이름이 사람 이름처럼 보인다") and "가나다" not in err


def test_fix_request_tool_id_not_formula(tmp_path):
    """수정 요청표(xlsx)의 Tool ID 칸도 '=' 로 시작하면 ' 를 붙여 문자열로 (openpyxl 은 '=…' 를 수식으로 저장한다)."""
    res = SimpleNamespace(issues=[{"file": "f.xlsx", "part": None, "sheet": USAGE_SHEET, "row": 5, "tool_id": "=X", "column": "Tool ID",
                                   "value": "=1+1", "kind": "선택지 밖 값", "hint": "-"}])
    path, = write_fix_requests(tmp_path / "fix", res)
    ws = openpyxl.load_workbook(path)["수정 요청"]
    assert [(c.value, c.data_type) for c in (ws["C3"], ws["E3"])] == [("'=X", "s"), ("'=1+1", "s")]


# ---- E3. 연계 Tool명 미해석 행 (docs/09 #17, I10·I35)
def test_review_lists_unresolved_partners(tmp_path):
    """합성 전체: 검토표에 사유 '연계SW 미해석' 행 = 골든 조사 누락 후보 키 (툴A 빈칸 — 유사도 0.85 미만은 힌트로만), 원문은 쓰지 않는다."""
    reg = tmp_path / "registry"
    copy_registry(REGISTRY_DIR, reg)
    out = run_load(registry_dir=reg, out_root=tmp_path / "out", shacl=False)
    rows = [r for r in _review_rows(out) if r["사유"] == PARTNER]
    assert [r["툴B_키"] for r in rows] == sorted(AGG["missing_tools"])
    assert all(r["툴A_키"] == "" and r["유사도"] == "" and r["판정(통합/별개)"] == "" for r in rows)
    by = {r["툴B_키"]: r for r in rows}
    assert by["가상미조사툴"]["툴B_표기"] == "(연계 Tool명 · 언급 2회 · 파트 2차유로(SAS)·제어)"
    assert by["가상외부해석툴"]["툴A_표기"] == "(기존 툴이면 툴A_키에 그 툴 키를 적는다 — 비슷한 키: 가상열해석 0.67 · 가상연소해석기 0.57)"
    assert "가상-미조사툴" not in (out.out_dir / "tool_review.csv").read_text(encoding="utf-8-sig")
    assert out.log["tool_keys"] == sorted(out.result.tools) and out.log["unresolved_partners"] == AGG["missing_tools"]


def test_review_partner_spelling_maps_to_existing_tool(tmp_path):
    """연계 행 판정 끝까지: 철자가 가까운 'Hypermash' 는 툴A_키 'hypermesh' 가 미리 채워지고, 한글 표기 '하이퍼메시' 는 빈칸 — 사람이 툴A_키를 적어
    통합 → merge_pairs [툴 키, 연계 키] → 재적재에서 연계가 그 툴로 해석되어 CQ09·검토표에서 빠진다. 기존 툴의 TOOL ID 는 그대로."""
    d = _copy(tmp_path)
    _set_io_cells(d / STR, {("STR-02", "블레이드 형상"): {H_PARTNER: "하이퍼메시"}, ("STR-02", "익형 형상"): {H_PARTNER: "Hypermash"}})
    reg = tmp_path / "registry"
    copy_registry(REGISTRY_DIR, reg)
    cfg = _cfg_copy(tmp_path)
    one = run_load(input_dir=d, registry_dir=reg, out_root=tmp_path / "o1", shacl=False, config_dir=cfg)
    hm_id = _tool_ids(reg)["hypermesh"]
    rows = _review_rows(one)
    part = {r["툴B_키"]: r for r in rows if r["사유"] == PARTNER}         # 구조 파일만이라 다른 파트 툴(ansysfluent 등)도 미해석으로 함께 오른다
    assert {"hypermash", "하이퍼메시"} <= set(part)
    assert (part["hypermash"]["툴A_키"], part["hypermash"]["툴A_표기"], part["hypermash"]["유사도"]) == ("hypermesh", "HyperMesh", "0.889")
    assert part["하이퍼메시"]["툴A_키"] == ""
    part["하이퍼메시"].update({"툴A_키": "hypermesh", "판정(통합/별개)": "통합"})
    part["hypermash"]["판정(통합/별개)"] = "통합"
    _write_rows(one.out_dir / "tool_review.csv", rows)
    r = apply_review(one.out_dir / "tool_review.csv", cfg)
    assert (r.merged, r.kept, r.partner_merged, r.partner_missing, r.notes) == (2, 0, 2, 0, [])
    assert _aliases_of(cfg)["merge_pairs"] == [["hypermesh", "hypermash"], ["hypermesh", "하이퍼메시"]]
    two = run_load(input_dir=d, registry_dir=reg, out_root=tmp_path / "o2", shacl=False, config_dir=cfg)
    assert not {"hypermash", "하이퍼메시"} & set(two.log["unresolved_partners"])
    xs = {x.name: x for x in two.result.ios if x.sw_id == "STR-02"}
    assert "hypermesh" in xs["블레이드 형상"].partner_tools and "hypermesh" in xs["익형 형상"].partner_tools
    assert _tool_ids(reg)["hypermesh"] == hm_id and "하이퍼메시" not in _tool_ids(reg)          # 연계 키는 레지스트리 행이 없다
    assert not {x["툴B_키"] for x in _review_rows(two) if x["사유"] == PARTNER} & {"hypermash", "하이퍼메시"}
    assert not _w(two.result, UNUSED_W)


def test_review_partner_missing_confirmed(tmp_path):
    """툴A_키 빈칸 + 별개 = 기존 툴 아님(조사 누락 확인) → partner_missing. 재적재에서 검토표에는 다시 안 오르고 CQ09 후보에는 남는다.
    그 연계 Tool명이 없는 회신을 적재하면 '별칭 미적용 … partner_missing' 경고."""
    d = _copy(tmp_path)
    _set_io_cells(d / STR, {("STR-02", "블레이드 형상"): {H_PARTNER: "가상누락툴"}})
    cfg = _cfg_copy(tmp_path)
    one = _load(d, tmp_path / "a", config_dir=cfg)
    rows = _review_rows(one)
    target = next(x for x in rows if x["툴B_키"] == "가상누락툴")
    assert target["툴A_키"] == "" and target["사유"] == PARTNER
    target["판정(통합/별개)"] = "별개"
    _write_rows(one.out_dir / "tool_review.csv", rows)
    r = apply_review(one.out_dir / "tool_review.csv", cfg)
    assert (r.merged, r.kept, r.partner_merged, r.partner_missing) == (0, 0, 0, 1)
    assert _aliases_of(cfg)["partner_missing"] == ["가상누락툴"]
    two = _load(d, tmp_path / "b", config_dir=cfg)
    assert "가상누락툴" in two.log["unresolved_partners"]
    assert "가상누락툴" not in {x["툴B_키"] for x in _review_rows(two)} and not _w(two.result, UNUSED_W)
    three = _load(_copy(tmp_path / "c"), tmp_path / "c", config_dir=cfg)
    assert _w(three.result, UNUSED_W) == [f"{UNUSED_W}: {config_where(cfg / 'tool_aliases.yaml')} partner_missing 가상누락툴{UNUSED_TAIL}"]


def test_review_partner_rejects_unknown_or_blank_tool_key(tmp_path, capsys):
    """연계 행 통합: 툴A_키가 이 실행의 툴 키가 아니거나 비면 '[NG] 검토표 <행>행' (설정 그대로). 검토표를 실행 폴더 밖으로 옮겨 load_log 가 없으면
    검사를 건너뛰고 '[주의]' — CLI 는 그 줄과 '연계 Tool명 대응' 건수를 보여 준다."""
    d = _copy(tmp_path)
    _set_io_cells(d / STR, {("STR-02", "블레이드 형상"): {H_PARTNER: "하이퍼메시"}})
    cfg = _cfg_copy(tmp_path)
    one = _load(d, tmp_path, config_dir=cfg)
    csvp = one.out_dir / "tool_review.csv"
    rows = _review_rows(one)
    target = next(x for x in rows if x["툴B_키"] == "하이퍼메시")
    assert target["사유"] == PARTNER
    n = rows.index(target) + 2
    before = (cfg / "tool_aliases.yaml").read_bytes()
    for a, match in (("nosuchtool", "툴A_키 nosuchtool 는 이 실행의 툴 키가 아니다"), ("", "통합은 툴A_키에 기존 툴 키를 적는다 — 툴B_키 하이퍼메시")):
        target.update({"툴A_키": a, "판정(통합/별개)": "통합"})
        _write_rows(csvp, rows)
        with pytest.raises(ValueError, match=match) as e:
            apply_review(csvp, cfg)
        assert str(e.value).startswith(f"검토표 {n}행: ")
        assert (cfg / "tool_aliases.yaml").read_bytes() == before
    target["툴A_키"] = "hypermesh"
    moved = tmp_path / "moved" / "r.csv"
    moved.parent.mkdir()
    _write_rows(moved, rows)
    from engenius_onto.cli import main
    assert main(["apply-review", str(moved), "--config-dir", str(cfg)]) == 0
    printed = capsys.readouterr().out
    assert "통합 1건, 별개 0건, 통합 해제 0건 (연계 Tool명 대응 1건 · 누락 확인 0건)" in printed and "  [주의] 연계SW 미해석 행의 툴A_키를 확인하지 못함" in printed
    assert _aliases_of(cfg)["merge_pairs"] == [["hypermesh", "하이퍼메시"]]


def test_partner_missing_shape_and_union(tmp_path):
    """partner_missing 은 키 목록 — 오버레이와 합집합, 목록이 아니면 ConfigError (파일·키 이름)."""
    assert merge_config("tool_aliases.yaml", {"partner_missing": ["a"]}, {"partner_missing": ["b", "a"]})["partner_missing"] == ["a", "b"]
    with pytest.raises(ConfigError, match="partner_missing"):
        merge_config("tool_aliases.yaml", {}, {"partner_missing": "가상누락툴"})
    over = _overlay(tmp_path, tool_aliases={"partner_missing": "가상누락툴"})
    with pytest.raises(ConfigError, match="partner_missing: 형식은 목록"):
        Loader(overlay_dir=over)


# ---- E4. 별칭 미적용 (docs/09 #2 (4)) · 제조사를 떼지 않은 이름 별칭 (#2 (3))
def test_unused_alias_entries_warn(tmp_path):
    """오버레이 판정 항목 가운데 이번 적재의 툴·연계 Tool명 어디에도 키가 없는 것마다 경고 한 줄 (파일·절·항목). 쓰인 항목은 경고 없이 적용."""
    over = _overlay(tmp_path, tool_aliases={"aliases": {"Nonexistent": ["Foo"], "HyperMesh": ["하이퍼메시"]},
                                            "merge_pairs": [["zzz", "yyy"], ["hypermesh", "nastran"]],
                                            "distinct": [["qqq", "rrr"], ["mechanical", "가상수명평가툴"]],
                                            "labels": {"zzz": "Z", "hypermesh": "HM"},
                                            "partner_missing": ["가상누락툴"]})
    res = _load(_copy(tmp_path), tmp_path, overlay_dir=over).result
    where = config_where(over / "tool_aliases.yaml")
    assert "real_config" in where
    assert _w(res, UNUSED_W) == [f"{UNUSED_W}: {where} {s}{UNUSED_TAIL}" for s in
                                 ("merge_pairs zzz / yyy", "distinct qqq / rrr", "labels zzz", "partner_missing 가상누락툴",
                                  "aliases HyperMesh ← 하이퍼메시", "aliases Nonexistent ← Foo")]
    assert "nastran" not in res.tools and res.tools["hypermesh"].pref_label == "HM"


def test_unused_alias_chain_through_observed_representative(tmp_path):
    """merge_pairs 사슬 [c, a]·[a, b] 에서 대표 c 만 보여도 사슬은 적용된 것 — '지워도 된다' 는 오안내를 하지 않는다."""
    over = _overlay(tmp_path, tool_aliases={"merge_pairs": [["hypermesh", "gonetool"], ["gonetool", "gonetool2"]]})
    res = _load(_copy(tmp_path), tmp_path, overlay_dir=over).result
    assert not _w(res, UNUSED_W)


def test_public_alias_dictionary_not_checked(tmp_path):
    """저장소 설정 폴더의 aliases(공개 별칭 사전 — 쓰지 않는 표기가 있는 게 정상)는 검사하지 않는다. 그 폴더의 판정 항목(labels 등)은 검사."""
    res = _load(_copy(tmp_path / "a"), tmp_path / "a").result
    assert not _w(res, UNUSED_W)
    cfg = _cfg_copy(tmp_path)
    data = _aliases_of(cfg)
    data["aliases"]["CATIA V5"] = ["카티아"]
    data["labels"] = {"zzz": "Z"}
    (cfg / "tool_aliases.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    res = _load(_copy(tmp_path / "b"), tmp_path / "b", config_dir=cfg).result
    assert _w(res, UNUSED_W) == [f"{UNUSED_W}: {config_where(cfg / 'tool_aliases.yaml')} labels zzz{UNUSED_TAIL}"]


def test_unused_alias_masks_person_like_key(tmp_path):
    """경고에 옮기는 항목이 인명 유사면 가린다 (Loader._q)."""
    over = _overlay(tmp_path, tool_aliases={"labels": {"가나다책임": "X"}, "aliases": {"가나다 책임 툴": ["가나다 선임 툴"]}})
    w = _w(_load(_copy(tmp_path), tmp_path, overlay_dir=over).result, UNUSED_W)
    assert len(w) == 2 and all(PERSON_MASK in x for x in w) and not any("가나다" in x for x in w)


def test_name_alias_with_vendor_prefixed_variant_applies_to_usage(tmp_path):
    """#2 (3): 이름 별칭 'HyperMesh: [Altair HyperMesh Pro]' 의 변형 키(altairhypermeshpro)는 제조사를 떼지 않고 만든다 — 툴사용 키(제조사 뗀
    hypermeshpro)로 안 맞으면 제조사를 떼지 않은 이름 키로도 찾아 그 툴로 (전에는 별도 툴 + 통합 후보로 남았다). 기존 툴의 TOOL ID 는 그대로."""
    d = _copy(tmp_path)
    _add_usage(d / STR, "STR-90", "Altair HyperMesh Pro", "Altair")
    plain = run_load(input_dir=d, registry_dir=tmp_path / "reg0", out_root=tmp_path / "o0", shacl=False).result
    assert "hypermeshpro" in plain.tools and ("hypermesh", "hypermeshpro") in {(c["a"], c["b"]) for c in plain.merge_candidates}
    reg = tmp_path / "registry"
    copy_registry(REGISTRY_DIR, reg)
    hm_id = _tool_ids(reg)["hypermesh"]
    over = _overlay(tmp_path, tool_aliases={"aliases": {"HyperMesh": ["Altair HyperMesh Pro"]}})
    res = run_load(input_dir=d, registry_dir=reg, out_root=tmp_path / "o1", shacl=False, overlay_dir=over).result
    assert "hypermeshpro" not in res.tools and "Altair HyperMesh Pro" in res.tools["hypermesh"].names
    assert _tool_ids(reg)["hypermesh"] == hm_id and "hypermeshpro" not in _tool_ids(reg)
    assert not _w(res, UNUSED_W) and not [c for c in res.merge_candidates if "hypermeshpro" in (c["a"], c["b"])]


# ---- E5. 레지스트리 엑셀 손상 (docs/09 #15 (4), Leo 결정 2026-10-12)
def _set_usage_key(reg: Path, old: str, new: str) -> str:
    """레지스트리 usages.csv 의 source_key 를 바꾼다 (엑셀이 바꿔 저장한 모양 흉내) → 그 행의 USE ID."""
    rows = read_csv_rows(reg / "usages.csv")[0]
    hit = [r for r in rows if r["source_key"] == old]
    assert len(hit) == 1, old
    hit[0]["source_key"] = new
    with (reg / "usages.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return hit[0]["id"]


RESTORED_TAIL = (" — 엑셀이 바꾼 Tool ID 칸('3-1'→'03월 01일', '01'→'1')을 라벨 끝 값으로 되살림, 이번 적재가 고쳐 저장한다 "
                 "(레지스트리 CSV 는 엑셀로 저장하지 않는다 — docs/09 #15)")


def test_registry_excel_damage_restored(tmp_path):
    """엑셀이 바꾼 Tool ID('3-1'→'03월 01일', '0012'→'12')는 라벨 끝 값으로 되살린다 — USE·IO ID 그대로, 새 발급 0, 경고 '레지스트리 엑셀 손상 복원'.
    (되살리지 않으면 그 툴사용·입출력이 새 ID 를 받고 옛 ID 는 폐기된다 — 경고가 적재 뒤에야 보여 늦다.)"""
    d = _copy(tmp_path)
    _rename_ids(d / STR, {"STR-01": "3-1", "STR-02": "0012"})
    reg = tmp_path / "registry"
    one = run_load(input_dir=d, registry_dir=reg, out_root=tmp_path / "o1", shacl=False)
    ids = {u.key: u.node_id for u in one.result.usages}
    ios = sorted(x.node_id for x in one.result.ios)
    u1, u2 = _set_usage_key(reg, "3-1", "03월 01일"), _set_usage_key(reg, "0012", "12")
    assert Registry(reg).notices == [f"레지스트리 엑셀 손상 복원: usages.csv 2행 ({u1}, {u2}){RESTORED_TAIL}"]
    two = run_load(input_dir=d, registry_dir=reg, out_root=tmp_path / "o2", shacl=False)
    assert {u.key: u.node_id for u in two.result.usages} == ids and sorted(x.node_id for x in two.result.ios) == ios
    assert two.log["registry"]["transitions"]["usage"] == {"created": 0, "revived": 0}
    assert _w(two.result, "레지스트리 엑셀 손상") == [f"레지스트리 엑셀 손상 복원: usages.csv 2행 ({u1}, {u2}){RESTORED_TAIL}"]
    assert {"3-1", "0012"} <= {r["source_key"] for r in _registry_rows(reg)} and Registry(reg).notices == []    # 저장할 때 고쳐 썼다


def test_registry_excel_damage_unexplained_warns(tmp_path):
    """라벨로 설명되지 않는 키 불일치(손 편집 등)는 되살리지 않고 경고만 — ID 만 인용 (값 없음). 그대로 적재하면 경고대로 새 USE ID."""
    reg = tmp_path / "registry"
    copy_registry(REGISTRY_DIR, reg)
    use = _set_usage_key(reg, "STR-01", "03월 01일")
    rg = Registry(reg)
    assert len(rg.notices) == 1 and rg.notices[0].startswith(f"레지스트리 엑셀 손상 의심: usages.csv 1행 ({use}) — Tool ID 칸이 라벨 끝과 다르다")
    assert "03월" not in rg.notices[0] and rg.id_of("usage", ("FLD-002", "03월 01일")) == use
    out = run_load(registry_dir=reg, out_root=tmp_path / "o", shacl=False)
    assert rg.notices[0] in out.result.warnings
    assert out.log["registry"]["transitions"]["usage"]["created"] == 1


def test_registry_damage_unit(tmp_path):
    """복원 (앞 0·소수 끝 0·영문 월 약어 날짜) · 같은 (분야, 원래 값) 행이 이미 있으면 의심만 · 구분 꼬리(I36) 라벨은 정상 · 설명 안 되면 의심 ·
    분야·툴·분류 키는 엑셀 날짜 모양이면 의심."""
    reg = tmp_path / "reg"
    reg.mkdir()

    def write(name: str, cols: list[str], rows: list[list[str]]) -> None:
        with (reg / name).open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(cols)
            w.writerows(rows)

    write("usages.csv", ["id", "field_id", "source_key", "label", "status", "merged_into"], [
        ["USE-000001", "FLD-001", "1", "가상 01", "활성", ""],
        ["USE-000002", "FLD-001", "1.5", "가상 1.50", "활성", ""],
        ["USE-000003", "FLD-001", "1-Mar", "가상 파트 MAR-1", "활성", ""],
        ["USE-000004", "FLD-001", "03월 01일", "가상 3-1", "폐기", ""],
        ["USE-000005", "FLD-001", "3-1", "가상 3-1", "활성", ""],
        ["USE-000006", "FLD-001", "STR-01@MD", "가상 STR-01 (MD)", "활성", ""],
        ["USE-000007", "FLD-001", "X-9", "가상 X-1", "활성", ""]])
    write("categories.csv", ["id", "key", "label", "status", "merged_into"], [["CAT-001", "2026-03-01", "2026-03-01", "활성", ""],
                                                                             ["CAT-002", "해석-결과", "해석-결과", "활성", ""]])
    rg = Registry(reg)
    assert [r["source_key"] for r in rg.rows("usage")] == ["01", "1.50", "MAR-1", "03월 01일", "3-1", "STR-01@MD", "X-9"]
    assert [n.split(" — ")[0] for n in rg.notices] == ["레지스트리 엑셀 손상 복원: usages.csv 3행 (USE-000001, USE-000002, USE-000003)",
                                                      "레지스트리 엑셀 손상 의심: usages.csv 2행 (USE-000004, USE-000007)",
                                                      "레지스트리 엑셀 손상 의심: categories.csv 1행 (CAT-001)"]


@pytest.mark.parametrize("orig, cur, want", [
    ("01", "1", True), ("0012", "12", True), ("12", "12", False), ("1.50", "1.5", True), ("10.0", "10", True), ("1.5", "1.5", False),
    ("3-1", "03월 01일", True), ("3-1", "3월 1일", True), ("3/1", "1-Mar", True), ("12-31", "2026-12-31", True), ("3-1", "2026-03-01 00:00:00", True),
    ("3-1", "3/1/2026", True), ("MAR-1", "01-Mar", True), ("mar-1", "03월 01일", True), ("2-30", "02월 30일", False), ("STR-01", "03월 01일", False),
    ("3-1", "03월 02일", False), ("13-1", "01월 13일", False), ("A-1", "1", False), ("", "1", False)])
def test_excel_explains(orig, cur, want):
    assert excel_explains(orig, cur) is want


def test_committed_registry_has_no_excel_damage():
    assert Registry(REGISTRY_DIR).notices == []


BLANK_STATUS_TAIL = " — 활성으로 봄 (이번 적재에 없으면 폐기로 바뀐다; 손 편집으로 열이 빠졌는지 확인 — 저장할 때 상태를 채워 쓴다)"


def test_registry_row_with_missing_columns_loads(tmp_path):
    """메모장 손 편집으로 꼬리 쉼표가 빠진 행('USE-000999,FLD-001,SAS-99') — csv 가 빠진 칸을 None 으로 채워 엑셀 손상 검사가 traceback 으로
    적재를 멈췄다 (2026-10-12 검토 수리, 430b398 회귀). 빈칸으로 읽고 적재는 rc 0, 저장할 때 열을 채워 쓴다. 빈 상태는 활성으로 보고 알림 —
    이번 적재에 없는 행이라 폐기로 저장된다 (2026-10-12 재검토 수리: 전에는 상태 '' 로 남아 되살림·폐기 판정 어디에도 걸리지 않았다)."""
    reg = copy_registry(REGISTRY_DIR, tmp_path / "registry")
    with (reg / "usages.csv").open("a", encoding="utf-8", newline="") as f:
        f.write("USE-000999,FLD-001,SAS-99\n")
    rg = Registry(reg)
    assert rg.notices == [f"레지스트리 상태 칸 빈 행: usages.csv 1행 (USE-000999){BLANK_STATUS_TAIL}"]
    assert rg.id_of("usage", ("FLD-001", "SAS-99")) == "USE-000999"
    rc = cli.main(["load", "--input", str(_copy(tmp_path)), "--registry", str(reg), "--out", str(tmp_path / "out"), "--no-shacl"])
    assert rc == 0
    assert "USE-000999,FLD-001,SAS-99,,폐기," in (reg / "usages.csv").read_text(encoding="utf-8-sig").splitlines()
    assert Registry(reg).notices == []


def test_registry_blank_status_tool_not_a_ghost(tmp_path):
    """tools.csv 행의 상태 칸이 빠지면('TOOL-000001,catia,CATIA V5') — 활성으로 보고 알림, 이번 적재에 없으면 폐기 (그래프에 eg:status 폐기).
    전에는 상태 '' 로 남아 폐기되지 않고, 그래프에 상태 없는 툴(= ifabsent 활성)로 써져 MCP·3D 지도에 활성 유령으로 나왔다 (2026-10-12 재검토 수리)."""
    reg = copy_registry(REGISTRY_DIR, tmp_path / "registry")
    path = reg / "tools.csv"
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    assert lines[1] == "TOOL-000001,catia,CATIA V5,활성,"
    path.write_text("\n".join([lines[0], "TOOL-000001,catia,CATIA V5", *lines[2:]]) + "\n", encoding="utf-8-sig")
    out = run_load(input_dir=_copy(tmp_path), registry_dir=reg, out_root=tmp_path / "out", shacl=False)   # 구조 파일만 — CATIA 없음
    assert f"레지스트리 상태 칸 빈 행: tools.csv 1행 (TOOL-000001){BLANK_STATUS_TAIL}" in out.result.warnings
    row = next(r for r in read_csv_rows(path)[0] if r["id"] == "TOOL-000001")
    assert row["status"] == "폐기"
    counts = out.log["registry"]["tool"]
    assert sum(counts.values()) == len(read_csv_rows(path)[0])                              # 세 상태 어디에도 안 세이는 행이 없다
    g = Graph().parse(data=out.turtle, format="turtle")
    t = SchemaTerms.load()
    tool = next(s for s in g.subjects(RDF.type, t.classes["Tool"]) if str(s).endswith("TOOL-000001"))
    assert [str(o) for o in g.objects(tool, t.props["status"])] == ["폐기"]


EMPTY_ROW_TAIL = " — ID·키 칸이 빈 줄 (엑셀·메모장에서 내용만 지운 줄), 저장할 때 뺀다"


def test_registry_empty_rows_dropped_and_new_id_issued(tmp_path):
    """엑셀·메모장에서 내용만 지운 줄(',,,,')·공백 한 줄·3f668cd 가 그런 줄을 저장한 ',,,폐기,' — 전에는 새 ID 발급(assign 의 번호 계산)이
    IndexError traceback 으로 멈추고, 새 ID 가 없는 적재는 그래프에 빈 IRI 툴(egid: a eg:Tool)을 만들고 그 줄을 ',,,폐기,' 로 굳혔다
    (2026-10-12 재검토 수리). 이제 읽을 때 버리고 알림(줄 번호만), 저장할 때 뺀다. 새 툴은 다음 번호를 받는다."""
    reg = copy_registry(REGISTRY_DIR, tmp_path / "registry")
    n_tools = len(read_csv_rows(reg / "tools.csv")[0])
    with (reg / "tools.csv").open("a", encoding="utf-8", newline="") as f:
        f.write(",,,,\n \n,,,폐기,\n")
    with (reg / "usages.csv").open("a", encoding="utf-8", newline="") as f:
        f.write(",,,,,\n")
    n_use = len(read_csv_rows(reg / "usages.csv")[0])
    rg = Registry(reg)
    assert rg.notices == [f"레지스트리 빈 행 무시: tools.csv 3행 ({n_tools + 2}줄, {n_tools + 3}줄, {n_tools + 4}줄){EMPTY_ROW_TAIL}",
                          f"레지스트리 빈 행 무시: usages.csv 1행 ({n_use + 1}줄){EMPTY_ROW_TAIL}"]
    assert len(rg.rows("tool")) == n_tools and all(r["id"] for r in rg.rows("tool"))
    d = _copy(tmp_path)
    _set_names(d / STR, {"STR-01": "가상 새툴 QWZ"})                                            # 새 TOOL ID 가 필요한 적재
    rc = cli.main(["load", "--input", str(d), "--registry", str(reg), "--out", str(tmp_path / "out"), "--no-shacl"])
    assert rc == 0
    run = next((tmp_path / "out").iterdir())
    log = json.loads((run / "load_log.json").read_text(encoding="utf-8"))
    assert set(rg.notices) <= set(log["warnings"]) and log["registry"]["transitions"]["tool"]["created"] == 1
    rows = read_csv_rows(reg / "tools.csv")[0]
    assert len(rows) == n_tools + 1 and all(re.fullmatch(r"TOOL-\d{6}", r["id"]) for r in rows)
    assert next(r for r in rows if r["label"] == "가상 새툴 QWZ")["id"] == f"TOOL-{n_tools + 1:06d}"
    assert sum(log["registry"]["tool"].values()) == len(rows)
    assert all(r["id"] for r in read_csv_rows(reg / "usages.csv")[0])
    g = Graph().parse(data=(run / "survey.ttl").read_text(encoding="utf-8"), format="turtle")
    assert not [s for s in set(g.subjects()) if str(s).endswith("/id/")]                       # 빈 IRI 툴 없음
    assert Registry(reg).notices == []


def test_registry_keyed_row_without_id_stops_load(tmp_path, capsys):
    """키는 있는데 ID 칸이 비었거나 모양이 다른 줄 (메모장에서 ID 를 지움·'TOOL-00000x') — 어느 ID 인지 알 수 없어 적재를 멈춘다
    (rc 2, traceback 없이 한 줄 — 줄 번호만, 값 없음). 이대로 적재하면 그 키가 새 ID 를 받는다. 레지스트리·실행 폴더는 손대지 않는다."""
    reg = copy_registry(REGISTRY_DIR, tmp_path / "registry")
    path = reg / "tools.csv"
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    assert lines[1].startswith("TOOL-000001,catia,") and lines[3].startswith("TOOL-000003,")
    lines[1] = "," + lines[1].split(",", 1)[1]
    lines[3] = "TOOL-00000x," + lines[3].split(",", 1)[1]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    before = {p.name: p.read_bytes() for p in reg.glob("*.csv")}
    with pytest.raises(RegistryFormatError) as e:
        Registry(reg)
    assert "모양이 다른 행: 2행 (tools.csv 2줄, tools.csv 4줄) — " in str(e.value) and "catia" not in str(e.value)
    rc = cli.main(["load", "--input", str(_copy(tmp_path)), "--registry", str(reg), "--out", str(tmp_path / "out"), "--no-shacl"])
    err = capsys.readouterr().err
    assert rc == 2 and err.startswith("[NG] 레지스트리 오류: 레지스트리 ID 칸이 비었거나 모양이 다른 행: 2행 (tools.csv 2줄, tools.csv 4줄)")
    assert "Traceback" not in err and {p.name: p.read_bytes() for p in reg.glob("*.csv")} == before
    assert not (reg / LOCK_NAME).exists() and not [p for p in (tmp_path / "out").glob("*") if p.is_dir()]


def test_registry_status_whitespace_and_typo(tmp_path):
    """상태 칸의 꼬리 공백('활성 ')은 떼고, 세 상태 밖의 값('페기')은 활성으로 보고 알림 — 전에는 빈칸만 잡아 그런 행이 폐기·되살림·상태 건수
    어디에도 걸리지 않았다 (2026-10-12 재검토 수리). 구조 파일만 적재 — 둘 다 이번 적재에 없어 폐기로 저장, 상태 건수 합 = 행 수."""
    reg = copy_registry(REGISTRY_DIR, tmp_path / "registry")
    path = reg / "tools.csv"
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    assert lines[1] == "TOOL-000001,catia,CATIA V5,활성," and lines[3].startswith("TOOL-000003,") and lines[3].endswith(",활성,")
    lines[1] = "TOOL-000001,catia,CATIA V5,활성 ,"
    lines[3] = lines[3][: -len("활성,")] + "페기,"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    rg = Registry(reg)
    assert rg.notices == ["레지스트리 상태 칸 값 이상: tools.csv 1행 (TOOL-000003) — 활성·통합됨·폐기 밖의 값이라 활성으로 봄 "
                          "(이번 적재에 없으면 폐기, 다른 툴로 통합된 키면 통합됨으로 바뀐다 — 저장할 때 상태를 고쳐 쓴다)"]
    assert "페기" not in rg.notices[0].split(" — ")[0]                                          # 값은 인용하지 않는다 (ID 만)
    assert {r["id"]: r["status"] for r in rg.rows("tool")}["TOOL-000001"] == "활성"
    out = run_load(input_dir=_copy(tmp_path), registry_dir=reg, out_root=tmp_path / "out", shacl=False)   # 구조 파일만 — CATIA·Fluent 없음
    rows = read_csv_rows(path)[0]
    status = {r["id"]: r["status"] for r in rows}
    assert status["TOOL-000001"] == status["TOOL-000003"] == "폐기"
    assert sum(out.log["registry"]["tool"].values()) == len(rows) and {r["status"] for r in rows} <= {"활성", "통합됨", "폐기"}
    assert Registry(reg).notices == []                                                       # 저장할 때 고쳐 썼다


def test_copy_registry_skips_lock_and_temp_files(tmp_path):
    """시험·사본용 레지스트리 복사는 잠금·임시 파일을 빼고 CSV 만 (2026-10-12 검토 수리: 강제 종료로 합성 레지스트리에 남은 잠금이 사본마다
    따라가 시험 수십 건이 임시 폴더의 잠금을 가리키며 실패했다). conftest 는 합성 레지스트리의 그 잠금을 시작 때 한 줄로 알리고 멈춘다."""
    import conftest

    src = copy_registry(REGISTRY_DIR, tmp_path / "src")
    for name in (LOCK_NAME, "usages.csv.tmp", ".write_test"):
        (src / name).write_text("pid=1 started=x\n", encoding="utf-8")
    dst = copy_registry(src, tmp_path / "dst")
    assert sorted(p.name for p in dst.iterdir()) == sorted(p.name for p in REGISTRY_DIR.glob("*.csv"))
    out = run_load(input_dir=_copy(tmp_path), registry_dir=dst, out_root=tmp_path / "out", shacl=False)
    assert len(out.result.usages) == 5
    assert conftest.SYNTH_LOCK == REGISTRY_DIR / LOCK_NAME and not conftest.SYNTH_LOCK.exists()


# --------------------------------------------------------------------------- F. 식별자·실행 안전 (묶음 ids, 2026-10-12)
# #25b 파트 약칭 개명(parts.yaml renamed_from) · 정식 이름 변경 회귀 · '파트 신규·폐기 동시' 휴리스틱 · 동시 적재 잠금 · 같은 초 두 실행 (docs/09 7장)
from engenius_onto import cli  # noqa: E402
from engenius_onto.rdf_writer import SurveyWriter  # noqa: E402
from engenius_onto.registry import LOCK_NAME, RegistryBusyError, RegistryFormatError  # noqa: E402

STR_NEW = "SW조사_STR_20260925.xlsx"
RENAMED_W = "파트 약칭 개명 반영"
HELD_W = "파트 약칭 개명 보류"
TURNOVER_W = "파트 신규·폐기 동시"
OLD_NAME_W = "옛 약칭 파일명"
F_NOW = dt.datetime(2026, 10, 12, 9, 0, 0)


def _parts_cfg(tmp: Path, name: str, parts: dict, drop_synthetic: tuple = (), bundles: dict | None = None) -> Path:
    """저장소 config 사본 — parts.yaml 의 parts 에 항목을 더하고 synthetic_parts 에서 약칭을 뺀다 (합성 약칭 '구조' 를 STR 로 바꾸는 시험)."""
    cfg = tmp / f"cfg_{name}"
    shutil.copytree(CONFIG_DIR, cfg)
    p = yaml.safe_load((cfg / "parts.yaml").read_text(encoding="utf-8"))
    p["parts"].update(parts)
    p["synthetic_parts"] = [x for x in p["synthetic_parts"] if x not in drop_synthetic]
    if bundles is not None:
        p["file_bundles"] = bundles
    (cfg / "parts.yaml").write_text(yaml.safe_dump(p, allow_unicode=True), encoding="utf-8")
    return cfg


STR_PART = {"name": "구조 파트", "domains": ["구조"], "status": "확정"}


def _rename_cfg(tmp: Path, name: str = "rename") -> Path:
    return _parts_cfg(tmp, name, {"STR": {**STR_PART, "renamed_from": ["구조"]}}, drop_synthetic=("구조",))


def _survey(tmp: Path, name: str, files: dict[str, str]) -> Path:
    """합성 파일 복사 — files: {놓을 이름: 원본 이름}."""
    d = tmp / name
    for dst, src in files.items():
        _place(d, src, dst)
    return d


def _fields(reg: Path) -> dict[str, dict]:
    return {r["key"]: r for r in read_csv_rows(reg / "fields.csv")[0]}


def _ids_of(out, part: str) -> tuple[dict[str, str], set[str]]:
    """그 파트의 {Tool ID: USE ID} · 그 파트 툴사용이 가진 입출력 ID 집합 (고아 포함 — 파일 약칭으로)."""
    use = {u.sw_id: u.node_id for u in out.result.usages if u.field == part}
    ios = {x.node_id for x in out.result.ios if (x.owner.field if x.owner else x.file_field) == part}
    return use, ios


def _wt(out, prefix: str) -> list[str]:
    return [w for w in out.result.warnings if w.startswith(prefix)]


def _base_two(tmp: Path):
    """기준 적재 — 구조·터빈 두 파일, 빈 레지스트리."""
    reg = tmp / "registry"
    out = run_load(input_dir=_survey(tmp, "s0", {STR: STR, TURB: TURB}), registry_dir=reg, out_root=tmp / "o0", shacl=False,
                   now=F_NOW)
    return reg, out


# ---- F1. 정식 이름 변경 (parts.yaml name) — 이미 라벨만 바뀐다 (회귀 잠금)
def test_part_name_change_keeps_ids(tmp_path):
    reg, base = _base_two(tmp_path)
    fld = _fields(reg)["구조"]["id"]
    use0, io0 = _ids_of(base, "구조")
    survey = _survey(tmp_path, "s1", {STR: STR, TURB: TURB})
    for i, name in enumerate(("구조해석 파트", "구조해석2 파트"), start=1):
        cfg = _parts_cfg(tmp_path, f"n{i}", {"구조": {"name": name, "domains": ["구조"], "status": "확정"}})
        out = run_load(input_dir=survey, registry_dir=reg, out_root=tmp_path / f"o{i}", shacl=False, config_dir=cfg)
        row = _fields(reg)["구조"]
        assert row["id"] == fld and row["label"] == f"{name} (구조)" and row["status"] == "활성"
        assert f'"{name} (구조)"@ko' in out.turtle
        assert _ids_of(out, "구조") == (use0, io0)
        assert not _wt(out, TURNOVER_W) and not _wt(out, RENAMED_W)


# ---- F2. 약칭 개명 (renamed_from) — 옛 약칭 파일명 → 새 약칭 파일명, ID 유지
def test_part_code_rename_keeps_ids(tmp_path):
    reg, base = _base_two(tmp_path)
    fld = _fields(reg)["구조"]["id"]
    use0, io0 = _ids_of(base, "구조")
    assert len(use0) == 5 and io0
    cfg = _rename_cfg(tmp_path)
    # ① 설정만 먼저 바꾸고 파일명은 옛 약칭 그대로 — 새 약칭으로 읽고 '옛 약칭 파일명' 경고, 레지스트리 키는 STR 로
    out1 = run_load(input_dir=_survey(tmp_path, "s1", {STR: STR, TURB: TURB}), registry_dir=reg, out_root=tmp_path / "o1",
                    shacl=False, config_dir=cfg)
    assert _wt(out1, RENAMED_W) == [f"파트 약칭 개명 반영: 구조 → STR ({fld} 유지 — 툴사용·입출력 ID 도 유지)"]
    assert _wt(out1, OLD_NAME_W) == [f"옛 약칭 파일명: {STR} — 약칭 '구조' → 'STR' 로 읽음 "
                                     "(config/parts.yaml renamed_from — 다음 회신부터 새 약칭 파일명으로)"]
    assert {u.field for u in out1.result.usages if u.file == STR} == {"STR"}
    assert _ids_of(out1, "STR") == (use0, io0)
    rows = _fields(reg)
    assert "구조" not in rows and rows["STR"]["id"] == fld and rows["STR"]["label"] == "구조 파트 (STR)" and rows["STR"]["status"] == "활성"
    assert "구조 파트 (STR)" in out1.turtle
    assert not _wt(out1, TURNOVER_W)
    assert out1.log["registry"]["transitions"]["field"] == {"created": 0, "revived": 0}
    # ② 새 약칭 파일명으로 다시 — 경고 없이 같은 ID (멱등)
    out2 = run_load(input_dir=_survey(tmp_path, "s2", {STR_NEW: STR, TURB: TURB}), registry_dir=reg, out_root=tmp_path / "o2",
                    shacl=False, config_dir=cfg)
    assert not _wt(out2, RENAMED_W) and not _wt(out2, OLD_NAME_W) and not _wt(out2, TURNOVER_W) and not _wt(out2, HELD_W)
    assert _ids_of(out2, "STR") == (use0, io0)
    assert _fields(reg)["STR"]["id"] == fld
    assert {r["status"] for r in read_csv_rows(reg / "usages.csv")[0]} == {"활성"}       # 옛 툴사용이 폐기되지 않았다


def test_part_code_rename_supersedes_old_file(tmp_path):
    """I31·I33: 옛 약칭 파일과 새 약칭 파일이 함께 있으면 같은 파트의 재발송 — 최신(STR) 하나만 (고치기 전: 둘 다 적재돼 툴사용 34 → 39)."""
    survey = tmp_path / "survey"
    shutil.copytree(SURVEY_DIR, survey)
    _place(survey, STR, STR_NEW)
    reg = tmp_path / "registry"
    copy_registry(REGISTRY_DIR, reg)
    out = run_load(input_dir=survey, registry_dir=reg, out_root=tmp_path / "out", shacl=False, config_dir=_rename_cfg(tmp_path))
    assert out.log["counts"]["usages"] == 34
    assert _wt(out, "재발송으로 대체: SW조사_구조") == [f"재발송으로 대체: {STR} → {STR_NEW} (적재 안 함) (내용 같음)"]
    assert not _wt(out, OLD_NAME_W)                                   # 대체된 옛 약칭 파일은 '옛 약칭 파일명' 경고 대상이 아니다
    assert [f.name for f in out.result.loaded_files if f.field == "STR"] == [STR_NEW]
    committed = {r["key"]: r["id"] for r in read_csv_rows(REGISTRY_DIR / "fields.csv")[0]}
    assert _fields(reg)["STR"]["id"] == committed["구조"]
    assert len(_wt(out, RENAMED_W)) == 1 and not _wt(out, TURNOVER_W)


@pytest.mark.parametrize("old_name, new_name, renamed_from", [
    ("SW조사_구조_20261012.xlsx", "SW조사_STR_20261012.xlsx", "구조"),        # 한글 옛 약칭 > ASCII 새 약칭 — 옛 파일이 이겼다
    ("Tool조사_구조_20261012.xlsx", "Tool조사_STR_20261012.xlsx", "구조"),    # v1.1 정식 접두
    ("Tool조사_구조_20261012.xlsx", "SW조사_STR_20261012.xlsx", "구조"),      # 접두가 달라도 ('Tool' > 'SW')
    ("Tool조사_TMP1_20261012.xlsx", "Tool조사_STR_20261012.xlsx", "TMP1"),    # ASCII 끼리 ('TMP1' > 'STR')
    # 사본 번호는 꼬리를 뗀 이름이 같은 사본끼리만 — 옛 약칭 첨부를 두 번 받은 '(1)' 이 새 약칭 파일을 이기지 않는다 (2026-10-12 재검토 수리)
    ("SW조사_구조_20261012 (1).xlsx", "SW조사_STR_20261012.xlsx", "구조"),
    ("SW조사_구조_20261012.xlsx", "SW조사_STR_20261012 (1).xlsx", "구조"),
    ("SW조사_구조_20261012 (2).xlsx", "SW조사_STR_20261012 (1).xlsx", "구조"),
], ids=["sw-hangul", "tool-hangul", "mixed-prefix", "ascii", "old-copy", "new-copy", "both-copies"])
def test_part_code_rename_same_date_new_name_wins(tmp_path, old_name, new_name, renamed_from):
    """I33: 옛·새 약칭 파일의 날짜가 같으면 사본 번호와 무관하게 새 약칭 파일이 최신 — renamed_from 은 옛 약칭이 먼저 쓰였다는 뜻이라 같은 날 새 이름으로
    다시 보낸 파일이 나중 것이다 (2026-10-12 검토 수리: 파일명 사전순으로 갈려 고친 새 파일이 '재발송으로 대체' 로 버려지고, 남은 옛 파일에
    '다음 회신부터 새 약칭 파일명으로' 경고가 붙었다; 재검토 수리: 비교 키가 (날짜, 사본 번호, …) 라 옛 약칭 '(1)' 사본이 같은 증상을 냈다)."""
    cfg = _parts_cfg(tmp_path, "tie", {"STR": {**STR_PART, "renamed_from": [renamed_from]}},
                     drop_synthetic=(renamed_from,) if renamed_from == "구조" else ())
    survey = _survey(tmp_path, "s", {old_name: STR, new_name: STR})
    _set_names(survey / new_name, {"STR-01": "가상-고친툴"})
    out = run_load(input_dir=survey, registry_dir=tmp_path / "registry", out_root=tmp_path / "out", shacl=False, config_dir=cfg)
    assert [f.name for f in out.result.loaded_files] == [new_name]
    assert _wt(out, "재발송으로 대체") == [f"재발송으로 대체: {old_name} → {new_name} (적재 안 함)"]
    assert not _wt(out, OLD_NAME_W)
    assert "가상-고친툴" in out.turtle and {u.field for u in out.result.usages} == {"STR"}


def test_copy_number_orders_only_same_name_copies(tmp_path):
    """I33: 사본 번호는 꼬리를 뗀 이름이 같은 파일끼리만 순서를 정한다 — 같은 날짜 v1.0 'SW조사_…(2)' 와 v1.1 'Tool조사_…' 는 사본 번호가 아니라
    이름(꼬리 뗀)으로 갈리고(사본 규칙 전과 같다), 같은 이름의 사본끼리는 번호가 큰 쪽 (2026-10-12 재검토 수리)."""
    survey = tmp_path / "survey"
    _place(survey, STR, "SW조사_구조_20260924 (2).xlsx")
    _set_names(_place(survey, STR, "Tool조사_구조_20260924.xlsx"), {"STR-01": "가상-v11툴"})
    _set_names(_place(survey, STR, "Tool조사_구조_20260924 (1).xlsx"), {"STR-01": "가상-v11사본툴"})
    out = _load(survey, tmp_path)
    assert [f.name for f in out.result.loaded_files] == ["Tool조사_구조_20260924 (1).xlsx"]
    assert "가상-v11사본툴" in out.turtle and "가상-v11툴" not in out.turtle


def test_part_code_rename_keeps_generic_tool_ids(tmp_path):
    """I34·#25b: 범용 이름 툴의 행별 키 '미상:<파트>/<Tool ID>' 는 약칭을 품고 있어 개명 때 툴 표 키 접두도 바꾼다 — TOOL ID 유지, 새 툴 0
    (2026-10-12 검토 수리: '미상:구조/STR-01' → '미상:STR/STR-01' 로 새 TOOL 이 발급되고 옛 것이 폐기됐다). 옛·새 약칭 파일명 모두."""
    reg = tmp_path / "registry"
    s0 = _survey(tmp_path, "s0", {STR: STR, TURB: TURB})
    _set_names(s0 / STR, {"STR-01": "자체개발"})
    base = run_load(input_dir=s0, registry_dir=reg, out_root=tmp_path / "o0", shacl=False, now=F_NOW)
    tool0 = _tool_ids(reg)["미상:구조/STR-01"]
    others = {k: v for k, v in _tool_ids(reg).items() if not k.startswith("미상:")}
    use0, io0 = _ids_of(base, "구조")
    cfg = _rename_cfg(tmp_path)
    out1 = run_load(input_dir=s0, registry_dir=reg, out_root=tmp_path / "o1", shacl=False, config_dir=cfg)
    ids = _tool_ids(reg)
    assert ids["미상:STR/STR-01"] == tool0 and "미상:구조/STR-01" not in ids
    assert {k: v for k, v in ids.items() if not k.startswith("미상:")} == others
    assert out1.log["registry"]["transitions"]["tool"] == {"created": 0, "revived": 0}
    assert {r["status"] for r in read_csv_rows(reg / "tools.csv")[0] if r["id"] == tool0} == {"활성"}
    fld = _fields(reg)["STR"]["id"]
    assert _wt(out1, RENAMED_W) == [f"파트 약칭 개명 반영: 구조 → STR ({fld} 유지 — 툴사용·입출력 ID 도 유지, 범용 이름 툴 1개 키 "
                                    "'미상:구조/…' → '미상:STR/…' (TOOL ID 유지))"]
    assert _ids_of(out1, "STR") == (use0, io0)
    s2 = _survey(tmp_path, "s2", {STR_NEW: STR, TURB: TURB})                     # 새 약칭 파일명으로 — 그대로 (멱등)
    _set_names(s2 / STR_NEW, {"STR-01": "자체개발"})
    out2 = run_load(input_dir=s2, registry_dir=reg, out_root=tmp_path / "o2", shacl=False, config_dir=cfg)
    assert _tool_ids(reg)["미상:STR/STR-01"] == tool0 and not _wt(out2, RENAMED_W)
    assert out2.log["registry"]["transitions"]["tool"] == {"created": 0, "revived": 0}


def test_generic_tool_rekey_prefix_held_when_target_exists(tmp_path):
    """툴 표 키 접두 개명: 새 키 행이 이미 있으면 그 행은 손대지 않는다 — 옛 행이 활성이면 보류 목록, 폐기면 조용히 (알릴 것이 없다)."""
    reg = tmp_path / "reg"
    reg.mkdir()
    (reg / "tools.csv").write_text("id,key,label,status,merged_into\nTOOL-000001,미상:A/X-1,a,활성,\nTOOL-000002,미상:B/X-1,b,활성,\n"
                                   "TOOL-000003,미상:A/X-2,c,활성,\nTOOL-000004,미상:A/X-3,d,폐기,\nTOOL-000005,미상:B/X-3,e,활성,\n"
                                   "TOOL-000006,미상:AB/X-1,f,활성,\n", encoding="utf-8-sig")
    rg = Registry(reg)
    assert rg.rekey_prefix("tool", "미상:A/", "미상:B/") == (["TOOL-000003"], ["TOOL-000001"])
    assert [r["key"] for r in rg.rows("tool")] == ["미상:A/X-1", "미상:B/X-1", "미상:B/X-2", "미상:A/X-3", "미상:B/X-3", "미상:AB/X-1"]


def test_part_new_and_retired_then_rename_conflict(tmp_path):
    """renamed_from 없이 약칭을 바꾸면 '파트 신규·폐기 동시' (새 FLD·새 USE ID) — 그 뒤 renamed_from 을 넣으면 '파트 약칭 개명 보류'(둘 다 있음, 손대지 않음).
    읽지 못한 파일이 있는 실행(폐기 판정 안 함)에서는 휴리스틱이 나오지 않는다."""
    reg, base = _base_two(tmp_path)
    old = _fields(reg)["구조"]["id"]
    use0, _ = _ids_of(base, "구조")
    no_rename = _parts_cfg(tmp_path, "plain", {"STR": STR_PART})
    survey = _survey(tmp_path, "s1", {STR_NEW: STR, TURB: TURB})
    out = run_load(input_dir=survey, registry_dir=reg, out_root=tmp_path / "o1", shacl=False, config_dir=no_rename)
    new = _fields(reg)["STR"]["id"]
    assert new != old and _fields(reg)["구조"]["status"] == "폐기"
    assert set(_ids_of(out, "STR")[0].values()).isdisjoint(use0.values())
    w = _wt(out, TURNOVER_W)
    assert len(w) == 1 and w[0].startswith(f"파트 신규·폐기 동시: 신규 STR({new}) · 폐기 구조({old}) — 약칭을 바꾼 것이면 ")
    assert "renamed_from: [옛 약칭]" in w[0]
    assert "  파트 신규·폐기 동시: 1" in (out.out_dir / "diag.txt").read_text(encoding="utf-8")
    # 이제 renamed_from 을 넣으면 — 옛·새 키가 둘 다 있어 손대지 않고 경고 (예외 없음, 새 ID 그대로)
    out2 = run_load(input_dir=survey, registry_dir=reg, out_root=tmp_path / "o2", shacl=False, config_dir=_rename_cfg(tmp_path))
    held = _wt(out2, HELD_W)
    assert len(held) == 1 and held[0].startswith(f"파트 약칭 개명 보류: '구조'({old})·'STR'({new}) 가 레지스트리에 둘 다 있음 — ")
    assert _fields(reg)["STR"]["id"] == new and _fields(reg)["구조"]["id"] == old
    assert not _wt(out2, RENAMED_W) and not _wt(out2, TURNOVER_W)
    # README_offline 6장의 사본 없는 되돌리기: fields.csv 에서 새 약칭 행 key → 다른 글자, 옛 약칭 행 key → 새 약칭 (메모장) → 옛 ID 가 되살아난다
    rows, _ = read_csv_rows(reg / "fields.csv")
    for r in rows:
        r["key"] = {"STR": "STR_취소", "구조": "STR"}.get(r["key"], r["key"])
    with (reg / "fields.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    out_fix = run_load(input_dir=survey, registry_dir=reg, out_root=tmp_path / "o2b", shacl=False, config_dir=_rename_cfg(tmp_path, "rename2"))
    assert _fields(reg)["STR"]["id"] == old and _fields(reg)["STR_취소"]["status"] == "폐기"
    assert _ids_of(out_fix, "STR")[0] == use0
    assert not _wt(out_fix, HELD_W) and not _wt(out_fix, RENAMED_W) and not _wt(out_fix, TURNOVER_W)
    # 읽지 못한 파일이 있는 실행 — 신규 FLD 가 생겨도 폐기 판정이 없으니 휴리스틱도 없다
    reg3, _ = _base_two(tmp_path / "t3")
    bad = _survey(tmp_path, "s3", {STR_NEW: STR, TURB: TURB})
    (bad / "SW조사_제어_20260924.xlsx").write_bytes(b"not a real workbook")
    out3 = run_load(input_dir=bad, registry_dir=reg3, out_root=tmp_path / "o3", shacl=False, config_dir=no_rename)
    assert not out3.result.complete and not _wt(out3, TURNOVER_W)
    assert _fields(reg3)["구조"]["status"] == "활성"


def test_part_turnover_masks_person_like_key(tmp_path):
    """휴리스틱 경고의 약칭은 레지스트리 원문 — 옛 판 키가 인명 유사면 FLD ID 만 (값 가림, C5)."""
    reg = tmp_path / "registry"
    reg.mkdir()
    (reg / "fields.csv").write_text("id,key,label,status,merged_into\nFLD-001,가나다 책임,가나다 책임,활성,\n", encoding="utf-8-sig")
    out = run_load(input_dir=_survey(tmp_path, "s", {STR: STR}), registry_dir=reg, out_root=tmp_path / "o", shacl=False)
    w = _wt(out, TURNOVER_W)
    assert len(w) == 1 and w[0].startswith("파트 신규·폐기 동시: 신규 구조(FLD-002) · 폐기 FLD-001 — ") and "가나다" not in w[0]


@pytest.mark.parametrize("parts, drop, match", [
    ({"STR": {**STR_PART, "renamed_from": "구조"}}, ("구조",), r"STR\.renamed_from: 형식은 목록"),
    ({"STR": {**STR_PART, "renamed_from": ["구조"]}}, (), r"옛 약칭 '구조' 이 file_bundles 키·synthetic_parts 에 있다"),
    ({"STR": {**STR_PART, "renamed_from": ["구조"]}, "STR2": {**STR_PART, "renamed_from": ["구조"]}}, ("구조",),
     r"옛 약칭 '구조' 이 두 파트\(STR·STR2\)의 renamed_from 에 있다"),
    ({"STR": {**STR_PART, "renamed_from": ["TEST"]}}, (), r"옛 약칭 'TEST' 이 parts 에 아직 있다 — 지우거나 'status: 폐기' 로"),
    ({"STR": {**STR_PART, "renamed_from": ["STR"]}}, (), r"옛 약칭이 비었거나 새 약칭과 같다"),
    ({"STR": {**STR_PART, "renamed_from": ["MD"]}}, (), r"옛 약칭 'MD' 이 file_bundles 키"),
    ({"STR": {**STR_PART, "renamed_from": ["S1"]}, "S1": {**STR_PART, "status": "폐기", "renamed_from": ["S0"]}}, (),
     r"S1\.renamed_from: 'S1' 은 'STR' 의 옛 약칭이다 — 마지막 약칭 한 곳에"),
], ids=["not-list", "still-synthetic", "two-parts", "still-active-part", "self", "bundle-code", "chain"])
def test_parts_renamed_from_config_errors(tmp_path, parts, drop, match):
    cfg = _parts_cfg(tmp_path, "bad", parts, drop_synthetic=drop)
    with pytest.raises(ConfigError, match=match):
        Loader(config_dir=cfg)


def test_parts_renamed_from_retired_entry_ok_and_cli_error(tmp_path, capsys):
    """옛 약칭 항목이 status: 폐기 면 허용 (사내 오버레이는 저장소 키를 지울 수 없다) — 오버레이로 개명. 설정 오류는 load 가 '[NG] 설정 오류' rc 2."""
    over = tmp_path / "over"
    over.mkdir()
    (over / "parts.yaml").write_text(yaml.safe_dump({"parts": {"TST": {"name": "시험 파트", "domains": ["시험"], "renamed_from": ["TEST"]},
                                                               "TEST": {"status": "폐기"}}}, allow_unicode=True), encoding="utf-8")
    ld = Loader(overlay_dir=over)
    assert ld.renames == {"TEST": "TST"} and "parts.yaml" in ld.overlay_files
    assert ld.file_label("Tool조사_TEST_20261012.xlsx", "0" * 64) == ("Tool조사_TEST_20261012.xlsx", "TST", "20261012", 0)
    (over / "parts.yaml").write_text(yaml.safe_dump({"parts": {"TST": {"renamed_from": ["TEST"]}}}, allow_unicode=True), encoding="utf-8")
    reg = tmp_path / "registry"
    copy_registry(REGISTRY_DIR, reg)
    rc = cli.main(["load", "--registry", str(reg), "--out", str(tmp_path / "out"), "--overlay", str(over), "--no-shacl"])
    err = capsys.readouterr().err
    assert rc == 2 and err.startswith("[NG] 설정 오류: ") and "옛 약칭 'TEST' 이 parts 에 아직 있다" in err and "Traceback" not in err
    assert not (tmp_path / "out").exists() and not (reg / LOCK_NAME).exists()


def test_bundle_part_rename_maps_prefix(tmp_path):
    """묶음 파일 안 파트 개명 (MDA → MDZ): 행의 옛 Tool ID 'MDA-1' 은 새 파트 MDZ 로, 기준 USE ID 유지 — file_bundles 목록에 옛 약칭이 남아 있어도."""
    bundle = {"MDX": ["MDA", "MDB"]}
    parts = {"MDA": {"name": "가상 A 파트", "domains": ["구조"]}, "MDB": {"name": "가상 B 파트", "domains": ["구조"]}}
    survey = tmp_path / "survey"
    _rename_ids(_place(survey, STR, "Tool조사_MDX_20260930.xlsx"),
                {"STR-01": "MDA-1", "STR-02": "MDA-2", "STR-03": "MDB-1", "STR-04": "MDB-2", "STR-05": "MDB-3"})
    reg = tmp_path / "registry"
    base = run_load(input_dir=survey, registry_dir=reg, out_root=tmp_path / "o0", shacl=False,
                    config_dir=_parts_cfg(tmp_path, "b0", parts, bundles=bundle))
    before = {u.sw_id: (u.field, u.node_id) for u in base.result.usages}
    fld = _fields(reg)["MDA"]["id"]
    renamed = {"MDZ": {"name": "가상 Z 파트", "domains": ["구조"], "renamed_from": ["MDA"]}, "MDB": parts["MDB"]}
    cfg = tmp_path / "b1"
    shutil.copytree(CONFIG_DIR, cfg)
    (cfg / "parts.yaml").write_text(yaml.safe_dump({"parts": renamed, "file_bundles": bundle}, allow_unicode=True), encoding="utf-8")
    out = run_load(input_dir=survey, registry_dir=reg, out_root=tmp_path / "o1", shacl=False, config_dir=cfg)
    after = {u.sw_id: (u.field, u.node_id) for u in out.result.usages}
    assert {k: v[0] for k, v in after.items()} == {"MDA-1": "MDZ", "MDA-2": "MDZ", "MDB-1": "MDB", "MDB-2": "MDB", "MDB-3": "MDB"}
    assert {k: v[1] for k, v in after.items()} == {k: v[1] for k, v in before.items()}
    assert _wt(out, RENAMED_W) == [f"파트 약칭 개명 반영: MDA → MDZ ({fld} 유지 — 툴사용·입출력 ID 도 유지)"]
    assert not _wt(out, "묶음 파일 파트 미정") and not _wt(out, OLD_NAME_W) and not _wt(out, TURNOVER_W)
    assert out.result.part_labels["MDZ"] == "가상 Z 파트 (MDZ)"


# ---- F3. 한 레지스트리 동시 적재 잠금 (docs/09 7장)
def _csv_bytes(reg: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(reg.glob("*.csv"))}


def test_registry_lock_blocks_second_load(tmp_path):
    reg = tmp_path / "registry"
    copy_registry(REGISTRY_DIR, reg)
    lock = reg / LOCK_NAME
    lock.write_text("pid=4321 started=2026-10-12T09:00:00+09:00\n", encoding="utf-8")
    before = _csv_bytes(reg)
    survey = _survey(tmp_path, "s", {STR: STR})
    with pytest.raises(RegistryBusyError) as e:
        run_load(input_dir=survey, registry_dir=reg, out_root=tmp_path / "out", shacl=False)
    msg = str(e.value)
    assert str(lock) in msg and "(pid=4321 started=2026-10-12T09:00:00+09:00)" in msg and "그 잠금 파일을 지우고 다시 실행한다" in msg
    assert _csv_bytes(reg) == before and not (tmp_path / "out").exists()
    assert lock.read_text(encoding="utf-8").startswith("pid=4321")              # 남의 잠금은 지우지 않는다
    lock.unlink()
    seen = []
    real = SurveyWriter.write

    def spy(self, *a, **kw):                                                       # 적재 도중에는 잠금이 있다 — 내 pid
        seen.append(lock.read_text(encoding="utf-8"))
        return real(self, *a, **kw)

    import os

    from _pytest.monkeypatch import MonkeyPatch
    with MonkeyPatch.context() as mp:
        mp.setattr(SurveyWriter, "write", spy)
        out = run_load(input_dir=survey, registry_dir=reg, out_root=tmp_path / "out", shacl=False)
    assert re.fullmatch(rf"pid={os.getpid()} started=\d{{4}}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d\n", seen[0])
    assert not lock.exists() and (out.out_dir / "survey.ttl").is_file()


def test_lock_and_run_dir_released_on_failure(tmp_path, monkeypatch):
    """적재 도중 예외 — 잠금 파일이 지워지고, 레지스트리는 그대로, 빈 실행 폴더도 남지 않는다."""
    reg = tmp_path / "registry"
    copy_registry(REGISTRY_DIR, reg)
    before = _csv_bytes(reg)

    def boom(self, *a, **kw):
        raise RuntimeError("시험용 실패")

    monkeypatch.setattr(SurveyWriter, "write", boom)
    with pytest.raises(RuntimeError, match="시험용 실패"):
        run_load(input_dir=_survey(tmp_path, "s", {STR: STR}), registry_dir=reg, out_root=tmp_path / "out", shacl=False, now=F_NOW)
    assert not (reg / LOCK_NAME).exists() and _csv_bytes(reg) == before
    assert list((tmp_path / "out").iterdir()) == []


def test_dry_run_ignores_lock(tmp_path):
    """save_registry=False 는 레지스트리를 쓰지 않아 잠그지 않는다 — 남의 잠금이 있어도 적재하고, 그 잠금은 건드리지 않는다."""
    reg = tmp_path / "registry"
    copy_registry(REGISTRY_DIR, reg)
    (reg / LOCK_NAME).write_text("pid=1 started=x\n", encoding="utf-8")
    out = run_load(input_dir=_survey(tmp_path, "s", {STR: STR}), registry_dir=reg, out_root=tmp_path / "out", shacl=False,
                   save_registry=False)
    assert len(out.result.usages) == 5 and (reg / LOCK_NAME).read_text(encoding="utf-8") == "pid=1 started=x\n"


def test_cli_load_registry_busy_rc2(tmp_path, capsys):
    reg = tmp_path / "registry"
    copy_registry(REGISTRY_DIR, reg)
    (reg / LOCK_NAME).write_text("pid=4321 started=2026-10-12T09:00:00+09:00\n", encoding="utf-8")
    rc = cli.main(["load", "--registry", str(reg), "--out", str(tmp_path / "out"), "--no-shacl"])
    err = capsys.readouterr().err
    assert rc == 2 and err.startswith("[NG] 레지스트리 사용 중: 다른 적재가 이 레지스트리를 쓰는 중이다 — 잠금 파일 ") and "Traceback" not in err
    assert len(err.strip().splitlines()) == 1 and (reg / LOCK_NAME).exists() and not (tmp_path / "out").exists()


def test_lock_file_is_git_ignored():
    """합성 레지스트리(git 추적)에 강제 종료로 남은 잠금이 커밋되지 않게 — .gitignore 에 있다."""
    assert LOCK_NAME in (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()


# ---- F4. 같은 초 두 실행 (docs/09 7장) — 1초 밀어 새 폴더, 앞 실행 산출물을 덮어쓰지 않는다
def test_same_second_runs_get_distinct_run_dirs(tmp_path):
    out_root = tmp_path / "out"
    reg_a, reg_b = tmp_path / "reg_a", tmp_path / "reg_b"
    copy_registry(REGISTRY_DIR, reg_a)
    a = run_load(registry_dir=reg_a, out_root=out_root, now=F_NOW, shacl=False)
    ttl_a = (a.out_dir / "survey.ttl").read_bytes()
    b = run_load(input_dir=_survey(tmp_path, "s", {STR: STR}), registry_dir=reg_b, out_root=out_root, now=F_NOW, shacl=False)
    assert a.run_id == "20261012T090000" and b.run_id == "20261012T090001" and a.out_dir != b.out_dir
    assert (a.out_dir / "survey.ttl").read_bytes() == ttl_a
    assert b.log["loaded_at"].startswith("2026-10-12T09:00:01")
    load_a = set(re.findall(r"LOAD-\d{8}T\d{6}-\d{2}", a.turtle))
    load_b = set(re.findall(r"LOAD-\d{8}T\d{6}-\d{2}", b.turtle))
    assert load_a and load_b and not (load_a & load_b)
    c = run_load(input_dir=_survey(tmp_path, "s2", {TURB: TURB}), registry_dir=tmp_path / "reg_c", out_root=out_root, now=F_NOW, shacl=False)
    assert c.run_id == "20261012T090002"
    assert sorted(p.name for p in out_root.iterdir()) == ["20261012T090000", "20261012T090001", "20261012T090002"]
