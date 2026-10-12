"""조사 엑셀 적재 (docs/02 5·6장, M3 · M3.1).

파트별 xlsx 를 읽어 툴사용(SW기본정보 행)·입출력(SW입출력 행)으로 만들고, 툴 통합·확장자·연계 SW명을 정규화한다.
RDF 로 쓰는 것은 rdf_writer, ID 고정은 registry 가 맡는다. 세부 해석의 정본은 골든 interpretations (I번호).

- 헤더 이름으로 매핑 (NFKC 후 공백·'*' 무시, I30) — 매핑 안 된 헤더는 경고, 의도적 제외 열(B 수식·K 문의처)은 읽지 않는다.
  추가 문구는 config/header_map.yaml + 사내 오버레이 (시트·슬롯별 합집합; 제외 열·인명 열 문구는 설정 오류 — form_spec).
- 엑셀 층 신호 (I37): 수식 오류 셀(#N/A 등)은 빈칸 + 열별 경고 + 행별 수정 요청 (Tool ID 칸이면 행 제외·이어받기 안 함), 캐시 없는
  수식·숨긴 행·양식 밖(사본) 시트·툴사용 0건 파일은 경고.
- 만료 시기 문자열: 텍스트 날짜 → YYYY-MM + 경고, '영구'·빈 값 토큰 → 빈칸, 그 밖 → 원문 + 경고·수정 요청 (I16·I27, docs/09 #21).
- 시트·선택지 목록 이름은 양식판마다 다르다 — config/rules.yaml loader.sheets·choice_list_aliases 가 흡수 (docs/09 #13, 양식 v1.1).
- 파트(Field) = 파일명의 약칭 (docs/10 5장). 묶음 파일(MD = MDT+MDC)은 행의 Tool ID 앞부분으로 나눈다 (config/parts.yaml).
  행의 '담당 부서' 는 분류 속성 reported_domain — 파트 설정과 다르면 경고만. 약칭을 바꾸면 새 약칭 항목의 renamed_from 에 옛 약칭을 적는다 —
  옛 약칭 파일명·Tool ID 앞부분은 새 약칭으로 읽고, run_load 가 레지스트리 분야 키를 바꿔 ID 를 유지한다 (I31, docs/09 #25b).
- 예시 행은 위치가 아니라 적재 열 전체가 템플릿 예시와 같은지로 판별 (I15) — config/template_examples.yaml (+ 오버레이).
  예시의 정보 열 80% 이상이 같거나 비고가 예시 문구인 '예시와 거의 같은 행' 은 경고 후 응답으로 적재하고, 같은 Tool ID 의 진짜 행이 뒤에
  있으면 진짜 행을 쓴다 (I15 개정, docs/09 #3). 시트에 예시 유사 행만 있고 정확한 예시가 0 이면 설정 점검 경고.
- 같은 파트 파일이 여럿이면 (날짜, 새 약칭 파일명인가, 사본 꼬리를 뗀 파일명, 사본 번호 '(n)') 최신 1개만 적재하고, 그 뒤 같은 내용(sha256) 파일은 한 번만 —
  대체된 옛 회신과 내용이 같은 사본도 적재하지 않는다 (I31·I33).
- 파일 간 같은 (파트, Tool ID) 는 둘 다 적재하고 경고 — 전용 파일이 아닌 쪽 레지스트리 키에 구분 꼬리 '@<약칭|file-sha10>' (I36, docs/09 #1).
- 툴 통합 (6.1): 별칭·통합 판정(tool_aliases.yaml + 오버레이)은 제조사를 뗀 키, 없으면 떼지 않은 이름 키로 찾는다 (docs/09 #2 (3)). 판정 항목 가운데
  이번 적재의 툴·연계 Tool명 어디에도 키가 없는 것은 경고 '별칭 미적용' (#2 (4) — 저장소의 공개 별칭 사전은 제외). 해석 못 한 연계 Tool명은
  CQ09 후보 + 검토표 '연계SW 미해석' 행 (partner_candidates, #17 — 툴A = 기존 툴 키 제안, 툴B = 연계 키).
- 어떤 행도 조용히 버리지 않는다 — 제외는 사유와 함께 excluded_rows, 문제는 warnings (5장 6). 행 단위 문제는 issues 에도
  구조화해 남겨 파트별 수정 요청표(fix_requests)를 만든다 (M3.1).
- 인명 열(실무 문의처)은 읽지 않는다 (CLAUDE.md 절대 규칙 5). 인명 유사 패턴은 경고만 하고 경고에 값을 옮기지 않는다 (D6, #20).
  검사 범위: 적재하는 모든 문자열 칸(정수 변환에 실패한 원문 포함) + 제외하는 내용 행(Tool ID 없음·Tool ID 수식 오류·빈 행 뒤) — 제외 행이 걸리면
  수정 요청은 '인명 유사' 한 줄 (Tool ID 를 붙이라고 하지 않는다, 2026-10-12 재검토 수리).
  값을 인용하는 경고·수정 요청표·검토표 표기 칸(힌트 키 포함)·load_log 속성 충돌 값은 Loader._q 를 거친다 — 인명 유사면 PERSON_MASK (docs/09 C5;
  모든 경고 2026-10-12 검토 수리 — 행 경고의 위치 문구(where)도 Tool ID·데이터명을 _q 로 만든다). 툴 키를 인용할 때는 Loader._qk — 키와 그 키를 낸
  보고 이름을 함께 판정한다 (키는 공백이 빠져 '이름 직급 한글…' 꼴이 패턴에 안 걸린다, 2026-10-12 재검토 수리).
  규칙 밖 파일명은 해시 이름으로만 기록한다 (#8 — 파일명에 인명이 섞여 있을 수 있다).
"""

from __future__ import annotations

import datetime as dt
import difflib
import hashlib
import posixpath
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

import openpyxl
import yaml
from openpyxl.utils.cell import column_index_from_string

from engenius_onto.config import CONFIG_DIR, ConfigError, config_where, load_config, load_yaml, read_yaml
from engenius_onto.form_spec import Column, FormSpec, load_form_spec, norm_header
from engenius_onto.normalize import GENERIC_KEY_PREFIX, Normalizer, merge_keys_from_pairs, nfc_strip, nfkc, read_merge_pairs

USAGE_SHEET, IO_SHEET = "SW기본정보", "SW입출력"      # 스키마의 시트 이름 (실제 파일의 시트 이름은 설정으로 찾는다)
EXCEL_SUFFIXES = {".xlsx", ".xlsm", ".xls"}
PERSON_MASK = "[인명 유사 — 값 생략]"                  # 경고·로그에 인용할 값이 인명 유사일 때 대신 쓰는 문구 (Loader._q, docs/09 #20·C5)
# 제외하는 내용 행(Tool ID 없음 등)이 인명 유사일 때 수정 요청표 안내 (Loader._excluded_person) — 'Tool ID 를 적어 주세요' 대신.
# 실제 Tool 행일 수도 있어 행 삭제만 시키지 않는다 (이름·연락처를 먼저 지우게 해 다음 적재에서 인명이 그래프에 들어가지 않게)
PERSON_ROW_HINT = ("사람 이름·연락처로 보이는 행 — 표 아래 연락처·작성자 메모면 지워 주세요 (Tool ID 를 붙이지 마세요). "
                   "실제 Tool 행이면 이름·연락처만 지우고 Tool ID 를 적어 주세요")
PERSON_TAIL_HINT = ("사람 이름·연락처로 보이는 행 — 표 아래 연락처·작성자 메모면 지워 주세요 (표로 옮기지 마세요). "
                    "실제 Tool 행이면 이름·연락처만 지우고 빈 행을 지워 위로 붙여 주세요")
ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿"), None)
# 엑셀 수식 결과 오류 (I37) — 셀 형식 'e' 는 모두, 문자열이면 이 표기와 같을 때 (openpyxl ERROR_CODES + 새 엑셀 오류)
EXCEL_ERRORS = ("#NULL!", "#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!", "#N/A", "#SPILL!", "#CALC!", "#FIELD!", "#BLOCKED!",
                "#CONNECT!", "#BUSY!", "#UNKNOWN!", "#GETTING_DATA")
# 만료 시기 텍스트 날짜 (I27, docs/09 #21 3단) — NFKC·앞뒤 공백 뒤 문자열 전체. 구분자 앞뒤 공백 허용, 월 1~12·일 1~31 만
MONTH_TEXT_RES = (
    re.compile(r"(?P<y>[0-9]{4})\s*[.\-/]\s*(?P<m>[0-9]{1,2})\s*\.?"),                                      # 2027.03 · 2027-3 · 2027/03 · 2027. 3.
    re.compile(r"(?P<y>[0-9]{4})\s*[.\-/]\s*(?P<m>[0-9]{1,2})\s*[.\-/]\s*(?P<d>[0-9]{1,2})\s*\.?"),      # 2027-03-31 · 2027.03.31 · 2027. 3. 31.
    re.compile(r"(?P<y>[0-9]{4})\s*년\s*(?P<m>[0-9]{1,2})\s*월(?:\s*(?P<d>[0-9]{1,2})\s*일)?"),           # 2027년 3월 · 2027년 3월 31일
)


def month_text(s) -> str | None:
    """만료 시기 텍스트 → 'YYYY-MM' (MONTH_TEXT_RES 가운데 하나에 전체가 맞고 월·일이 범위 안일 때), 아니면 None (I27)."""
    t = unicodedata.normalize("NFKC", "" if s is None else str(s)).strip()
    for rx in MONTH_TEXT_RES:
        m = rx.fullmatch(t)
        if m:
            mo, d = int(m["m"]), int(m["d"]) if m.groupdict().get("d") else 1
            if 1 <= mo <= 12 and 1 <= d <= 31:
                return f"{m['y']}-{mo:02d}"
    return None


def excel_error(cell) -> str | None:
    """셀이 수식 결과 오류면 그 표기('#N/A' 등), 아니면 None (I37). 셀 형식 'e' 는 표기와 무관하게 오류."""
    v = cell.value
    if getattr(cell, "data_type", None) == "e":
        return str(v).strip() if v not in (None, "") else "#오류"
    if isinstance(v, str) and v.strip().upper() in EXCEL_ERRORS:
        return v.strip().upper()
    return None


def id_key(s) -> str:
    """Tool ID 연결용 키 (docs/09 #18): NFKC·앞뒤 공백·보이지 않는 문자 제거·대문자, '-' 뒤 숫자 앞 0 무시 (MDC-01 = MDC-1)."""
    k = unicodedata.normalize("NFKC", "" if s is None else str(s)).translate(ZERO_WIDTH).strip().upper()
    return re.sub(r"(?<=-)0+(?=\d)", "", re.sub(r"\s+", "", k))


# --------------------------------------------------------------------------- 시트 XML 직접 읽기 (I37 ② 캐시 없는 수식)
# openpyxl 은 칸의 <v></v>·<v/>·<v> 없음을 모두 None 으로 읽어 '캐시된 빈 문자열' 과 '캐시 없음' 을 구별하지 못한다 — 표준 라이브러리로 XML 을 본다.
def _local(tag: str) -> str:
    """XML 태그·속성 이름의 로컬 부분 ('{ns}c' → 'c') — OOXML 표준·엄격(strict) 이름공간을 함께 받는다."""
    return tag.rsplit("}", 1)[-1]


def _xml_root(z: zipfile.ZipFile, part: str):
    with z.open(part) as f:
        return ET.parse(f).getroot()


def sheet_parts(z: zipfile.ZipFile) -> dict[str, str]:
    """{시트 이름: 시트 XML 경로} — _rels/.rels(통합 문서 위치) → 통합 문서의 <sheet name r:id> → 통합 문서 rels 의 Target."""
    names = set(z.namelist())
    wb_part = "xl/workbook.xml"
    if "_rels/.rels" in names:
        for rel in _xml_root(z, "_rels/.rels"):
            if rel.get("Type", "").endswith("/officeDocument"):
                wb_part = rel.get("Target", wb_part).lstrip("/")
                break
    base = posixpath.dirname(wb_part)
    targets = {}
    for rel in _xml_root(z, posixpath.join(base, "_rels", posixpath.basename(wb_part) + ".rels")):
        t = rel.get("Target", "")
        targets[rel.get("Id")] = t.lstrip("/") if t.startswith("/") else posixpath.normpath(posixpath.join(base, t))
    out = {}
    for el in _xml_root(z, wb_part).iter():
        if _local(el.tag) == "sheet":
            rid = next((v for k, v in el.attrib.items() if _local(k) == "id"), None)
            if rid in targets:
                out[el.get("name")] = targets[rid]
    return out


def formula_cells_without_cache(path: Path, sheets: list[str], min_row: int) -> dict[str, set[tuple[int, int]]]:
    """{시트: 캐시 없는 수식 칸 (행, 열)} — min_row 행부터 (I37 ②). 시트 XML 을 스트리밍으로 훑는다 (먼 서식 칸이 있어도 메모리 일정).

    캐시 없음 = <f> 가 있는데 캐시 값이 없다: <v> 가 없거나, <v> 가 비었고 형식(t)이 'str' 이 아님 (openpyxl 로 저장한 수식 — 엑셀이 계산한 적
    없음). 엑셀·LibreOffice 는 빈 문자열을 돌려주는 수식(=IFERROR(…,""))을 t="str" + 빈 <v> 로 저장한다 — 캐시된 빈 문자열이라 다시 저장해도
    그대로이므로 '캐시 없음' 이 아니다 (2026-10-12 검토 수리). 인라인 문자열(<is>)도 캐시로 본다."""
    out: dict[str, set[tuple[int, int]]] = {}
    with zipfile.ZipFile(path) as z:
        parts = sheet_parts(z)
        for name in sheets:
            cells: set[tuple[int, int]] = set()
            row = col = 0
            sheet_data = None
            with z.open(parts[name]) as f:
                for ev, el in ET.iterparse(f, events=("start", "end")):
                    tag = _local(el.tag)
                    if ev == "start":
                        if tag == "sheetData":
                            sheet_data = el
                        elif tag == "row":
                            r = el.get("r")
                            row, col = (int(r) if r else row + 1), 0
                        continue
                    if tag == "c":
                        ref = el.get("r")
                        if ref:
                            letters = ref.rstrip("0123456789")
                            row_c, col = int(ref[len(letters):]), column_index_from_string(letters)
                        else:
                            row_c, col = row, col + 1
                        kids = {_local(ch.tag): ch for ch in el}
                        if "f" in kids and row_c >= min_row:
                            v = kids.get("v")
                            if not ("is" in kids or (v is not None and (v.text or el.get("t") == "str"))):
                                cells.add((row_c, col))
                        el.clear()
                    elif tag == "row" and sheet_data is not None:
                        sheet_data.clear()                               # 읽은 행은 버린다 (메모리 일정)
            out[name] = cells
    return out


# --------------------------------------------------------------------------- 레코드
@dataclass
class UsageRec:
    file: str
    file_field: str | None
    row: int
    v: dict                         # 슬롯 → 값 (문자열·정수·None)
    raw: dict = field(default_factory=dict)   # 정수 변환 실패 원문 (슬롯 → 원문)
    part: str | None = None          # 파트 약칭 = Field 키 (v0.3: 파일명에서, 묶음 파일은 Tool ID 앞부분에서)
    tool_key: str = ""
    node_id: str = ""                # 레지스트리 USE ID (rdf_writer 가 채움)
    reg_tag: str = ""                # 파일 간 같은 (파트, Tool ID) 의 구분 꼬리 — 파일 약칭 또는 'file-<sha256 앞 10자>' (I36, 충돌 때만)
    near_example: str | None = None  # 예시와 거의 같은 행이면 근거 ('29/30 열 같음' 등, I15 개정 — docs/09 #3)

    @property
    def sw_id(self) -> str:
        return nfc_strip(self.v.get("source_key"))

    @property
    def field(self) -> str:
        return self.part or ""

    @property
    def reg_key(self) -> str:
        """레지스트리 USE 키의 Tool ID 부분 — 충돌로 구분 꼬리가 붙은 행만 '<Tool ID>@<구분>' (I36). 파일명은 쓰지 않는다 (C4)."""
        return self.sw_id + (f"@{self.reg_tag}" if self.reg_tag else "")

    @property
    def key(self) -> str:
        return f"{self.field}/{self.reg_key}"


@dataclass
class IORec:
    file: str
    file_field: str | None
    row: int
    v: dict
    owner: UsageRec | None
    direction_short: str            # in | out | ? (표시 키용)
    exts: list = field(default_factory=list)
    inhouse: bool = False
    bad_ext: list = field(default_factory=list)
    partner_names: list = field(default_factory=list)
    partner_tools: set = field(default_factory=set)
    partner_unresolved: list = field(default_factory=list)
    seq: int = 0                    # 완전 중복 행 순번 (D2)
    suffix: str = ""                # 표시 키 구분 (골든 키 표기)
    node_id: str = ""                # IO-<해시> (rdf_writer 가 채움)
    near_example: str | None = None  # 예시와 거의 같은 행이면 근거 (I15 개정 — 응답으로 적재, 경고만)

    @property
    def sw_id(self) -> str:
        return nfc_strip(self.v.get("owner_source_key"))

    @property
    def name(self) -> str:
        return nfc_strip(self.v.get("data_name"))

    @property
    def category(self) -> str:
        return nfc_strip(self.v.get("io_category"))

    @property
    def base_key(self) -> str:
        owner = self.owner.key if self.owner else f"{self.file_field or '(파트 미상)'}/{self.sw_id}(고아)"
        return f"{owner}/{self.direction_short}/{self.name}"

    @property
    def key(self) -> str:
        """사람이 읽는 키 (골든 표기와 같음) — 로그·보고서용. 노드 ID 는 해시 (docs/02 4장)."""
        return self.base_key + self.suffix


@dataclass
class ToolGroup:
    key: str
    usages: list
    alias_label: str | None = None

    @property
    def names(self) -> list[str]:
        return sorted({nfc_strip(u.v.get("reported_tool_name")) for u in self.usages})

    def majority(self, slot: str) -> str | None:
        c = Counter(nfc_strip(u.v.get(slot)) for u in self.usages if nfc_strip(u.v.get(slot)))
        if not c:
            return None
        top = max(c.values())
        return sorted(v for v, n in c.items() if n == top)[0]      # I23 동률은 사전순 첫 값

    @property
    def pref_label(self) -> str:
        if self.alias_label:
            return self.alias_label
        c = Counter(nfc_strip(u.v.get("reported_tool_name")) for u in self.usages)
        top = max(c.values())
        return sorted(v for v, n in c.items() if n == top)[0]

    @property
    def alt_labels(self) -> list[str]:
        return [n for n in self.names if n != self.pref_label]


@dataclass
class FileReport:
    name: str                        # 기록용 이름 — 규칙 밖 파일명은 해시 이름 (#8). 실제 경로는 path
    sha256: str
    field: str | None                # 파일명 약칭 (파트 또는 묶음)
    date: str | None
    path: Path | None = None
    superseded_by: str | None = None
    unreadable: str | None = None    # 읽지 못한 이유 (#7)
    usage_rows: int = 0
    io_rows: int = 0
    excluded: int = 0
    warnings: int = 0
    copy: int = 0                    # 파일명 사본 번호 '(n)' — 없으면 0 (I31·I33)
    index: int = 0                   # 입력 폴더 정렬 순번 (1부터) — 해시 이름 파일을 사람이 찾게 (#8)
    duplicate_of: str | None = None  # 같은 내용(sha256) 파일이라 적재하지 않음 — 남긴 파일의 기록 이름 (I33)
    renamed_from: str | None = None  # 파일명이 옛 약칭(parts.yaml renamed_from)이면 그 옛 약칭 — field 는 새 약칭 (#25b)

    def stats(self) -> dict:
        """골든 per_file 과 dict 전체를 비교한다 — 키를 더하지 않는다 (copy·index·duplicate_of 는 load_log files[] 에만)."""
        return {"usage_rows": self.usage_rows, "io_rows": self.io_rows, "excluded": self.excluded,
                "warnings": self.warnings, "superseded": self.superseded_by is not None}


@dataclass
class LoadResult:
    files: list[FileReport]
    usages: list[UsageRec]
    ios: list[IORec]
    tools: dict[str, ToolGroup]
    warnings: list[str]
    excluded_rows: list[dict]
    merge_candidates: list[dict]
    attribute_conflicts: dict
    alias_map: dict[str, str]
    issues: list[dict] = field(default_factory=list)       # 행 단위 문제 (수정 요청표·diag 용)
    part_labels: dict[str, str] = field(default_factory=dict)
    partner_candidates: list[dict] = field(default_factory=list)   # 검토표 '연계SW 미해석' 행 (Loader._partner_review, docs/09 #17)
    part_renames: dict[str, str] = field(default_factory=dict)      # {옛 약칭: 새 약칭} — run_load 가 레지스트리 분야 키를 바꾼다 (#25b)

    def unresolved_partners(self) -> dict[str, dict]:
        """CQ09 조사 누락 후보 — 해석 못 한 연계 Tool명 키별 {mentions, fields} (I10, load_log unresolved_partners)."""
        return unresolved_partner_summary(self.ios)

    @property
    def loaded_files(self) -> list[FileReport]:
        return [f for f in self.files if f.superseded_by is None and f.unreadable is None and f.duplicate_of is None]

    @property
    def complete(self) -> bool:
        """모든 파일을 읽었는가 — 아니면 이번 적재에 없다고 폐기 처리하지 않는다 (#7)."""
        return all(f.unreadable is None for f in self.files)

    def per_file(self) -> dict:
        return {f.name: f.stats() for f in self.files}


def unresolved_partner_summary(ios) -> dict[str, dict]:
    """해석 못 한 연계 Tool명 키별 언급 수·언급 파트 (CQ09 조사 누락 후보 — I10). 파트 = 소유 툴사용의 파트, 고아면 파일 약칭.
    x.partner_unresolved 는 인명 유사 조각을 이미 뺀 목록이다 (#20-2, C9) — load_log 와 검토표 연계 행(#17)이 이 한 집계를 쓴다."""
    out: dict[str, dict] = {}
    for x in ios:
        for k in x.partner_unresolved:
            e = out.setdefault(k, {"mentions": 0, "fields": set()})
            e["mentions"] += 1
            e["fields"].add(x.owner.field if x.owner else x.file_field)
    return {k: {"mentions": v["mentions"], "fields": sorted(f for f in v["fields"] if f)} for k, v in sorted(out.items())}


# --------------------------------------------------------------------------- 셀 값
def cell_key(v) -> str:
    """예시 행 대조용 정규형 — 셀 타입이 달라도 같은 값이면 같게."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else repr(v)
    if isinstance(v, dt.datetime):
        return v.date().isoformat() if v.time() == dt.time() else v.isoformat()
    if isinstance(v, dt.date):
        return v.isoformat()
    return nfc_strip(v)


def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def resolve_sheet(names: list[str], candidates) -> str | None:
    """실제 시트 이름 — 후보를 앞에서부터, 없으면 공백·'*' 무시 비교 (#13)."""
    cands = [candidates] if isinstance(candidates, str) else list(candidates or [])
    for c in cands:
        if c in names:
            return c
    norm = {norm_header(n): n for n in names}
    for c in cands:
        if norm_header(c) in norm:
            return norm[norm_header(c)]
    return None


# --------------------------------------------------------------------------- 적재기
class Loader:
    def __init__(self, config_dir: Path | None = None, schema_file: Path | None = None, overlay_dir: Path | None = None):
        """overlay_dir: 사내 설정 오버레이 폴더 (data/real/config, docs/09 C15) — 있는 파일만 config/ 위에 덮는다.
        None 이면 오버레이 없음 (run_load 가 실데이터 실행일 때 default_overlay_dir() 로 정해 넘긴다)."""
        self.config_dir = config_dir or CONFIG_DIR
        self.overlay_dir = Path(overlay_dir) if overlay_dir else None
        self.overlay_files: list[str] = []                      # 실제로 덮은 오버레이 파일 이름 (load_log·diag 용, 값 없음)
        self.rules = self._cfg("rules.yaml")
        self.lcfg = self.rules["loader"]
        self.norm = Normalizer.from_config(self.config_dir, self.overlay_dir)
        self._note_overlay("extensions.yaml")
        sheets = self.lcfg["sheets"]
        self.sheet_cands = {USAGE_SHEET: sheets["usage"], IO_SHEET: sheets["io"]}
        # 헤더 추가 문구: 저장소 + 사내 오버레이(시트·슬롯별 합집합, 시트 키는 v1.1 이름도 — I30)
        self.spec: FormSpec = load_form_spec(schema_file, self.config_dir, self.overlay_dir, sheet_names=self.sheet_cands)
        self._note_overlay("header_map.yaml")
        self.examples = self._cfg("template_examples.yaml")      # 오버레이는 시트별 합집합 (사내 양식판의 예시 — docs/09 #3)
        self.near_ratio, self.near_min_cols = self._near_settings()
        self.example_notes = {k for k in (cell_key(e.get("note")) for e in self.examples.get(USAGE_SHEET, []))
                              if k and not self.norm.is_empty(k)}           # 기본정보 예시 비고 문구 (예시 유사 판별)
        self.aliases_cfg = self._cfg("tool_aliases.yaml")
        self.person_re = re.compile(self.rules["person_pattern"])
        self.person_all = [re.compile(p) for p in self.rules.get("person_patterns_all") or []]
        self.free_text = set(self.rules["free_text_slots"])
        self.month_slots = set(self.lcfg.get("month_slots", ["license_expiry"]))
        # 아래 두 키의 코드 기본값 = 배포 rules.yaml 값 — 사내 rules.yaml 이 로컬 수정이라 업데이트가 '.new' 로만 남겨도(키 없음) 같은 동작.
        # 키가 있으면(빈 목록 포함) 그 값 (2026-10-12 검토 수리)
        self.month_blank = {nfkc(v).strip().lower() for v in self.lcfg.get("month_blank_values", ["영구"]) or []}   # '영구' 등 (I16)
        self.other_sheets = {norm_header(s) for s in self.lcfg.get("other_sheets", ["작성안내"]) or []}          # 양식 밖이지만 아는 시트 (I37)
        d = self.rules["direction"]
        self.dir_short = {**{x: "in" for x in d["consume"]}, **{x: "out" for x in d["produce"]}}
        self.choice_aliases = {name: [name, *alts] for name, alts in (self.lcfg.get("choice_list_aliases") or {}).items()}
        self.absent_ok = set(self.lcfg.get("absent_ok_slots") or [])
        parts_cfg = self._cfg("parts.yaml", optional=True)
        self.parts = parts_cfg.get("parts") or {}
        self.bundles = {k: list(v) for k, v in (parts_cfg.get("file_bundles") or {}).items()}
        self.synthetic_parts = set(parts_cfg.get("synthetic_parts") or [])
        self.renames = self._part_renames()                     # {옛 약칭: 새 약칭} (parts.yaml renamed_from, docs/09 #25b)
        self.value_aliases = self._value_aliases(self._cfg("value_aliases.yaml", optional=True))
        self.min_contain = int(self.rules.get("candidate_min_contain_len", 3))
        # 파일마다 _load_file 이 새로 채우는 엑셀 층 상태 (I37)·빈 값 표기 건수 — 여기서는 빈 값으로만 (메서드 단독 호출 대비)
        self._err_cells: dict[tuple[str, int], dict[str, str]] = {}
        self._hidden: dict[str, set[int]] = {}
        self._used_sheets: set[str] = set()
        self._formula_cells: dict[str, set[tuple[int, int]]] = {}
        self._na_cells = self._na_int_cells = self._na_month_cells = 0
        self.issues: list[dict] = []
        self.known_tool_keys: set[str] = set()                  # 레지스트리 활성 툴 키 (load() 가 받는다)
        self.prefix_held: list[tuple[str, str]] = []            # 접두 흡수를 보류한 그룹의 키 쌍 (_absorptions → _candidates '제조사 접두')
        self._seen_keys: set[str] = set()                       # 이번 적재에서 본 툴 이름 키 (별칭 미적용 검사 — _group_tools·_resolve_partners)
        self._key_names: dict[str, set[str]] = {}               # 툴 키 → 그 키를 낸 보고 이름들 (흡수 전 키 포함 — _qk 의 인명 판정, _group_tools)

    def _cfg(self, name: str, optional: bool = False) -> dict:
        """config/<name> (+ 오버레이). 덮은 파일 이름은 overlay_files 에 남긴다."""
        data, used = load_config(name, self.config_dir, self.overlay_dir, optional=optional)
        if used:
            self._note_overlay(name)
        return data

    def _note_overlay(self, name: str) -> None:
        if self.overlay_dir and (self.overlay_dir / name).is_file() and name not in self.overlay_files:
            self.overlay_files.append(name)

    def _near_settings(self) -> tuple[float, int]:
        """rules.yaml loader.example_near_ratio (0 < r ≤ 1) · example_near_min_cols (정수 ≥ 1) — 틀리면 ConfigError (I15 개정, docs/09 #3)."""
        r = self.lcfg.get("example_near_ratio", 0.8)
        m = self.lcfg.get("example_near_min_cols", 5)
        where = "config/rules.yaml (또는 data/real/config 오버레이) loader"
        if isinstance(r, bool) or not isinstance(r, (int, float)) or not 0 < r <= 1:
            raise ConfigError(f"{where}.example_near_ratio: 0 보다 크고 1 이하인 수여야 한다 (지금: {r!r})")
        if isinstance(m, bool) or not isinstance(m, int) or m < 1:
            raise ConfigError(f"{where}.example_near_min_cols: 1 이상의 정수여야 한다 (지금: {m!r})")
        return float(r), m

    def _optional_yaml(self, name: str) -> dict:
        path = self.config_dir / name
        return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.is_file() else {}

    def _value_aliases(self, cfg: dict) -> dict[str, dict[str, str]]:
        """열(양식 헤더 또는 슬롯 이름) → {적힌 값: 드롭다운 값} 을 슬롯 기준으로."""
        by_head = {}
        for sheet in (USAGE_SHEET, IO_SHEET):
            for c in self.spec.columns[sheet]:
                by_head.setdefault(norm_header(c.header), c.slot)
                by_head.setdefault(norm_header(c.slot), c.slot)
            for h, slot in self.spec.aliases.get(sheet, {}).items():
                by_head.setdefault(h, slot)
        out: dict[str, dict[str, str]] = {}
        for col, mapping in (cfg or {}).items():
            slot = by_head.get(norm_header(col))
            if slot is None:
                raise ConfigError(f"config/value_aliases.yaml: 알 수 없는 열 '{col}' — 양식 헤더(예: '전달 방법')나 슬롯 이름을 쓴다")
            out.setdefault(slot, {}).update({nfc_strip(k): nfc_strip(v) for k, v in (mapping or {}).items()})
        return out

    def _part_renames(self) -> dict[str, str]:
        """parts.yaml 파트 항목의 선택 키 renamed_from → {옛 약칭: 새 약칭} (docs/09 #25b, Leo 결정 2026-10-12 — 별도 field_renames.yaml 대신).
        새 약칭 항목에 옛 약칭을 모두 적는다 (여러 번 바꿨으면 마지막 약칭 한 곳에 — 사슬 없음). 옛 약칭 파일명은 새 약칭으로 읽고(I31·I33),
        run_load 가 레지스트리 분야 키를 옛 → 새로 바꿔 FLD·툴사용·입출력 ID 를 유지한다. 설정 오류(ConfigError, 약칭만 인용 — 값 아님):
        목록이 아님 · 옛 = 새 · 같은 옛 약칭이 두 파트에 · 옛 약칭이 아직 쓰이는 파트(parts 키인데 status 가 '폐기' 가 아님 — 오버레이는 키를 지울 수
        없어 status: 폐기 로 둔다)·묶음 약칭(file_bundles 키 — 묶음 파일 약칭 개명은 범위 밖)·합성 약칭(synthetic_parts) · 옛 약칭에 또 renamed_from."""
        where = "config/parts.yaml (또는 data/real/config 오버레이) parts"
        out: dict[str, str] = {}
        for new, ent in self.parts.items():
            new = nfc_strip(new)
            olds = ent.get("renamed_from") if isinstance(ent, dict) else None
            if olds is None:
                continue
            if not isinstance(olds, list):
                raise ConfigError(f"{where}.{new}.renamed_from: 형식은 목록([옛 약칭, …]) 이어야 한다 (지금: {type(olds).__name__})")
            for o in olds:
                old = nfc_strip(o)
                if not old or old == new:
                    raise ConfigError(f"{where}.{new}.renamed_from: 옛 약칭이 비었거나 새 약칭과 같다")
                if old in out:
                    raise ConfigError(f"{where}: 옛 약칭 '{old}' 이 두 파트({out[old]}·{new})의 renamed_from 에 있다")
                ent_old = self.parts.get(old)
                if old in self.parts and nfc_strip(ent_old.get("status") if isinstance(ent_old, dict) else None) != "폐기":
                    raise ConfigError(f"{where}.{new}.renamed_from: 옛 약칭 '{old}' 이 parts 에 아직 있다 — 지우거나 'status: 폐기' 로 둔다 "
                                      "(오버레이는 저장소 parts.yaml 의 키를 지울 수 없다)")
                if old in self.bundles or old in self.synthetic_parts:
                    raise ConfigError(f"{where}.{new}.renamed_from: 옛 약칭 '{old}' 이 file_bundles 키·synthetic_parts 에 있다 "
                                      "(묶음 파일 약칭 개명은 지원하지 않는다 — docs/10 3장)")
                out[old] = new
        for old, new in out.items():
            if isinstance(self.parts.get(old), dict) and self.parts[old].get("renamed_from"):
                raise ConfigError(f"{where}.{old}.renamed_from: '{old}' 은 '{new}' 의 옛 약칭이다 — 마지막 약칭 한 곳에 옛 약칭을 모두 적는다 (사슬 없음)")
        return out

    @property
    def known_codes(self) -> set[str]:
        """파일명 약칭으로 인정하는 값 — parts · file_bundles · synthetic_parts · 옛 약칭(renamed_from — 새 약칭으로 읽는다, I31)."""
        return set(self.parts) | set(self.bundles) | self.synthetic_parts | set(self.renames)

    def part_label(self, code: str) -> str:
        name = nfc_strip((self.parts.get(code) or {}).get("name"))
        return f"{name} ({code})" if name else code

    # ---- 파일 ------------------------------------------------------------------
    def discover(self, data_dir: Path) -> list[Path]:
        """조사 폴더 바로 아래의 엑셀 파일 (확장자 대소문자 무관, 잠금 파일 '~$' 제외 — #24)."""
        return sorted(p for p in Path(data_dir).iterdir()
                      if p.is_file() and p.suffix.lower() in EXCEL_SUFFIXES and not p.name.startswith("~$"))

    def parse_name(self, name: str) -> tuple[str | None, str | None, int]:
        """(약칭, 날짜, 사본 번호). 사본 꼬리 '(n)' 이 없거나 정규식에 copy 그룹이 없으면(옛 오버레이) 사본 번호 0 (I31)."""
        m = re.match(self.lcfg["file_name_regex"], unicodedata.normalize("NFC", name))
        if not m:
            return None, None, 0
        return m.group("field"), m.group("date"), int(m.groupdict().get("copy") or 0)

    def file_label(self, name: str, sha: str, used: set[str] | None = None) -> tuple[str, str | None, str | None, int]:
        """(기록용 이름, 약칭, 날짜, 사본 번호). 규칙 밖이거나 모르는 약칭이면 해시 이름 — 인명이 섞였을 수 있는 원래 이름은 남기지 않는다 (#8).
        used: 이번 실행에서 이미 쓴 기록 이름 — 해시 이름이 겹치면(같은 내용 사본) '-2'·'-3' 을 붙인다 (I31; 날짜 8자리 조건 때문에
        유일화한 이름도 파일명 규칙에 맞지 않는다). 규칙 안 이름이 겹치는 것(NFC 로 같아지는 두 이름)도 해시 이름으로 돌린다.
        옛 약칭(parts.yaml renamed_from) 파일명은 원래 이름 그대로 기록하고 약칭은 새 약칭으로 돌려준다 (#25b — 재발송 판정이 옛·새 파일을 잇는다)."""
        used = used if used is not None else set()
        code, date, copy = self.parse_name(name)
        label = unicodedata.normalize("NFC", name)
        if code is not None and code in self.known_codes and Path(name).suffix == ".xlsx" and label not in used:
            return label, self.renames.get(code, code), date, copy
        stem, suffix, n = f"Tool조사_규칙밖_{sha[:10]}", Path(name).suffix.lower(), 1
        label = stem + suffix
        while label in used:
            n += 1
            label = f"{stem}-{n}{suffix}"
        return label, None, None, 0

    def load(self, paths: list[Path], known_tool_keys: set[str] | None = None) -> LoadResult:
        """known_tool_keys: 레지스트리의 활성 툴 키 집합 (run_load 가 넘긴다) — 제조사 접두 흡수의 생존 키 선택에 쓴다
        (레지스트리 ID 유지). 없으면(골든 oracle·단독 호출) 키 모양 규칙만."""
        warnings: list[str] = []
        self.issues: list[dict] = []
        self.known_tool_keys = set(known_tool_keys or ())
        self._seen_keys = set()
        self._key_names = {}
        reports: list[FileReport] = []
        used: set[str] = set()
        for idx, p in enumerate(paths, start=1):
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
            label, code, date, copy = self.file_label(p.name, sha, used)
            used.add(label)
            old = self.parse_name(p.name)[0] if code is not None else None      # 옛 약칭 파일명이면 (#25b)
            reports.append(FileReport(label, sha, code, date, path=p, copy=copy, index=idx,
                                      renamed_from=old if old != code else None))
        # 재발송 (I33): 같은 파트는 (날짜, 새 약칭 파일명인가, 사본 꼬리를 뗀 파일명, 사본 번호) 최신만 — 같은 날짜면 새 약칭 파일명
        # (renamed_from 의 옛 약칭이 아닌 쪽 — 개명 뒤에 받은 파일)이 이기고, 그다음 브라우저 사본 '(n)' 번호가 큰 쪽(나중에 받은 파일).
        # 사본 번호는 꼬리를 뗀 이름이 같은 파일끼리만 순서를 말해 준다 — 옛 약칭 첨부를 두 번 받아 붙은 '(1)' 이 새 약칭 파일을 이기면 안 된다
        # (2026-10-12 재검토 수리: (날짜, 사본 번호, …) 였을 때 옛 약칭 '(1)' 사본이 고친 새 약칭 회신을 '재발송으로 대체' 로 버렸다)
        def newer(r: FileReport) -> tuple:
            base = re.sub(r"\s*\(\d+\)(?=\.[^.]+$)", "", r.name) if r.copy else r.name
            return r.date, r.renamed_from is None, base, r.copy, r.name

        latest: dict[str, FileReport] = {}
        for r in reports:
            if r.field is None:
                continue
            if r.field not in latest or newer(r) > newer(latest[r.field]):
                latest[r.field] = r
        for r in reports:
            if r.field is None:
                warnings.append(f"파일명 규칙 밖: {r.name} — 파트를 알 수 없어 재발송 판정·담당 부서 대조를 하지 않음 "
                                "(파일명 약속: docs/10 5장)")
                r.warnings += 1
            elif latest[r.field] is not r:
                r.superseded_by = latest[r.field].name
                same = " (내용 같음)" if r.sha256 == latest[r.field].sha256 else ""
                warnings.append(f"재발송으로 대체: {r.name} → {r.superseded_by} (적재 안 함){same}")
                r.warnings += 1
        self._same_content(reports, warnings)
        for r in reports:                       # 옛 약칭 파일명을 실제로 적재할 때만 (대체·같은 내용은 위 경고로 충분, #25b)
            if r.renamed_from and r.superseded_by is None and r.duplicate_of is None:
                warnings.append(f"옛 약칭 파일명: {r.name} — 약칭 '{r.renamed_from}' → '{r.field}' 로 읽음 "
                                "(config/parts.yaml renamed_from — 다음 회신부터 새 약칭 파일명으로)")
                r.warnings += 1

        usages: list[UsageRec] = []
        ios: list[IORec] = []
        excluded: list[dict] = []
        for rep in reports:
            if rep.superseded_by or rep.duplicate_of:
                continue
            u, i = self._load_file(rep, warnings, excluded)
            usages += u
            ios += i

        by_name = {r.name: r for r in reports}
        self._cross_file(usages, by_name, warnings)
        alias_map, alias_labels = self._alias_map(warnings)
        tools = self._group_tools(usages, alias_map, alias_labels, by_name, warnings)
        self._resolve_partners(ios, usages, tools, alias_map, warnings)
        self._disambiguate(ios, by_name, warnings)
        candidates = self._candidates(tools)
        partner_rows = self._partner_review(unresolved_partner_summary(ios), tools, alias_map)
        self._unused_alias_entries(tools, alias_map, warnings)
        conflicts = self._conflicts(tools)
        labels = {u.field: self.part_label(u.field) for u in usages if u.field}
        return LoadResult(reports, usages, ios, tools, warnings, excluded, candidates, conflicts, alias_map,
                          self.issues, labels, partner_candidates=partner_rows, part_renames=dict(self.renames))

    def _same_content(self, reports: list[FileReport], warnings: list) -> None:
        """I33 뒤에: 대체되지 않은 파일 가운데 내용(sha256)이 같은 파일은 한 번만 적재한다 — 규칙 안 파일 우선, 다음 입력 순서.
        나머지는 duplicate_of + 경고 '같은 내용 파일' (제외 건수에 넣지 않는다 — I33 과 같은 원칙). 같은 날짜 '(n)' 사본처럼 규칙 안
        같은 약칭이면 이미 I33 이 '(내용 같음)' 으로 처리했다. 두 규칙 안 파일의 약칭이 다르면 어느 파트 파일인지 확인을 덧붙인다.
        I33 이 대체한(버린) 옛 회신과 내용이 같은 파일도 적재하지 않는다 — 탐색기 사본('- 복사본')·다른 약칭으로 저장한 사본으로 옛 데이터가
        다시 들어와 툴사용이 두 번 잡히지 않게 (2026-10-12 검토 수리). 단 그 옛 회신을 대체한 최신 파일 자신(내용이 같은 재발송 —
        I33 '(내용 같음)')이 그 묶음에 있으면 그 파일은 정상이고 나머지만 위 규칙으로 한 번만."""
        groups: dict[str, list[FileReport]] = defaultdict(list)
        for r in reports:
            groups[r.sha256].append(r)
        for group in groups.values():
            live = [r for r in group if r.superseded_by is None]
            stale = [r for r in group if r.superseded_by is not None]
            if stale and live and not {s.superseded_by for s in stale} & {r.name for r in live}:
                src = min(stale, key=lambda r: (r.field is None, r.index))
                for r in live:
                    r.duplicate_of = src.name
                    note = " — 약칭이 다르다, 어느 파트 파일인지 확인" if r.field is not None and r.field != src.field else ""
                    warnings.append(f"같은 내용 파일: {r.name} = {src.name} ({src.name} 은 재발송으로 대체됨 — 적재 안 함){note}")
                    r.warnings += 1
                continue
            if len(live) < 2:
                continue
            keep = min(live, key=lambda r: (r.field is None, r.index))
            for r in live:
                if r is keep:
                    continue
                r.duplicate_of = keep.name
                note = " — 약칭이 다르다, 어느 파트 파일인지 확인" if r.field is not None and keep.field is not None else ""
                warnings.append(f"같은 내용 파일: {r.name} = {keep.name} (한 번만 적재){note}")
                r.warnings += 1

    def _cross_file(self, usages: list[UsageRec], by_name: dict[str, FileReport], warnings: list) -> None:
        """파일 간 같은 (파트, Tool ID) (I36, docs/09 #1 (a)) — 묶음 파일 + 분할 전용 파일, 규칙 밖 파일끼리 등. 둘 다 적재하고 경고한다.

        같은 (파트, id_key(Tool ID)) 가 두 파일 이상에 나오면: 전용 파일(파일 약칭 = 행의 파트) 행이 정확히 하나면 그 행만 원래 키를 쓰고,
        원문 Tool ID 가 실제로 겹치는(레지스트리 키가 같아지는) 나머지 행에 구분 꼬리 reg_tag 를 붙인다 — 규칙 안 파일은 그 파일 약칭
        (parts.yaml 에 있는 값), 규칙 밖 파일은 'file-<sha256 앞 10자>'. 원래 파일명은 꼬리에도 해시 입력에도 쓰지 않는다 (C4).
        표기만 다른 것('MDA-01'/'MDA-1')은 키가 이미 달라 경고만. 경고는 (파트, 파일 쌍)마다 한 줄 (Tool ID 는 _q 로 인용).
        더해서 규칙 밖 파일의 Tool ID 가 규칙 안 파일과 겹치면 경고 (이름이 틀린 재발송·사본 의심 — 둘 다 적재)."""
        groups: dict[tuple[str, str], list[UsageRec]] = defaultdict(list)
        for u in usages:
            groups[(u.field, id_key(u.sw_id))].append(u)
        pairs: dict[tuple[str, str, str], dict] = {}
        for (part, _k), us in sorted(groups.items(), key=lambda kv: kv[0]):
            files = sorted({u.file for u in us})
            if len(files) < 2:
                continue
            homes = [u for u in us if part and by_name[u.file].field == part]
            home = homes[0] if len(homes) == 1 else None
            raw = Counter(u.sw_id for u in us)
            for u in us:
                if u is not home and raw[u.sw_id] >= 2:
                    rep = by_name[u.file]
                    u.reg_tag = rep.field if rep.field is not None else f"file-{rep.sha256[:10]}"
            for fa, fb in combinations(files, 2):
                e = pairs.setdefault((part, fa, fb), {"ids": [], "tags": set()})
                e["ids"].append("=".join(sorted({u.sw_id for u in us if u.file in (fa, fb)})))
                e["tags"] |= {(u.file, u.reg_tag) for u in us if u.file in (fa, fb) and u.reg_tag}
        for (part, fa, fb), e in sorted(pairs.items()):
            ids = e["ids"]
            msg = (f"파일 간 같은 (파트, Tool ID): {part or '(파트 미상)'} — {fa} ↔ {fb} {len(ids)}건 "
                   f"(예: {', '.join(self._q(x) for x in ids[:3])}) — 둘 다 적재")
            if e["tags"]:
                msg += ", 구분 키 " + ", ".join(f"{f} 쪽 '@{t}'" for f, t in sorted(e["tags"]))
            else:
                msg += " (Tool ID 표기가 달라 키는 이미 다름)"
            warnings.append(msg)
            by_name[fa].warnings += 1
            by_name[fb].warnings += 1
        ids_by_file: dict[str, set[str]] = defaultdict(set)
        for u in usages:
            ids_by_file[u.file].add(id_key(u.sw_id))
        for off in sorted(f for f in ids_by_file if by_name[f].field is None):
            for other in sorted(f for f in ids_by_file if by_name[f].field is not None):
                n = len(ids_by_file[off] & ids_by_file[other])
                if n:
                    warnings.append(f"규칙 밖 파일의 Tool ID 가 다른 파일과 겹침: {off} ↔ {other} {n}개 — "
                                    "재발송·사본이면 파일명을 규칙대로 고치세요 (둘 다 적재)")
                    by_name[off].warnings += 1

    def _issue(self, rep: FileReport, sheet: str, row: int | None, tool_id, header: str | None, value, kind: str,
               hint: str) -> None:
        """수정 요청표 한 줄 (값은 사내 파일에만 — diag 는 값을 쓰지 않는다). 인명 유사 값은 싣지 않는다 — 적힌 값은 비우고
        Tool ID 는 PERSON_MASK (행 번호로 찾는다; 표 아래 꼬리말·서명이 Tool ID 칸에 들어간 경우, docs/09 C5·C8)."""
        val = "" if value is None else cell_key(value)
        self.issues.append({"file": rep.name, "part": rep.field, "sheet": sheet, "row": row,
                            "tool_id": self._q(nfc_strip(tool_id)) if tool_id is not None else "",
                            "column": (header or "").rstrip(" *"), "value": "" if self._looks_person(val) else val,
                            "kind": kind, "hint": hint})

    # ---- 시트 읽기 ----------------------------------------------------------------
    def _read_sheet(self, wb, sheet: str, rep: FileReport, warnings: list, excluded: list):
        """([(행 번호, {슬롯: 셀 값})], 이 파일에 있는 슬롯). 빈 행은 건너뛰고, 연속 빈 행이 blank_rows_end 개면 끝으로 본다.
        엑셀 층 신호 (I37): 수식 결과 오류 셀(#N/A 등)은 빈칸으로 보고 행별로 self._err_cells 에 남긴 뒤 열마다 경고 1줄, 캐시 없는 수식
        (self._formula_cells 좌표인데 값이 없음)은 열마다 경고 1줄, 숨긴 행은 self._hidden 에 (경고는 예시 판별 뒤 _load_file 이).
        셋 다 내용 행(빈 행·시트 끝 뒤 행 제외)만 센다 — 끌어 내린 수식만 있는 빈 응답 행은 빈 행이다."""
        fname = rep.name
        actual = resolve_sheet(wb.sheetnames, self.sheet_cands[sheet])
        if actual is None:
            warnings.append(f"시트 없음: {fname} '{sheet}' — 이 시트는 적재하지 않음 (찾은 이름 후보: config/rules.yaml loader.sheets)")
            rep.warnings += 1
            return [], set()
        self._used_sheets.add(actual)
        ws = wb[actual]
        hr, start = self.lcfg["header_row"], self.lcfg["data_start_row"]
        header = [c.value for c in ws[hr]] if ws.max_row >= hr else []
        mapping, by_h = {}, self.spec.by_header(sheet)
        for idx, h in enumerate(header):
            if _blank(h):
                continue
            nh = norm_header(h)
            if nh in self.spec.ignored[sheet]:                                # 의도적 제외 열(문의처 등)은 매핑보다 먼저 — 읽지 않는다 (절대 규칙 5)
                continue
            if nh in by_h:
                col = by_h[nh]
                if col in mapping.values():                                   # #19 중복 헤더 — 앞 열 사용
                    warnings.append(f"중복 헤더: {fname} {sheet} '{self._q(nfc_strip(h))}' — 앞 열만 읽음")
                    rep.warnings += 1
                    continue
                mapping[idx] = col
            else:                                                             # 헤더 칸에 적은 이름도 가린다 (N3)
                warnings.append(f"매핑 안 된 헤더: {fname} {sheet} '{self._q(nfc_strip(h))}'")
                rep.warnings += 1
        present = {c.slot for c in mapping.values()}
        missing = [c.header for c in self.spec.columns[sheet] if c.slot not in present and c.slot not in self.absent_ok]
        if missing:
            warnings.append(f"양식 열 없음: {fname} {sheet} {missing}")
            rep.warnings += 1
        fill = self._merged_fill(ws, start, mapping, fname, sheet, rep, warnings)
        formulas = self._formula_cells.get(actual, set())
        errs: Counter = Counter()                                               # 슬롯 → 오류 칸 수 (I37)
        nocache: Counter = Counter()                                            # 슬롯 → 캐시 없는 수식 칸 수
        hidden: set[int] = set()
        rows, blanks, ended, tail = [], 0, False, []
        for n in range(start, self._last_content_row(ws, start, mapping, fill) + 1):
            v, err_here, nocache_here = {}, {}, []
            for i, c in mapping.items():
                if (n, i) in fill:
                    v[c.slot] = fill[(n, i)]
                    continue
                x = ws.cell(n, i + 1)
                code = excel_error(x)
                if code:
                    v[c.slot], err_here[c.slot] = None, code
                else:
                    v[c.slot] = x.value
                    if x.value is None and (n, i + 1) in formulas:
                        nocache_here.append(c.slot)
            if all(_blank(x) for x in v.values()):
                blanks += 1
                if blanks >= self.lcfg["blank_rows_end"]:
                    ended = True
                continue
            blanks = 0
            if ended:                                                          # #6 빈 행 뒤 내용은 적재 안 함, 기록
                tail.append((n, v))
                continue
            rows.append((n, v))
            if err_here:
                self._err_cells[(sheet, n)] = err_here
                errs.update(err_here.keys())
            nocache.update(nocache_here)
            rd = ws.row_dimensions.get(n)                                      # get — 인덱싱은 빈 행 정보를 새로 만든다
            if rd is not None and rd.hidden:
                hidden.add(n)
        self._hidden[sheet] = hidden
        for col in self.spec.columns[sheet]:                                   # 열 순서대로 한 줄씩 (헤더는 양식 문구 — 값 아님)
            if errs[col.slot]:
                warnings.append(f"수식 오류 셀: {fname} {sheet} '{col.header.rstrip(' *')}' {errs[col.slot]}칸 — 빈칸으로 봄 "
                                "(#N/A·#REF! 등 수식 결과 오류, 수정 요청표에 행별로)")
                rep.warnings += 1
            if nocache[col.slot]:
                warnings.append(f"캐시 없는 수식: {fname} {sheet} '{col.header.rstrip(' *')}' {nocache[col.slot]}칸 — 값을 읽지 못함 "
                                "(엑셀에서 열어 저장하면 읽힘)")
                rep.warnings += 1
        if tail:
            warnings.append(f"빈 행 {self.lcfg['blank_rows_end']}개 뒤 내용 행: {fname} {sheet} {len(tail)}행 — 적재하지 않음 "
                            f"(첫 행 {tail[0][0]})")
            rep.warnings += 1
            for n, tv in tail:
                excluded.append({"file": fname, "sheet": sheet, "row": n, "reason": "빈 행 뒤 내용 행 (시트 끝으로 봄, #6)"})
                rep.excluded += 1
                if self._excluded_person(rep, sheet, n, tv, "빈 행 뒤", warnings, PERSON_TAIL_HINT):    # 표 아래 연락처 꼬리말 — 위로 붙이라고만 하지 않는다
                    continue
                self._issue(rep, sheet, n, None, None, None, "빈 행 뒤 내용",
                            f"빈 행 {self.lcfg['blank_rows_end']}개 이상 뒤에 있어 읽지 않았다 — 빈 행을 지우고 위로 붙여 주세요")
        return rows, present

    @staticmethod
    def _last_content_row(ws, start: int, mapping: dict, fill: dict) -> int:
        """매핑 열에 값이 있는 마지막 행 (병합 채움 포함, 없으면 start - 1) — 그 뒤는 모두 빈 행이라 읽어도 결과가 같다.
        ws.max_row 는 서식만 있는 먼 칸(엑셀 Ctrl+End 가 튀는 칸)까지 세어, 거기까지 ws.cell 로 돌면 칸 객체를 수백만 개 만든다 (docs/09 C7).
        있는 칸만 본다 (openpyxl 일반 모드의 ws._cells — 없으면 max_row 그대로)."""
        cells = getattr(ws, "_cells", None)
        if not isinstance(cells, dict):
            return ws.max_row
        last = max((r for (r, c), x in cells.items() if r >= start and c - 1 in mapping and not _blank(x.value)), default=start - 1)
        return max([last, *(r for r, _i in fill)])

    def _merged_fill(self, ws, start: int, mapping: dict, fname: str, sheet: str, rep: FileReport, warnings: list) -> dict:
        """데이터 영역의 세로 병합 셀은 위(첫) 칸 값으로 채운다 — 범위마다 경고 1회 (docs/09 #4 A)."""
        fill = {}
        cols = set(mapping)
        for rng in ws.merged_cells.ranges:
            if rng.max_row < start or rng.max_row == rng.min_row:
                continue
            idxs = [c - 1 for c in range(rng.min_col, rng.max_col + 1) if c - 1 in cols]
            if not idxs:
                continue
            top_cell = ws.cell(rng.min_row, rng.min_col)
            top = top_cell.value
            if _blank(top) or excel_error(top_cell):                         # 오류 칸은 채우지 않는다 — 첫 칸에서 '수식 오류 셀' 로 센다 (I37)
                continue
            for r in range(max(rng.min_row, start), rng.max_row + 1):
                for i in idxs:
                    fill[(r, i)] = top
            warnings.append(f"병합 셀: {fname} {sheet} {rng.coord} — 위 칸 값으로 채움")
            rep.warnings += 1
        return fill

    def _scan_formulas(self, rep: FileReport, sheets: list[str], warnings: list) -> dict[str, set[tuple[int, int]]]:
        """{시트: 캐시 없는 수식 칸 좌표 (행, 열)} — 데이터 시작 행부터 (I37 ②). 본 로드(data_only)는 수식의 캐시값만 보여 캐시 없는 수식이
        그냥 빈칸이 되고, openpyxl 은 캐시된 빈 문자열(엑셀이 =IFERROR(…,"") 를 저장한 모양)과도 구별하지 못한다 — 시트 XML 을 직접 본다
        (formula_cells_without_cache — 값은 쓰지 않는다). 실패해도 적재는 계속하고 경고 '수식 검사 못 함' (캐시 없는 수식 경고만 빠진다)."""
        if not sheets:
            return {}
        try:
            return formula_cells_without_cache(rep.path, sheets, self.lcfg["data_start_row"])
        except Exception as e:                                          # noqa: BLE001 — 본 로드는 이미 됐다
            warnings.append(f"수식 검사 못 함: {rep.name} — {type(e).__name__} (캐시 없는 수식 경고를 내지 않음, 적재는 계속)")
            rep.warnings += 1
            return {}

    def _extra_sheets(self, wb, rep: FileReport, warnings: list) -> None:
        """양식 밖 시트 (I37) — 읽은 기본정보·입출력 시트, 선택지 시트, rules.yaml loader.other_sheets(작성안내 등, 공백·'*' 무시) 밖의
        내용 있는 시트. 2행 헤더가 기본정보·입출력 양식 열의 절반 이상과 맞으면(헤더 추가 문구 포함) '양식 사본 시트'(+ 수정 요청표),
        아니면 '양식 밖 시트' 경고만. 적재는 하지 않는다 (무엇이 응답인지는 사람이 판단 — HITL). 시트 이름은 _q 로 인용 (인명 가림).
        있는 칸만 훑는다 (ws._cells) — iter_rows 는 max_row × max_column 직사각형의 빈 칸까지 만들어, 서식만 있는 먼 칸 하나에 수 초·수백 MB 가
        든다 (2026-10-12 검토 수리, docs/09 C7)."""
        hr, start = self.lcfg["header_row"], self.lcfg["data_start_row"]
        known = set(self._used_sheets)
        choices = resolve_sheet(wb.sheetnames, self.lcfg["choices_sheet"])
        if choices:
            known.add(choices)
        for ws in wb.worksheets:
            name = ws.title
            if name in known or norm_header(name) in self.other_sheets:
                continue
            cells = getattr(ws, "_cells", None)
            items = (((r, x.value) for (r, _c), x in cells.items()) if isinstance(cells, dict)
                     else ((x.row, x.value) for row in ws.iter_rows() for x in row))
            filled: set[int] = set()
            hdr: set[str] = set()
            for r, v in items:
                if _blank(v):
                    continue
                filled.add(r)
                if r == hr:
                    hdr.add(norm_header(v))
            if not filled:
                continue
            form = [s for s in (USAGE_SHEET, IO_SHEET)
                    if len(hdr & set(self.spec.by_header(s))) * 2 >= len(self.spec.columns[s])]
            state = " (숨김)" if ws.sheet_state != "visible" else ""
            label = self._q(nfc_strip(name))
            if form:
                content = sum(1 for r in filled if r >= start)
                warnings.append(f"양식 사본 시트: {rep.name} '{label}'{state} — {form[0]} 와 같은 헤더, 내용 {content}행, 적재하지 않음")
                self._issue(rep, form[0], None, "", None, None if label == PERSON_MASK else nfc_strip(name), "양식 사본 시트",
                            "응답이 이 시트에 있으면 원래 시트로 옮기고 사본 시트는 지워 주세요 (사본 시트는 읽지 않습니다)")
            else:
                warnings.append(f"양식 밖 시트: {rep.name} '{label}'{state} — 읽지 않음 (아는 시트면 rules.yaml loader.other_sheets 에 추가)")
            rep.warnings += 1

    def _read_choices(self, wb) -> dict[str, list[str]]:
        """{정규화 목록 이름: 값}. 목록 이름 행은 2행 (1행 제목) — 열마다 2행부터 빈칸이 아닌 값을 위에서 아래로, 첫 값이 목록 이름.
        있는 칸만 훑는다 (ws._cells) — max_row × max_column 직사각형을 ws.cell 로 돌면 서식만 있는 먼 칸 하나에 칸 객체 수백만 개·수 초가
        든다 (2026-10-12 재검토 수리, docs/09 C7 — 선택지 시트가 빠져 있었다). _cells 가 없으면(다른 openpyxl 판) 예전처럼 직사각형."""
        name = resolve_sheet(wb.sheetnames, self.lcfg["choices_sheet"])
        if name is None:
            return {}
        ws = wb[name]
        cells = getattr(ws, "_cells", None)
        if isinstance(cells, dict):
            by_col: dict[int, list[tuple[int, str]]] = defaultdict(list)
            for (r, c), x in cells.items():
                if r >= 2 and not _blank(x.value):
                    by_col[c].append((r, nfc_strip(x.value)))
            cols = [[v for _r, v in sorted(by_col[c])] for c in sorted(by_col)]
        else:
            cols = [[nfc_strip(ws.cell(r, c).value) for r in range(2, ws.max_row + 1) if not _blank(ws.cell(r, c).value)]
                    for c in range(1, ws.max_column + 1)]
        out = {}
        for vals in cols:
            if vals:
                out[norm_header(vals[0])] = vals[1:]
        return out

    def _choice_list(self, choices: dict, list_name: str) -> list[str] | None:
        extra = [nfc_strip(x) for x in (self.lcfg.get("extra_choice_values") or {}).get(list_name, [])]
        for cand in self.choice_aliases.get(list_name, [list_name]):
            if norm_header(cand) in choices:
                return choices[norm_header(cand)] + extra
        return None

    def _is_example(self, sheet: str, v: dict) -> bool:
        """적재 열 전체가 템플릿 예시 행과 같은지 (I15) — 위치 무관."""
        cols = [c.slot for c in self.spec.columns[sheet]]
        got = tuple(cell_key(v.get(s)) for s in cols)
        return any(got == tuple(cell_key(ex.get(s)) for s in cols) for ex in self.examples.get(sheet, []))

    def _example_similarity(self, sheet: str, v: dict, present: set) -> tuple[int, int]:
        """(같은 칸 수, 비교한 칸 수) — 예시 가운데 비율이 가장 높은 것 (같으면 비교한 칸이 많은 쪽, 그다음 앞 예시). 없으면 (0, 0).
        비교 칸 = 예시의 정보 열: 예시 값이 비지 않고 빈 값 토큰(I16 — NA·모름 등)도 아니며 이 파일에 있는 열(present). 이런 열이
        example_near_min_cols 보다 적은 예시는 보지 않는다. 값 비교는 _is_example 과 같은 cell_key (I15 개정, docs/09 #3).
        빈 값 토큰 칸을 빼는 이유: 양식 v1.1 TA-01 예시는 절반이 NA·모름이라 NA 투성이 실제 응답이 0.8 을 넘었다."""
        best = (0, 0)
        for ex in self.examples.get(sheet, []):
            eq = n = 0
            for c in self.spec.columns[sheet]:
                e = cell_key(ex.get(c.slot))
                if not e or c.slot not in present or self.norm.is_empty(e):
                    continue
                n += 1
                eq += cell_key(v.get(c.slot)) == e
            if n >= self.near_min_cols and (not best[1] or (eq / n, n) > (best[0] / best[1], best[1])):
                best = (eq, n)
        return best

    def _near_example(self, sheet: str, v: dict, present: set) -> str | None:
        """예시와 거의 같은 행이면 근거 문구('29/30 열 같음', '…, 비고가 예시 문구'), 아니면 None. 정확한 예시(_is_example)는 먼저 걸러 둔다.
        판별: 정보 열 같은 비율 ≥ example_near_ratio, 또는 기본정보 비고가 예시 비고 문구와 같음 (I15 개정)."""
        eq, n = self._example_similarity(sheet, v, present)
        hit = bool(n) and eq / n >= self.near_ratio
        note = sheet == USAGE_SHEET and "note" in present and cell_key(v.get("note")) in self.example_notes
        if not (hit or note):
            return None
        return ", ".join(([f"{eq}/{n} 열 같음"] if n else []) + (["비고가 예시 문구"] if note else []))

    # ---- 셀 규칙 (D5) -------------------------------------------------------------
    def _convert(self, col: Column, value, where: str, warnings: list, rep: FileReport, row: int | None = None, tool_id=None):
        """문자열 슬롯의 숫자·날짜 셀 변환 (I27). 정수 슬롯은 (정수 | None, 원문 | None).
        만료 시기(loader.month_slots)의 **문자열 셀**은 _month_text (I16·I27 — 실수 셀 2027.1 은 아래 실수 경로 그대로; 문자열이 된 뒤에
        정규화하면 '2027-01' 로 잘못 바뀐다). row·tool_id 는 수정 요청표 행용."""
        if col.kind == "int":
            if value is None or (isinstance(value, str) and not value.strip()):
                return None, None
            if isinstance(value, str) and self.norm.is_empty(value):      # 'NA'·'-'·'없음' 은 빈칸 (docs/09 #21 2단) — 경고 없음
                self._na_int_cells += 1
                return None, None
            if isinstance(value, bool):
                return None, str(value)
            if isinstance(value, int):
                return value, None
            if isinstance(value, float) and value.is_integer():
                return int(value), None
            s = nfc_strip(value)
            if re.fullmatch(r"\d+", s):
                return int(s), None
            return None, s if not isinstance(value, float) else repr(value)
        if value is None:
            return None, None
        if isinstance(value, bool):
            return str(value), None
        if isinstance(value, int):
            return str(value), None                       # 정수 — 경고 없음 (선행 0 소실은 탐지 불가)
        if isinstance(value, float):
            if value.is_integer():
                return str(int(value)), None
            warnings.append(f"엑셀 숫자 변환 가능성: {where} {col.header} = {value}")
            rep.warnings += 1
            return repr(value), None
        if isinstance(value, (dt.date, dt.datetime)):
            d = value.date() if isinstance(value, dt.datetime) else value
            if col.slot in self.month_slots:
                return d.strftime("%Y-%m"), None
            warnings.append(f"날짜 셀: {where} {col.header} → {d.isoformat()}")
            rep.warnings += 1
            return d.isoformat(), None
        if col.slot in self.month_slots and isinstance(value, str) and not _blank(value):
            return self._month_text(col, value, where, warnings, rep, row, tool_id), None
        return nfc_strip(value), None

    def _month_text(self, col: Column, value: str, where: str, warnings: list, rep: FileReport, row: int | None, tool_id) -> str | None:
        """만료 시기 문자열 (docs/09 #21 3단, I16·I27). 순서: 값 대응표(value_aliases)에 있는 원문 → 그대로 (대응표가 바꾼다) ·
        빈 값 토큰·loader.month_blank_values('영구') → 빈칸 (원문 없음, 파일당 한 줄) · 이미 YYYY-MM → 그대로 · 텍스트 날짜
        (2027.03·2027/3·2027-03-31·2027. 3. 31.·2027년 3월) → YYYY-MM + 경고 '만료 시기 표기 변환' · 그 밖 → 원문 보존 + 경고
        '만료 시기 형식 아님' + 수정 요청표 '만료 시기 형식' (인명 유사면 값 생략 — 스키마 층(Pydantic·SHACL)도 계속 위반으로 본다, D4)."""
        s = nfc_strip(value)
        if s in self.value_aliases.get(col.slot, {}):
            return s
        if self.norm.is_empty(s) or nfkc(s).strip().lower() in self.month_blank:
            self._na_month_cells += 1
            return None
        ym = month_text(s)
        if ym == s:                                                      # 이미 YYYY-MM (스키마 패턴) — 경고 없음
            return s
        if ym:
            warnings.append(f"만료 시기 표기 변환: {where} '{self._q(s)}' → '{ym}'")
            rep.warnings += 1
            return ym
        warnings.append(f"만료 시기 형식 아님: {where} '{self._q(s)}' — 원문 보존 (YYYY-MM 으로)")
        rep.warnings += 1
        if row is not None:
            self._issue(rep, col.sheet, row, tool_id, col.header, None if self._looks_person(s) else s, "만료 시기 형식",
                        "YYYY-MM 으로 적어 주세요 (예: 2027-03). 영구면 비워 두세요")
        return s

    def _apply_value_aliases(self, v: dict, rep: FileReport) -> int:
        n = 0
        for slot, mapping in self.value_aliases.items():
            val = v.get(slot)
            if isinstance(val, str) and nfc_strip(val) in mapping:
                v[slot] = mapping[nfc_strip(val)]
                n += 1
        return n

    def _person_hit(self, slot: str, val) -> bool:
        """인명 유사 패턴 (D6·I29) — 자유 텍스트 슬롯(free_text_slots)은 person_pattern 도, 모든 문자열 칸은 person_patterns_all.
        경고·수정 요청은 부르는 쪽이 (_check · _excluded_person). 값 인용 가림(_q)은 두 목록을 모든 칸에 쓴다 (더 넓다)."""
        return isinstance(val, str) and not _blank(val) and (
            (slot in self.free_text and bool(self.person_re.search(val))) or any(p.search(val) for p in self.person_all))

    def _excluded_person(self, rep: FileReport, sheet: str, n: int, raw: dict, why: str, warnings: list,
                         hint: str = PERSON_ROW_HINT) -> bool:
        """제외하는 내용 행의 인명 검사 (I22·I29, docs/09 #20 수리 계획 2 — Tool ID 없음·Tool ID 수식 오류·빈 행 뒤). 걸린 칸마다 경고
        '인명 유사 패턴: <파일> <시트> <n>행 (<why>) '<열>'' (값·Tool ID 를 옮기지 않는다 — 행 번호로 찾는다) + 그 행의 수정 요청 '인명 유사'
        한 줄 → True. 부르는 쪽은 True 면 그 행의 원래 요청('Tool ID 없음' 등)을 내지 않는다 — 표 아래 연락처 꼬리말에 'Tool ID 를 적어 주세요'
        라고 시키면 다음 적재에서 인명이 그래프·레지스트리에 들어간다 (2026-10-12 재검토 수리). raw = 원문 셀 (변환 전 — 정수 열 문자열 포함)."""
        hits = [c.header for c in self.spec.columns[sheet] if self._person_hit(c.slot, raw.get(c.slot))]
        if not hits:
            return False
        for h in hits:
            warnings.append(f"인명 유사 패턴: {rep.name} {sheet} {n}행 ({why}) '{h}'")
            rep.warnings += 1
        self._issue(rep, sheet, n, "", " · ".join(h.rstrip(" *") for h in hits), None, "인명 유사", hint)
        return True

    def _check(self, sheet: str, v: dict, present: set, choices: dict, where: str, warnings: list, rep: FileReport,
               row: int, tool_id, missing_lists: set, err_slots=(), raw_text: dict | None = None) -> None:
        """err_slots: 수식 오류로 빈칸이 된 슬롯 (I37) — 필수값 누락 경고는 내되 수정 요청은 '수식 오류 셀' 한 행만 (중복 방지).
        raw_text: 정수 변환에 실패해 값이 빈칸이 된 슬롯의 원문 (사용 인원수·보유 수량) — 인명 검사는 그 원문을 본다 (I29 '적재하는 모든
        문자열 열' — 원문은 그래프 <슬롯>_raw 로 적재된다, 2026-10-12 재검토 수리)."""
        raw_text = raw_text or {}
        for col in self.spec.columns[sheet]:
            if col.slot not in present:
                continue
            val = v.get(col.slot)
            if col.required and _blank(val):
                warnings.append(f"필수값 누락: {where} '{col.header}'")
                rep.warnings += 1
                if col.slot not in err_slots:
                    self._issue(rep, sheet, row, tool_id, col.header, None, "필수값 누락", "빈칸 — 값을 적거나 '모름'을 고르세요")
                continue
            if col.choice_list and not _blank(val) and choices:
                lst = self._choice_list(choices, col.choice_list)
                if lst is None:
                    if col.choice_list not in missing_lists:
                        missing_lists.add(col.choice_list)
                        warnings.append(f"선택지 목록 없음: {rep.name} '{col.choice_list}' — '{col.header}' 열은 선택지 검사를 하지 않음")
                        rep.warnings += 1
                elif str(val) not in lst and self.norm.is_empty(val):
                    self._na_cells += 1       # 'NA'·'-' 등 — 양식 v1.1 안내가 'NA' 를 쓰라고 한다. 경고 대신 파일당 한 줄 (#21)
                elif str(val) not in lst:
                    warnings.append(f"선택지 밖 값: {where} '{col.header}' = '{self._q(val)}'")
                    rep.warnings += 1
                    self._issue(rep, sheet, row, tool_id, col.header, val, "선택지 밖 값",
                                "드롭다운에서 고르세요. 목록에 없으면 '기타'를 고르고 비고에 적어 주세요")
            if self._person_hit(col.slot, val if isinstance(val, str) else raw_text.get(col.slot)):
                warnings.append(f"인명 유사 패턴: {where} '{col.header}'")      # where 의 Tool ID·데이터명은 이미 _q (그 칸이 걸려도 값이 안 옮겨진다)
                rep.warnings += 1
                self._issue(rep, sheet, row, tool_id, col.header, None, "인명 유사",
                            "사람 이름·연락처로 보이는 내용 — 지워 주세요 (인명은 저장하지 않습니다)")

    # ---- 파일 1개 -----------------------------------------------------------------
    def _load_file(self, rep: FileReport, warnings: list, excluded: list):
        fname = rep.name
        try:
            if rep.path.suffix.lower() != ".xlsx":
                raise ValueError(f"{rep.path.suffix} 형식 — .xlsx 로 다시 저장해야 한다")
            wb = openpyxl.load_workbook(rep.path, data_only=True)       # 일반 모드 — 병합 범위·실제 크기를 본다 (#4·#5)
        except Exception as e:                                          # #7 읽을 수 없는 파일은 건너뛰고 계속
            # 예외 문구에는 원래 경로·파일명(인명 가능)이 들어갈 수 있어 종류만 남긴다 (#8)
            rep.unreadable = str(e) if isinstance(e, ValueError) and str(e).startswith(".") else type(e).__name__
            warnings.append(f"읽을 수 없는 파일: {fname} — {rep.unreadable} (적재 안 함, 이번 실행은 폐기 판정을 하지 않음)")
            rep.warnings += 1
            return [], []
        # 엑셀 층 신호 (I37) — 파일마다 새로: 수식 칸 좌표·오류 칸·숨긴 행·읽은 시트
        self._err_cells: dict[tuple[str, int], dict[str, str]] = {}
        self._hidden: dict[str, set[int]] = {}
        self._used_sheets: set[str] = set()
        self._formula_cells = self._scan_formulas(rep, [s for s in (resolve_sheet(wb.sheetnames, self.sheet_cands[k])
                                                                    for k in (USAGE_SHEET, IO_SHEET)) if s], warnings)
        try:
            choices = self._read_choices(wb)
            if not choices:
                warnings.append(f"선택지 시트 없음: {fname} — 선택지 검사를 하지 않음")
                rep.warnings += 1
            urows, upresent = self._read_sheet(wb, USAGE_SHEET, rep, warnings, excluded)
            irows, ipresent = self._read_sheet(wb, IO_SHEET, rep, warnings, excluded)
            self._extra_sheets(wb, rep, warnings)
        finally:
            wb.close()
        cols_u = {c.slot: c for c in self.spec.columns[USAGE_SHEET]}
        cols_i = {c.slot: c for c in self.spec.columns[IO_SHEET]}
        missing_lists: set = set()
        aliased = 0
        self._na_cells = 0
        self._na_int_cells = 0
        self._na_month_cells = 0

        def exclude(sheet, row, reason):
            excluded.append({"file": fname, "sheet": sheet, "row": row, "reason": reason})
            rep.excluded += 1

        # 엑셀 층 신호의 행 단위 처리 (I37) — 예시 행(정확 일치)을 거른 뒤의 응답 행만
        hidden_seen: dict[str, list[int]] = {USAGE_SHEET: [], IO_SHEET: []}

        def excel_rows(sheet: str, n: int, raw: dict, id_slot: str) -> bool:
            """숨긴 행 기록 + 수식 오류 칸의 수정 요청 행. Tool ID 칸이 오류면 행을 제외하고 True (입출력은 이어받기 대상도 아님) —
            그 행이 인명 유사면 수정 요청은 '인명 유사' 한 줄 (_excluded_person)."""
            tool_id = raw.get(id_slot)
            if n in self._hidden.get(sheet, ()):
                hidden_seen[sheet].append(n)
                self._issue(rep, sheet, n, tool_id, None, None, "숨긴 행",
                            "숨긴 행도 응답으로 읽었습니다 — 지울 행이면 행 삭제, 아니면 숨기기 해제")
            errs = self._err_cells.get((sheet, n), {})
            cols = cols_u if sheet == USAGE_SHEET else cols_i
            if id_slot in errs:
                exclude(sheet, n, "Tool ID 수식 오류 (I37)")
                if not self._excluded_person(rep, sheet, n, raw, "Tool ID 수식 오류", warnings):
                    self._issue(rep, sheet, n, "", cols[id_slot].header, errs[id_slot], "수식 오류 셀",
                                "Tool ID 칸이 수식 오류(#N/A 등)입니다 — Tool ID 를 값으로 적어 주세요")
                return True
            for slot, code in errs.items():
                self._issue(rep, sheet, n, tool_id, cols[slot].header, code, "수식 오류 셀",
                            "수식 결과가 오류(#N/A 등)라 빈칸으로 읽었습니다 — 값을 직접 적거나 수식을 고쳐 주세요")
            return False

        # 예시 행 (I15): 시트별 정확 일치·유사 행 수 — 끝에서 설정 낡음 점검. 기본정보 유사 행의 수정 요청 행은 교체되면 종류를 바꾼다
        n_exact = {USAGE_SHEET: 0, IO_SHEET: 0}
        n_near = {USAGE_SHEET: 0, IO_SHEET: 0}
        near_issue: dict[int, dict] = {}

        def near_check(sheet: str, n: int, raw: dict, present: set, tool_id) -> str | None:
            """예시와 거의 같은 행이면 경고·수정 요청 후 근거 문구 (원문 셀 기준 — 병합 채움 뒤·값 대응표 전, 값은 인용하지 않는다)."""
            near = self._near_example(sheet, raw, present)
            if near:
                n_near[sheet] += 1
                warnings.append(f"예시와 거의 같은 행: {fname} {sheet} {n}행 ({near}) — 응답으로 적재, 양식 예시가 남은 것인지 확인")
                rep.warnings += 1
                self._issue(rep, sheet, n, tool_id, None, None, "예시와 거의 같은 행",
                            "양식 예시와 거의 같습니다 — 남은 예시면 지우고, 실제 응답이면 예시 문구(비고 등)를 실제 내용으로 고쳐 주세요")
                if sheet == USAGE_SHEET:
                    near_issue[n] = self.issues[-1]
            return near

        usages, by_id = [], {}
        for n, raw in urows:
            if self._is_example(USAGE_SHEET, raw):
                exclude(USAGE_SHEET, n, "템플릿 예시 행 (내용 일치, I15)")
                n_exact[USAGE_SHEET] += 1
                continue
            near = near_check(USAGE_SHEET, n, raw, upresent, raw.get("source_key"))
            if excel_rows(USAGE_SHEET, n, raw, "source_key"):
                continue
            if _blank(raw.get("source_key")):
                name = nfc_strip(raw.get("reported_tool_name"))
                warnings.append(f"SW ID 없는 내용 행: {fname} {USAGE_SHEET} '{self._q(name)}' — 건너뜀")
                rep.warnings += 1
                exclude(USAGE_SHEET, n, "SW ID 없음 (I22)")
                if not self._excluded_person(rep, USAGE_SHEET, n, raw, "Tool ID 없음", warnings):    # 연락처 꼬리말에 ID 를 붙이라 하지 않는다
                    self._issue(rep, USAGE_SHEET, n, "", "Tool ID", None, "Tool ID 없음", "Tool ID(부서약칭-번호)를 적어 주세요")
                continue
            # 경고 위치 문구 — 값(Tool ID)은 _q 로 (표 아래 꼬리말·서명이 Tool ID 칸에 들어갈 수 있다, C5·C8). 이 행의 모든 경고가 쓴다
            where = f"{fname} {USAGE_SHEET} {self._q(cell_key(raw.get('source_key')))}"
            v, rawvals = {}, {}
            for slot, val in raw.items():
                v[slot], r = self._convert(cols_u[slot], val, where, warnings, rep, n, raw.get("source_key"))
                if r is not None:
                    rawvals[slot] = r
            aliased += self._apply_value_aliases(v, rep)
            self._check(USAGE_SHEET, v, upresent, choices, where, warnings, rep, n, v.get("source_key"), missing_lists,
                        self._err_cells.get((USAGE_SHEET, n), {}), raw_text=rawvals)
            u = UsageRec(fname, rep.field, n, v, rawvals, part=self._part_of(rep, v.get("source_key"), warnings, n),
                         near_example=near)
            k = id_key(u.sw_id)
            if k in by_id:
                prev = by_id[k]
                if not (prev.near_example and not near):              # 보통: 먼저 나온 행 사용 (docs/02 5장 4)
                    warnings.append(f"중복 SW ID: {fname} {self._q(u.sw_id)} — 먼저 나온 행 사용, "
                                    f"'{self._q(nfc_strip(v.get('reported_tool_name')))}' 행 제외")
                    rep.warnings += 1
                    exclude(USAGE_SHEET, n, f"중복 SW ID {self._q(u.sw_id)} (먼저 나온 {prev.row}행 사용)")
                    self._issue(rep, USAGE_SHEET, n, u.sw_id, "Tool ID", u.sw_id, "Tool ID 중복",
                                f"{prev.row}행과 같은 Tool ID — 번호를 다르게 해 주세요")
                    continue
                # 예외 (I15 개정, Leo #3 A): 앞 행이 예시 유사이고 이 행은 아니면 — 고쳐 남긴 예시가 진짜 행을 밀어내지 않게 앞 행을 뺀다.
                # 입출력 소유는 툴사용을 다 읽은 뒤 by_id 로 정하므로 이 행으로 붙는다. 아래 공통 경로(담당 부서·정수 변환 경고·등록)로 이어진다.
                usages.remove(prev)
                rep.usage_rows -= 1
                exclude(USAGE_SHEET, prev.row, f"SW ID 중복 — 예시와 거의 같은 행이라 제외 ({n}행 사용, #3)")
                warnings.append(f"중복 SW ID — 예시 유사 행 제외: {fname} {self._q(u.sw_id)} — {prev.row}행(예시와 {prev.near_example}) 제외, "
                                f"'{self._q(nfc_strip(v.get('reported_tool_name')))}'({n}행) 사용")
                rep.warnings += 1
                if prev.row in near_issue:
                    near_issue[prev.row].update(kind="예시 행 남음",
                                                hint=f"양식 예시를 고쳐 남긴 행으로 보여 같은 Tool ID 의 {n}행을 썼습니다 — 예시 행을 지워 주세요")
            dom = nfc_strip(v.get("reported_domain"))
            allowed = self._domains(u.part)
            if u.part and dom and allowed and dom not in allowed:
                warnings.append(f"파일 분야 ≠ 담당 부서: {fname} {self._q(u.sw_id)} → '{self._q(dom)}'")
                rep.warnings += 1
            for slot, r in rawvals.items():
                warnings.append(f"{cols_u[slot].header.rstrip(' *')} 정수 변환 실패: {fname} {self._q(u.sw_id)} '{self._q(r)}' — 원문 보존")
                rep.warnings += 1
            by_id[k] = u
            usages.append(u)
            rep.usage_rows += 1

        ios = []
        fill_down = bool(self.lcfg.get("io_id_fill_down"))
        prev_n, prev_id = None, None                                 # 바로 위 행의 Tool ID (I22 — ID 이어받기)
        for n, raw in irows:
            if self._is_example(IO_SHEET, raw):
                exclude(IO_SHEET, n, "템플릿 예시 행 (내용 일치, I15)")
                n_exact[IO_SHEET] += 1
                prev_n = prev_id = None
                continue
            near = near_check(IO_SHEET, n, raw, ipresent, raw.get("owner_source_key"))   # 응답이므로 이어받기를 끊지 않는다 (I22)
            if excel_rows(IO_SHEET, n, raw, "owner_source_key"):
                prev_n = prev_id = None                              # Tool ID 오류 행은 이어받지도 넘겨주지도 않는다 (I22 보호, I37)
                continue
            if _blank(raw.get("owner_source_key")) and fill_down and prev_id is not None and prev_n == n - 1:
                # 같은 툴의 입출력을 여러 행에 적으며 첫 행에만 ID 를 적은 경우 (Leo 2026-10-09) — 바로 위 행과 붙어 있을 때만
                raw = {**raw, "owner_source_key": prev_id}
                warnings.append(f"Tool ID 이어받음: {fname} {IO_SHEET} '{self._q(nfc_strip(raw.get('data_name')))}' → "
                                f"'{self._q(nfc_strip(prev_id))}' (바로 위 행)")
                rep.warnings += 1
            if _blank(raw.get("owner_source_key")):
                prev_n = prev_id = None
                warnings.append(f"SW ID 없는 내용 행: {fname} {IO_SHEET} '{self._q(nfc_strip(raw.get('data_name')))}' — 건너뜀")
                rep.warnings += 1
                exclude(IO_SHEET, n, "SW ID 없음 (I22)")
                if not self._excluded_person(rep, IO_SHEET, n, raw, "Tool ID 없음", warnings):
                    self._issue(rep, IO_SHEET, n, "", "Tool ID", None, "Tool ID 없음",
                                "이 입출력이 어느 Tool 것인지 Tool ID 를 적어 주세요")
                continue
            prev_n, prev_id = n, raw.get("owner_source_key")
            where = f"{fname} {IO_SHEET} {self._q(cell_key(raw.get('owner_source_key')))} '{self._q(cell_key(raw.get('data_name')))}'"
            v = {}
            for slot, val in raw.items():
                v[slot], _ = self._convert(cols_i[slot], val, where, warnings, rep, n, raw.get("owner_source_key"))
            aliased += self._apply_value_aliases(v, rep)
            self._check(IO_SHEET, v, ipresent, choices, where, warnings, rep, n, v.get("owner_source_key"), missing_lists,
                        self._err_cells.get((IO_SHEET, n), {}))
            sw = nfc_strip(v.get("owner_source_key"))
            owner = by_id.get(id_key(sw))                            # D3: 소유는 같은 파일 안에서 (#18 표기 차이 흡수)
            dval = nfc_strip(v.get("direction"))
            x = IORec(fname, rep.field, n, v, owner, self.dir_short.get(dval, "?"), near_example=near)
            if owner is None:
                warnings.append(f"고아 입출력: {fname} SW ID '{self._q(sw)}' ({self._q(x.name)}) — SW기본정보에 없음")
                rep.warnings += 1
                self._issue(rep, IO_SHEET, n, sw, "Tool ID", sw, "Tool ID 가 기본정보에 없음",
                            "Tool 기본정보 시트의 Tool ID 와 똑같이 적어 주세요")
            elif owner.sw_id != sw:
                warnings.append(f"Tool ID 표기 차이: {fname} '{self._q(sw)}' → '{self._q(owner.sw_id)}' 로 연결")
                rep.warnings += 1
            if dval and x.direction_short == "?":                      # #11 방향을 못 읽으면 연결 계산에서 빠진다
                warnings.append(f"방향 값 인식 못 함: {where} '{self._q(dval)}' — 연결 계산에서 빠짐 (config/value_aliases.yaml 로 대응)")
                rep.warnings += 1
            x.exts, x.inhouse, x.bad_ext = self.norm.extensions(v.get("extensions_raw"))
            self._check_extensions(rep, x, n, sw, cols_i["extensions_raw"].header, warnings)
            x.partner_names = self.norm.split_partners(v.get("partner_raw"))
            ios.append(x)
            rep.io_rows += 1
        # 설정 낡음 점검 (I15 개정, docs/09 #3c) — 시트별: 파일 단위면 입출력 예시가 정확히 맞아 기본정보 예시만 어긋난 양식을 놓친다
        for sh in (USAGE_SHEET, IO_SHEET):
            if n_near[sh] and not n_exact[sh]:
                warnings.append(f"예시 행 판별 설정 점검: {fname} {sh} — 예시와 정확히 같은 행 0, 거의 같은 행 {n_near[sh]} → "
                                "예시를 고쳐 남긴 것이 아니면 config/template_examples.yaml 이 이 파일의 양식과 다를 수 있음 "
                                "(양식판 확인 · template-examples --form <양식> --overlay)")
                rep.warnings += 1
        if aliased:
            warnings.append(f"값 대응표 적용: {fname} {aliased}건 (config/value_aliases.yaml)")
            rep.warnings += 1
        if self._na_cells:
            warnings.append(f"빈 값 표기(NA·-·해당없음 등) 드롭다운 칸: {fname} {self._na_cells}칸 — 선택지 검사에서 뺌 (원문 보존)")
            rep.warnings += 1
        if self._na_int_cells:
            warnings.append(f"빈 값 표기 정수 칸: {fname} {self._na_int_cells}칸 — 빈칸으로 봄 (docs/09 #21)")
            rep.warnings += 1
        if self._na_month_cells:
            warnings.append(f"빈 값 표기 만료 시기: {fname} {self._na_month_cells}칸 — 빈칸으로 봄 ('영구'·NA·- 등, docs/09 #21)")
            rep.warnings += 1
        for sh in (USAGE_SHEET, IO_SHEET):                                  # I37 — 숨긴 행은 적재하고 시트마다 한 줄
            if hidden_seen[sh]:
                warnings.append(f"숨긴 행: {fname} {sh} {len(hidden_seen[sh])}행 — 응답으로 적재함 (첫 행 {hidden_seen[sh][0]})")
                rep.warnings += 1
        if rep.usage_rows == 0:                                             # I37 — 예시만 남았거나 시트·헤더가 양식과 다름
            warnings.append(f"툴사용 0건: {fname} — 기본정보 시트에서 적재한 행이 없음 (예시만 남았거나 시트·헤더가 양식과 다름)")
            rep.warnings += 1
            self._issue(rep, USAGE_SHEET, None, "", None, None, "툴사용 0건",
                        "응답 행이 하나도 읽히지 않았습니다 — 시트 이름·헤더를 양식대로 두고 예시 아래에 적어 주세요")
        # 입출력이 하나도 없는 툴사용 — 정상 고립일 수 있어 '확인 요청' 으로만 수정 요청표에 싣는다 (docs/11 3장 6번, 경고 아님)
        owners = {id(x.owner) for x in ios if x.owner is not None}
        for u in usages:
            if id(u) not in owners:
                self._issue(rep, USAGE_SHEET, u.row, u.sw_id, "Tool ID", None, "입출력 없음",
                            "확인 요청 — 정상일 수 있음: 이 Tool 의 입출력이 Tool 입출력 시트에 없습니다. "
                            "주고받는 데이터가 있으면 적어 주세요 (없으면 그대로 두셔도 됩니다)")
        return usages, ios

    def _part_of(self, rep: FileReport, tool_id, warnings: list, row: int) -> str | None:
        """행의 파트: 보통 파일 약칭, 묶음 파일(parts.yaml file_bundles)은 Tool ID 앞부분 (docs/10 3-1).
        앞부분이 옛 약칭(renamed_from)이면 새 약칭으로 — 묶음 안 파트를 개명해도 행의 옛 Tool ID 를 그대로 받는다 (#25b;
        file_bundles 목록에 옛 약칭이 남아 있어도 같은 결과)."""
        if rep.field not in self.bundles:
            return rep.field
        prefix = id_key(tool_id).split("-")[0]
        prefix = self.renames.get(prefix, prefix)
        if prefix in {self.renames.get(p, p) for p in self.bundles[rep.field]}:
            return prefix
        warnings.append(f"묶음 파일 파트 미정: {rep.name} {self._q(nfc_strip(tool_id))} — Tool ID 앞부분이 {self.bundles[rep.field]} 가 아님, "
                        f"'{rep.field}' 로 적재")
        rep.warnings += 1
        self._issue(rep, USAGE_SHEET, row, tool_id, "Tool ID", tool_id, "묶음 파일 파트 미정",
                    f"Tool ID 를 {' 또는 '.join(p + '-번호' for p in self.bundles[rep.field])} 로 적어 주세요")
        return rep.field

    def _domains(self, part: str | None) -> list[str]:
        """파트의 허용 '담당 부서' 값. 설정에 없는 파트(합성 데이터)는 약칭 = 담당 부서 값 체계."""
        if part in self.parts:
            return [nfc_strip(d) for d in (self.parts[part].get("domains") or [])]
        return [part] if part else []

    def _check_extensions(self, rep: FileReport, x: IORec, row: int, sw: str, header: str, warnings: list) -> None:
        """확장자 칸의 경고·수정 요청 (I12, docs/09 #10). 값은 원문 보존 — 매핑 못 한 토큰은 경고 '확장자 매핑 실패',
        묶음 목록 밖 다중 점 토큰('model.stp')은 값은 쓰고 경고 '확장자 다중 점 확인'. 둘 다 수정 요청표에 '확장자 확인' 한 행.
        칸이 인명 유사면 토큰·적힌 값을 옮기지 않는다 (데이터명도 _q 로 가린다)."""
        raw = nfc_strip(x.v.get("extensions_raw"))
        masked = self._looks_person(raw)
        multi = self.norm.unknown_compound(x.exts)
        if x.bad_ext:
            warnings.append(f"확장자 매핑 실패: {rep.name} {self._q(sw)} '{self._q(x.name)}' 토큰 {PERSON_MASK if masked else x.bad_ext} — 원문 보존")
            rep.warnings += 1
        if multi:
            warnings.append(f"확장자 다중 점 확인: {rep.name} {self._q(sw)} '{self._q(x.name)}' 토큰 {PERSON_MASK if masked else multi} — 그대로 사용 "
                            "(묶음 확장자면 extensions.yaml compound_extensions 에 추가)")
            rep.warnings += 1
        hints = []
        if x.bad_ext:
            hints.append("확장자로 읽지 못한 말이 있습니다 — '.stp / .csv' 처럼 확장자만 적어 주세요 (형식 이름은 괄호 안에 .확장자: Parasolid(.x_t))")
        if multi:
            hints.append("파일 이름이 아니라 확장자만 적어 주세요 (예: model.stp → .stp). tar.gz 같은 묶음 확장자면 그대로 두세요")
        if hints:
            self._issue(rep, IO_SHEET, row, sw, header, None if masked else raw, "확장자 확인", " / ".join(hints))

    # ---- 툴 통합 (6.1) --------------------------------------------------------------
    def _alias_map(self, warnings: list | None = None) -> tuple[dict[str, str], dict[str, str]]:
        """정규화 키 → 대표 키, 대표 키 → 대표 이름 (config/tool_aliases.yaml + 오버레이).

        - aliases (이름 기반, 손으로 적는 것): 변형 표기의 키 → 대표 이름의 키, 대표 이름은 라벨
        - merge_pairs (apply-review 의 판정 이력, docs/09 #2 A): 키가 있으면 (빈 목록이어도) 여기서 merge_keys 를 다시 계산해 쓴다 —
          손으로 고친 이력이 조용히 무시되지 않게. 어느 파일의 merge_keys 가 자기 이력과 다르면 경고 (다음 apply-review 저장이 파일을
          맞춘다). 이력 키가 없고 merge_keys 만 있는 옛 파일은 merge_keys 그대로 (B 키 → A 키, 생존 키 = A, TOOL ID 유지).
        - labels: 키 → 대표 이름 (apply-review 의 '대표 이름' — 판정 당시의 대표 키에 적혀 있고 옮기지 않는다)
        합친 뒤 추이적으로 닫는다 (A→B, B→C 면 A→C). 손으로 고친 파일의 순환은 경고하고 가장 작은 키를 대표로 (#14).
        그룹의 대표 이름: labels[대표 키] 가 있으면 그것, 없으면 그룹 키 가운데 merge_pairs 에서 **가장 최근에 A 키로 적힌** 키의 라벨,
        그다음 키 정렬 순 첫 라벨 (라벨이 전혀 없으면 ToolGroup 이 다수결 표기). 별개로 되돌리면 각 키는 자기 라벨로 돌아간다."""
        amap, labels = {}, {}
        for rep_name, variants in (self.aliases_cfg.get("aliases") or {}).items():
            rk = self.norm.tool_key(rep_name)
            if not rk:
                continue
            labels[rk] = nfc_strip(rep_name)
            for name in variants or []:
                vk = self.norm.tool_key(name)
                if vk and vk != rk:
                    amap[vk] = rk
        file_mk = {nfc_strip(b): nfc_strip(a) for b, a in (self.aliases_cfg.get("merge_keys") or {}).items()}
        pairs = read_merge_pairs(self.aliases_cfg, promote=False)
        # merge_pairs **키가 있으면** (빈 목록이어도 — `merge_pairs: []` 로 비운 파일은 통합 0) 거기서 다시 계산, 키가 없는 옛 파일만 merge_keys
        merge_keys = merge_keys_from_pairs(pairs) if "merge_pairs" in self.aliases_cfg else file_mk
        if warnings is not None and self._merge_keys_stale():
            warnings.append("손으로 고친 merge_pairs — merge_keys 재계산 (다음 apply-review 가 파일을 맞춘다)")
        for b, a in merge_keys.items():
            if b and a and b != a:
                amap[b] = a
        for k, name in (self.aliases_cfg.get("labels") or {}).items():
            if nfc_strip(name):
                labels[nfc_strip(k)] = nfc_strip(name)

        def root(k: str) -> str:
            path = [k]
            while path[-1] in amap:
                nxt = amap[path[-1]]
                if nxt in path:                                  # 순환 — 손으로 고친 파일에서만 생길 수 있다
                    cyc = sorted(path[path.index(nxt):])
                    if warnings is not None:                     # 키는 _q — 툴 이름 키에 '이름+직급' 이 남을 수 있다 (2026-10-12 재검토 수리)
                        warnings.append(f"툴 별칭 순환: {' ↔ '.join(self._q(k) for k in cyc)} — 가장 작은 키 '{self._q(cyc[0])}' 를 대표로 "
                                        "(config/tool_aliases.yaml 확인)")
                    return cyc[0]
                path.append(nxt)
            return path[-1]

        closed = {k: root(k) for k in list(amap)}
        closed = {k: v for k, v in closed.items() if k != v}
        distinct = {tuple(sorted(p)) for p in (self.aliases_cfg.get("distinct") or [])}
        for k, v in closed.items():
            if tuple(sorted((k, v))) in distinct and warnings is not None:
                warnings.append(f"툴 별칭과 별개 판정이 충돌: {self._q(k)} / {self._q(v)} — 통합이 적용됨 (config/tool_aliases.yaml distinct 확인)")
        # 그룹 대표 이름 — 대표 키에 라벨이 없으면 그룹 키 가운데 이력에서 가장 최근에 A 키로 적힌 것 → 키 정렬 순
        groups: dict[str, set[str]] = defaultdict(set)
        for k, v in closed.items():
            groups[v].add(k)
        recent = {a: i for i, (a, _b) in enumerate(pairs)}        # 뒤에 적힌 것이 최근
        for rep, members in groups.items():
            if rep in labels:
                continue
            order = sorted((k for k in members if k in recent), key=lambda k: -recent[k]) + sorted(k for k in members if k not in recent)
            for k in order:
                if k in labels:
                    labels[rep] = labels[k]
                    break
        return closed, labels

    def _merge_keys_stale(self) -> bool:
        """설정 파일(저장소 config/ 와 오버레이) 가운데 merge_keys 가 자기 merge_pairs 에서 계산한 것과 다른 파일이 있는가 —
        손으로 고친 이력. 합친 설정(merge_config)은 merge_keys 를 다시 계산해 주므로 파일마다 원문을 따로 본다."""
        for d in (self.config_dir, self.overlay_dir):
            path = Path(d) / "tool_aliases.yaml" if d else None
            if path is None or not path.is_file():
                continue
            raw = read_yaml(path)
            if "merge_pairs" not in raw:
                continue
            mk = {nfc_strip(b): nfc_strip(a) for b, a in (raw.get("merge_keys") or {}).items()}
            if merge_keys_from_pairs(read_merge_pairs(raw, promote=False)) != {b: a for b, a in mk.items() if b and a}:
                return True
        return False

    def _group_tools(self, usages, amap, labels, reports: dict | None = None, warnings: list | None = None) -> dict[str, ToolGroup]:
        """툴사용 → 툴 키 (6.1). 순서: 범용·빈 이름은 행별 '미상:' 키 (I34) → 별칭·통합(amap) → 제조사 접두 흡수 (I1, Q3(a)).

        별칭·통합은 제조사를 뗀 키로 먼저 찾고, 없으면 제조사를 떼지 않은 이름 키로도 찾는다 (docs/09 #2 (3) — 손으로 적은 이름 별칭
        'Fluent: [ANSYS Fluent Meshing]' 의 변형 키는 제조사를 떼지 않고 만들어진다; 연계 Tool명 해석과 같은 조건). 두 키 모두 '본 키' 로
        남겨 '별칭 미적용' 검사(_unused_alias_entries)가 쓴다.
        접두 흡수는 2단계 — 먼저 모든 툴사용의 키를 정하고, 그 키 집합 위에서 흡수 쌍(k, rest)을 구한 뒤 모든 툴사용에 적용한다
        (행 순서에 따라 결과가 달라지지 않게). 생존 키는 _absorptions() 가 고른다. 흡수된 키는 alias_map 에도 넣어
        레지스트리의 옛 행이 통합됨으로 바뀌게 한다."""
        warnings = warnings if warnings is not None else []
        raw_keys: dict[int, str] = {}

        def named(key: str, u) -> None:                           # _qk — 키를 인용할 때 그 키를 낸 보고 이름까지 본다
            self._key_names.setdefault(key, set()).add(nfc_strip(u.v.get("reported_tool_name")))

        for u in usages:
            name = u.v.get("reported_tool_name")
            k = self.norm.tool_key(name, u.v.get("reported_vendor"))
            if not self.norm.is_generic_key(k):
                kn = self.norm.tool_key(name)                             # 제조사를 떼지 않은 이름 키 (#2 (3))
                self._seen_keys.update({k, kn})
                raw_keys[id(u)] = amap.get(k) or amap.get(kn) or k
                for key in (k, kn, raw_keys[id(u)]):
                    named(key, u)
                continue
            k = f"{GENERIC_KEY_PREFIX}{u.field}/{u.reg_key}"              # 범용·빈 이름 — 파일 간 충돌 행은 구분 꼬리까지 (I34·I36)
            warnings.append(f"툴 이름 범용/비어 있음: {u.file} {self._q(u.sw_id)} — 통합하지 않고 행별 툴로 둠 (툴 이름 요청)")
            rep = (reports or {}).get(u.file)
            if rep is not None:
                rep.warnings += 1
                self._issue(rep, USAGE_SHEET, u.row, u.sw_id, "Tool명(정식)", u.v.get("reported_tool_name"), "툴 이름 범용/비어 있음",
                            "툴 이름을 지어 주세요 — 분야마다 자체개발 툴이 달라 통합할 수 없습니다 "
                            "(예: '<업무>용 <무엇> 계산기' 처럼 다른 파트가 알아볼 이름)")
            raw_keys[id(u)] = amap.get(k, k)
            named(k, u)
            named(raw_keys[id(u)], u)
        absorb, reasons, self.prefix_held = self._absorptions(set(raw_keys.values()), usages, amap, warnings)
        for key, v in list(amap.items()):                        # 흡수 뒤 별칭 사슬을 다시 닫는다 — '엑셀'→excel→microsoftexcel 이 한 번에
            if v in absorb:                                      # (연계 SW명 해석·레지스트리 통합됨 표시는 amap.get 한 번만 본다)
                amap[key] = absorb[v]
        tools: dict[str, ToolGroup] = {}
        for u in usages:                                         # 흡수된 이름도 생존 키의 이름으로 (그룹 보고 이름 = tools[k].names 와 같게)
            if raw_keys[id(u)] in absorb:
                named(absorb[raw_keys[id(u)]], u)
        for u in usages:
            k = raw_keys[id(u)]
            if k in absorb:
                survivor = absorb[k]
                warnings.append(f"제조사 접두 흡수: {u.file} {self._q(u.sw_id)} '{self._qk(k)}' → '{self._qk(survivor)}' ({reasons[k]})")
                amap.setdefault(k, survivor)                     # 레지스트리의 옛 행(k)이 통합됨으로 바뀌게 (rdf_writer)
                if k in labels and survivor not in labels:
                    labels[survivor] = labels[k]
                k = survivor
            u.tool_key = k
            tools.setdefault(k, ToolGroup(k, [], labels.get(k))).usages.append(u)
        return dict(sorted(tools.items()))

    def _absorptions(self, keys: set[str], usages, amap, warnings: list | None = None
                     ) -> tuple[dict[str, str], dict[str, str], list[tuple[str, str]]]:
        """키 집합 위의 제조사 접두 흡수 쌍 → ({패자 키: 생존 키}, {패자 키: 이유}, 보류한 그룹의 키 쌍 목록) (I1, Leo Q3(a)).

        키 k 가 조사에 나온 제조사명(범용 제조사 제외, 긴 것부터)으로 시작하고 나머지 rest 가 다른 키와 같으면 둘은 같은 툴.
        쌍을 합집합(union)으로 묶어 **그룹 단위**로 생존 키를 고른다 — 셋 이상이 얽혀도({altairfluent, ansysfluent, fluent}) 쌍을
        버리지 않는다. 생존 키: 그룹 안에 레지스트리 활성 행(known_tool_keys)이 있는 키가 **정확히 하나**면 그 키 (TOOL ID 유지 —
        'Fluent' 행이 새로 들어와도 기존 'ansysfluent' ID 가 흔들리지 않는다), 없으면 접두를 뗀 쪽, 곧 사슬의 끝(접두를 뗀 쪽의
        대표 키 — amap 을 거친 뒤의 키; 골든 oracle 거울). 흡수하지 않고 통째로 건너뛰는 그룹 (HITL — 두 툴을 합치는 판정은 사람 몫):
        · 그룹 안 어느 두 키가 별개 판정(distinct) 쌍이면 (직접 쌍은 애초에 묶지 않지만 제3의 키를 거쳐 한 그룹이 될 수 있다) —
          경고 '제조사 접두 흡수와 별개 판정이 충돌', 후보표에는 올리지 않는다 (이미 판정한 쌍)
        · 활성 레지스트리 키가 둘 이상이면 — 기존 툴 둘을 합치는 셈이라 경고 '제조사 접두 흡수 보류' 로 멈추고, 그룹의 모든 키 쌍을
          통합 후보(사유 '제조사 접두', tool_review.csv)로 올린다 (돌려주는 세 번째 값)"""
        vendors = self.norm.survey_vendors(u.v.get("reported_vendor") for u in usages)
        distinct = {tuple(sorted(p)) for p in (self.aliases_cfg.get("distinct") or [])}
        known = self.known_tool_keys
        warnings = warnings if warnings is not None else []
        parent: dict[str, str] = {}                           # union-find — 부모는 접두를 뗀 쪽

        def find(x: str) -> str:
            while parent.get(x, x) != x:
                x = parent[x]
            return x

        for k in sorted(keys):
            if k.startswith(GENERIC_KEY_PREFIX):
                continue
            for vk in vendors:
                rest = k[len(vk):]
                if not (k.startswith(vk) and rest):
                    continue
                rest = amap.get(rest, rest)
                if rest not in keys or rest == k or tuple(sorted((k, rest))) in distinct:
                    continue
                rk, rr = find(k), find(rest)
                if rk != rr:                                  # 같은 그룹이면(순환 방어) 그대로
                    parent[rk] = rr
                break
        groups: dict[str, set[str]] = defaultdict(set)
        for k in parent:
            groups[find(k)].add(k)
        absorb: dict[str, str] = {}
        reasons: dict[str, str] = {}
        held: list[tuple[str, str]] = []
        for end, members in sorted(groups.items()):
            members.add(end)
            pairs = list(combinations(sorted(members), 2))
            clashes = [p for p in pairs if p in distinct]
            if clashes:
                for a, b in clashes:
                    warnings.append(f"제조사 접두 흡수와 별개 판정이 충돌: {self._qk(a)} / {self._qk(b)} — 흡수하지 않음")
                continue
            active = sorted(k for k in members if k in known)
            if len(active) >= 2:
                warnings.append(f"제조사 접두 흡수 보류: 기존 툴 둘 이상 ({', '.join(self._qk(k) for k in active)}) — 검토표에서 판정")
                held.extend(pairs)
                continue
            survivor, why = (active[0], "레지스트리 ID 유지") if active else (end, "제조사 접두를 뗀 키")
            for k in sorted(members - {survivor}):
                absorb[k], reasons[k] = survivor, why
        return absorb, reasons, held

    def _looks_person(self, s: str) -> bool:
        return self.norm.looks_person(s)

    def _q(self, s) -> str:
        """경고·로그에 인용할 값 — 인명 유사(rules.yaml person_pattern·person_patterns_all)면 PERSON_MASK, 아니면 그대로 (docs/09 #20·C5)."""
        s = "" if s is None else str(s)
        return PERSON_MASK if self._looks_person(s) else s

    def _qk(self, k) -> str:
        """툴 키를 인용할 때 — 키 자체가 인명 유사이거나 그 키를 낸 보고 이름(흡수 전 이름 포함, _key_names) 가운데 하나라도 인명 유사면 PERSON_MASK
        (2026-10-12 재검토 수리: tool_key 는 공백을 지워 '가나다 책임 해석툴' → '가나다책임해석툴' 이 되면 직급 뒤에 한글이 이어져 인명 패턴(P2·P6)에
        걸리지 않았다 — 원문은 걸린다). 설정에만 있는 키(별칭 순환·별칭과 별개 판정 충돌)는 보고 이름이 없어 키만 본다 (_q 와 같다)."""
        k = "" if k is None else str(k)
        if self._looks_person(k) or any(self._looks_person(n) for n in self._key_names.get(k, ())):
            return PERSON_MASK
        return k

    def _names(self, group: ToolGroup) -> list[str]:
        """검토표·load_log 통합 후보의 보고 이름(표기 칸) — 인명 유사 이름은 PERSON_MASK (C5 '검토표 표기 칸도 가림'; apply-review 는 표기 칸을 읽지 않는다).
        키 칸(툴A_키·툴B_키)만 apply-review 가 읽어서 그대로 둔다 — 키에는 이름이 남는다 (tool_key 는 괄호·버전·공백만 지워
        '가나다 책임 v2' → '가나다책임', '가나다 책임 해석툴' → '가나다책임해석툴' — 뒤 꼴은 직급 뒤에 한글이 이어져 키만으로는 인명 패턴에 안 걸린다).
        그런 툴 이름은 '인명 유사 패턴' 경고·수정 요청으로 고치고, 키 칸·load_log tool_keys·레지스트리의 원문은 C8·N1(Leo 결정 대기) 범위.
        경고·표기 칸의 '비슷한 키' 힌트에 키를 인용할 때는 _qk (키와 그 키를 낸 보고 이름을 함께 판정)."""
        return [self._q(n) for n in group.names]

    def _resolve_partners(self, ios, usages, tools, amap, warnings: list) -> None:
        """연계 SW명 → 툴 (I1): 키가 같거나, 조사에 나온 제조사명(범용 제조사 제외)을 앞에서 뗀 키가 같으면 그 툴.
        사람 이름처럼 보이는 표기는 조사 누락 후보에 올리지 않는다 (#20-2)."""
        vendors = self.norm.survey_vendors(u.v.get("reported_vendor") for u in usages)

        def resolve(name: str) -> str | None:
            k0 = self.norm.tool_key(name)
            self._seen_keys.add(k0)                              # 별칭 미적용 검사용 '본 키' — 조각 키와 제조사를 뗀 나머지 (#2 (4))
            k = amap.get(k0, k0)
            if k in tools:
                return k
            for vk in vendors:
                rest = k[len(vk):]
                if k.startswith(vk) and rest:
                    self._seen_keys.add(rest)
                    rest = amap.get(rest, rest)
                    if rest in tools:
                        return rest
            return None

        for x in ios:
            for p in x.partner_names:
                t = resolve(p)
                if t:
                    x.partner_tools.add(t)
                elif self._looks_person(p):
                    warnings.append(f"연계 Tool명이 인명처럼 보임: {x.file} {self._q(x.sw_id)} '{self._q(x.name)}' — 조사 누락 후보에서 뺌")
                else:
                    x.partner_unresolved.append(self.norm.tool_key(p))

    def _candidates(self, tools) -> list[dict]:
        """통합 후보 (I23) — 자동 통합하지 않는다. 별개 판정 쌍(distinct)은 제외. 제조사 접두 흡수를 보류한 그룹(기존 툴 둘 이상)의
        키 쌍은 사유 '제조사 접두' 로 올린다 (포함·유사도에 걸리지 않아도) — 사람이 검토표에서 판정한다."""
        distinct = {tuple(sorted(p)) for p in (self.aliases_cfg.get("distinct") or [])}
        held = set(getattr(self, "prefix_held", []))
        th = float(self.rules["fuzzy_threshold"])
        keys = sorted(k for k in tools if not k.startswith(GENERIC_KEY_PREFIX))     # 행별 '미상:' 키는 후보에 올리지 않는다 (I34)
        out = []
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                if (a, b) in distinct:
                    continue
                r = max(difflib.SequenceMatcher(None, a, b).ratio(), difflib.SequenceMatcher(None, b, a).ratio())
                contains = (a in b or b in a) and min(len(a), len(b)) >= self.min_contain    # 포함은 짧은 키가 3자 이상일 때만 (#16)
                prefix = (a, b) in held
                if contains or r >= th or prefix:
                    out.append({"a": a, "b": b, "similarity": round(r, 3),
                                "reason": "제조사 접두" if prefix else "포함" if contains else "유사도",
                                "names_a": self._names(tools[a]), "names_b": self._names(tools[b])})
        return out

    def _partner_review(self, summary: dict[str, dict], tools: dict, amap: dict) -> list[dict]:
        """검토표 '연계SW 미해석' 행 (docs/09 #17, I10·I35) — 해석 못 한 연계 Tool명 키(summary = unresolved_partner_summary)마다 한 행.

        툴A = 기존 툴 키 제안: 포함 관계(짧은 키 candidate_min_contain_len 이상)이거나 유사도(양방향 difflib 최댓값) ≥ fuzzy_threshold 인
        툴 키 가운데 유사도가 가장 높은 것 ('미상:' 키·별개 판정 쌍 제외). 없으면 빈칸 + 비슷한 키 3개(유사도 0.5 이상)를 힌트로 —
        '가상외부해석툴 → 가상열해석 0.67' 같은 엉뚱한 제안을 툴A 칸에 넣지 않는다. 툴B = 연계 키 (merge_pairs 'A 생존' 과 맞게 순서를 둔다 —
        통합하면 기존 툴의 TOOL ID 가 유지된다). 원문(partner_raw)은 쓰지 않고 키·언급 수·파트만 (인명 유사 조각은 summary 에 이미 없다).
        다시 올리지 않는 키: tool_aliases.yaml partner_missing (기존 툴 아님 판정 — CQ09 후보에는 남는다), 이미 별칭·통합이 있는 키
        (판정한 대상 툴이 이번 적재에 없을 때)."""
        missing = {nfc_strip(k) for k in self.aliases_cfg.get("partner_missing") or []}
        distinct = {tuple(sorted(p)) for p in (self.aliases_cfg.get("distinct") or [])}
        th = float(self.rules["fuzzy_threshold"])
        keys = sorted(k for k in tools if not k.startswith(GENERIC_KEY_PREFIX))
        out = []
        for k, e in summary.items():
            if k in missing or k in amap:
                continue
            scored = []
            for t in keys:
                if tuple(sorted((k, t))) in distinct:
                    continue
                r = max(difflib.SequenceMatcher(None, k, t).ratio(), difflib.SequenceMatcher(None, t, k).ratio())
                contains = (k in t or t in k) and min(len(k), len(t)) >= self.min_contain
                scored.append((-round(r, 3), t, contains))
            scored.sort()
            strong = [s for s in scored if s[2] or -s[0] >= th]
            a = strong[0][1] if strong else ""
            # 힌트 키는 툴A_표기 칸에 실린다 (apply-review 는 읽지 않는다) — 키나 그 툴의 보고 이름이 인명 유사면 가림 (_qk, 2026-10-12 재검토 수리)
            out.append({"a": a, "b": k, "similarity": -strong[0][0] if strong else None,
                        "reason": "연계SW 미해석", "names_a": self._names(tools[a]) if a else [],
                        "mentions": e["mentions"], "fields": e["fields"],
                        "hints": [] if a else [(self._qk(t), -r) for r, t, _c in scored if -r >= 0.5][:3]})
        return out

    def _unused_alias_entries(self, tools: dict, amap: dict, warnings: list) -> None:
        """'별칭 미적용' 경고 (docs/09 #2 (4)) — 툴 통합 판정 항목 가운데 키가 이번 적재의 툴·연계 Tool명 어디에도 없는 것.

        '본 키' = 툴사용 이름 키(제조사 뗀 것·안 뗀 것) ∪ 연계 Tool명 조각 키(제조사를 뗀 나머지 포함) ∪ 툴 그룹 키. 설정 파일(저장소 config/ 와 오버레이)마다
        원문을 따로 읽어 어느 파일의 항목인지 적는다. 검사: merge_pairs(없으면 merge_keys 를 쌍으로) — 두 키 모두 안 보이고 그 대표도 안 보일 때
        (대표만 보이면 사슬은 적용된 것), distinct — 두 키 모두, labels·partner_missing — 그 키, aliases — **오버레이 파일만** 변형 표기마다.
        저장소 config/ 의 공개 별칭 사전(aliases)은 쓰지 않는 표기가 있는 게 정상이라 검사하지 않는다. 값은 _q 로 인용 (인명 유사면 가림)."""
        observed = self._seen_keys | set(tools)

        def seen(k) -> bool:
            k = nfc_strip(k)
            return k in observed or amap.get(k, k) in observed

        for d, public in ((self.config_dir, True), (self.overlay_dir, False)):
            path = Path(d) / "tool_aliases.yaml" if d else None
            if path is None or not path.is_file():
                continue
            raw = read_yaml(path)
            items: list[tuple[str, str]] = []
            if "merge_pairs" in raw:
                sect, pairs = "merge_pairs", read_merge_pairs(raw, promote=False)
            else:
                sect, pairs = "merge_keys", [[nfc_strip(a), nfc_strip(b)] for b, a in (raw.get("merge_keys") or {}).items()]
            items += [(sect, f"{self._q(a)} / {self._q(b)}") for a, b in pairs if a and b and not (seen(a) or seen(b))]
            items += [("distinct", f"{self._q(nfc_strip(a))} / {self._q(nfc_strip(b))}") for a, b in raw.get("distinct") or []
                      if not (seen(a) or seen(b))]
            items += [("labels", self._q(nfc_strip(k))) for k in raw.get("labels") or {} if nfc_strip(k) and not seen(k)]
            items += [("partner_missing", self._q(nfc_strip(k))) for k in raw.get("partner_missing") or []
                      if nfc_strip(k) and nfc_strip(k) not in observed]
            if not public:
                for rep, variants in (raw.get("aliases") or {}).items():
                    rk = self.norm.tool_key(rep)
                    for v in variants or []:
                        vk = self.norm.tool_key(v)
                        if vk and vk != rk and vk not in observed:
                            items.append(("aliases", f"{self._q(nfc_strip(rep))} ← {self._q(nfc_strip(v))}"))
            where = config_where(path)
            for s, item in items:
                warnings.append(f"별칭 미적용: {where} {s} {item} — 이번 적재의 툴·연계 Tool명 어디에도 없음 "
                                "(툴 이름 키 규칙이 바뀌었거나 그 툴이 이번 회신에 없다; 지우기 전에 확인)")

    def _conflicts(self, tools) -> dict:
        """같은 툴의 제조사·구분 값이 갈리면 {툴 키: {vendor|kind: {majority, values: {값: 건수}}}} (load_log tool_attribute_conflicts).
        다수결은 원문으로 정한 뒤 값만 _q 로 가린다 — 인명 유사 값은 PERSON_MASK 한 칸에 건수를 더한다 (2026-10-12 재검토 수리:
        '제조사 / 개발주체' 칸의 'Microsoft(… 책임 구매)' 가 load_log 에 원문으로 남았다; 그래프에는 보존 — D6)."""
        out = {}
        for k, g in tools.items():
            for attr, slot in (("vendor", "reported_vendor"), ("kind", "reported_kind")):
                c = Counter(nfc_strip(u.v.get(slot)) for u in g.usages)
                if len(c) > 1:
                    shown: Counter = Counter()
                    for val, cnt in c.items():
                        shown[self._q(val)] += cnt
                    maj = g.majority(slot)
                    out.setdefault(k, {})[attr] = {"majority": None if maj is None else self._q(maj), "values": dict(sorted(shown.items()))}
        return out

    # ---- 입출력 키 (D2) ---------------------------------------------------------------
    def _disambiguate(self, ios, reports: dict, warnings: list) -> None:
        groups = defaultdict(list)
        for x in ios:
            groups[(x.file, x.base_key)].append(x)
        getters = [lambda x: x.category, lambda x: nfc_strip(x.v.get("extensions_raw")),
                   lambda x: nfc_strip(x.v.get("transfer_method")), lambda x: nfc_strip(x.v.get("partner_raw"))]
        for group in groups.values():
            if len(group) < 2:
                continue
            varying = [g for g in getters if len({g(x) for x in group}) > 1]
            seen = Counter()
            for x in group:
                sig = tuple(g(x) for g in varying)
                if varying:
                    x.suffix = "[" + "|".join(sig) + "]"
                if seen[sig]:
                    x.seq = seen[sig]
                    x.suffix += f"#{x.seq}"
                    warnings.append(f"완전 중복 입출력 행: {self._q(x.key)} — 경고 후 순번")    # 키에 데이터명·연계 SW명 원문이 든다
                    reports[x.file].warnings += 1
                seen[sig] += 1


# --------------------------------------------------------------------------- 템플릿 예시
def extract_template_examples(form_xlsx: Path, config_dir: Path | None = None, overlay_dir: Path | None = None) -> dict:
    """양식의 예시 행(데이터 시작 행부터 내용이 있는 행)을 슬롯 이름으로 뽑는다 → config/template_examples.yaml.
    overlay_dir(사내 오버레이)를 주면 그 rules.yaml·header_map.yaml 도 쓴다 — 사내 양식판의 시트 이름·헤더 문구 (I30)."""
    rules = load_config("rules.yaml", config_dir, overlay_dir)[0]["loader"]
    spec = load_form_spec(config_dir=config_dir, overlay_dir=overlay_dir)
    cands = {USAGE_SHEET: rules["sheets"]["usage"], IO_SHEET: rules["sheets"]["io"]}
    wb = openpyxl.load_workbook(form_xlsx, read_only=True, data_only=True)
    out = {}
    try:
        for sheet in (USAGE_SHEET, IO_SHEET):
            ws = wb[resolve_sheet(wb.sheetnames, cands[sheet])]
            header = next(ws.iter_rows(min_row=rules["header_row"], max_row=rules["header_row"], values_only=True))
            by_h = spec.by_header(sheet)
            idx = {i: by_h[norm_header(h)].slot for i, h in enumerate(header) if not _blank(h) and norm_header(h) in by_h}
            rows = []
            for cells in ws.iter_rows(min_row=rules["data_start_row"], values_only=True):
                v = {s: cells[i] for i, s in idx.items() if i < len(cells) and not _blank(cells[i])}
                if len(v) > 2:          # 양식 v1.1: 빈 응답 행에도 수식·일련번호가 있다 — 내용 열이 몇 개 이상인 행만 예시
                    rows.append({s: (x if isinstance(x, (int, float)) else cell_key(x)) for s, x in v.items()})
            out[sheet] = rows
    finally:
        wb.close()
    return out


def write_template_examples(forms: list[Path], config_dir: Path | None = None, overlay_dir: Path | None = None) -> tuple[Path, int]:
    """여러 양식판의 예시 행을 합쳐 쓴다 (v1.0 + v1.1, M3.1) → (쓴 파일, 새로 더한 행 수).

    overlay_dir 를 주면 (cli --overlay — 사내 data/real/config, docs/09 #3) 저장소 config/template_examples.yaml 은 손대지 않고 그 폴더의
    template_examples.yaml 에 **더한다** — 이미 그 파일이나 저장소 파일에 있는 행은 빼고. 적재기가 시트별 합집합으로 읽는다 (config.merge_config).
    저장소 파일을 고치면 업데이트가 '.new' 로 남기고 selftest(양식 일치 검사)가 실패하므로 사내 양식판은 이쪽으로 넣는다."""
    data: dict[str, list] = {USAGE_SHEET: [], IO_SHEET: []}
    for form in forms:
        for sheet, rows in extract_template_examples(form, config_dir, overlay_dir).items():
            data[sheet] += [r for r in rows if r not in data[sheet]]
    if overlay_dir is not None:
        path = Path(overlay_dir) / "template_examples.yaml"
        base = load_yaml("template_examples.yaml", config_dir)
        old = read_yaml(path) if path.is_file() else {}
        merged = {sheet: list(old.get(sheet) or []) for sheet in (USAGE_SHEET, IO_SHEET)}
        added = 0
        for sheet, rows in data.items():
            for r in rows:
                if r not in merged[sheet] and r not in (base.get(sheet) or []):
                    merged[sheet].append(r)
                    added += 1
        head = ("# 사내 양식판의 템플릿 예시 행 (사내 전용 — 실제 값이 섞일 수 있어 밖으로 가져가지 않는다). 양식 파일 이름은 적지 않는다 (인명이 섞일 수 있다).\n"
                "# 더하기: python -m engenius_onto template-examples --form <양식 xlsx> --overlay (이미 있는 행은 그대로)\n"
                "# 적재기는 저장소 config/template_examples.yaml 과 시트별로 합쳐 읽는다 (I15, docs/09 #3).\n")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(head + yaml.safe_dump(merged, allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8", newline="\n")
        return path, added
    path = (config_dir or CONFIG_DIR) / "template_examples.yaml"
    head = (f"# 템플릿 예시 행 (docs/02 2장, 골든 I15) — {', '.join(f.name for f in forms)} 에서 추출.\n"
            "# 다시 만들기: python -m engenius_onto template-examples --form <양식 xlsx> [--form <양식 xlsx> ...]\n"
            "# 적재 열(스키마 양식 열) 전체가 여기 한 행과 같으면 위치와 무관하게 적재에서 제외한다.\n"
            "# 수식 열(SW명·Tool명 자동)과 '실무 문의처' 열은 적재 열이 아니라 여기에도 없다 (인명 미저장).\n")
    body = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000)
    path.write_text(head + body, encoding="utf-8", newline="\n")
    return path, sum(len(rows) for rows in data.values())
