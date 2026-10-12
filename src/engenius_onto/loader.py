"""조사 엑셀 적재 (docs/02 5·6장, M3 · M3.1).

파트별 xlsx 를 읽어 툴사용(SW기본정보 행)·입출력(SW입출력 행)으로 만들고, 툴 통합·확장자·연계 SW명을 정규화한다.
RDF 로 쓰는 것은 rdf_writer, ID 고정은 registry 가 맡는다. 세부 해석의 정본은 골든 interpretations (I번호).

- 헤더 이름으로 매핑 (NFKC 후 공백·'*' 무시, I30) — 매핑 안 된 헤더는 경고, 의도적 제외 열(B 수식·K 문의처)은 읽지 않는다.
- 시트·선택지 목록 이름은 양식판마다 다르다 — config/rules.yaml loader.sheets·choice_list_aliases 가 흡수 (docs/09 #13, 양식 v1.1).
- 파트(Field) = 파일명의 약칭 (docs/10 5장). 묶음 파일(MD = MDT+MDC)은 행의 Tool ID 앞부분으로 나눈다 (config/parts.yaml).
  행의 '담당 부서' 는 분류 속성 reported_domain — 파트 설정과 다르면 경고만.
- 예시 행은 위치가 아니라 적재 열 전체가 템플릿 예시와 같은지로 판별 (I15) — config/template_examples.yaml.
- 같은 파트 파일이 여럿이면 (날짜, 사본 번호 '(n)', 파일명) 최신 1개만 적재하고, 그 뒤 같은 내용(sha256) 파일은 한 번만 (I31·I33).
- 파일 간 같은 (파트, Tool ID) 는 둘 다 적재하고 경고 — 전용 파일이 아닌 쪽 레지스트리 키에 구분 꼬리 '@<약칭|file-sha10>' (I36, docs/09 #1).
- 어떤 행도 조용히 버리지 않는다 — 제외는 사유와 함께 excluded_rows, 문제는 warnings (5장 6). 행 단위 문제는 issues 에도
  구조화해 남겨 파트별 수정 요청표(fix_requests)를 만든다 (M3.1).
- 인명 열(실무 문의처)은 읽지 않는다 (CLAUDE.md 절대 규칙 5). 인명 유사 패턴은 경고만 하고 경고에 값을 옮기지 않는다 (D6, #20).
  값을 인용하는 경고는 Loader._q 를 거친다 — 인명 유사면 PERSON_MASK (docs/09 C5, 확장자 경고부터 2026-10-12).
  규칙 밖 파일명은 해시 이름으로만 기록한다 (#8 — 파일명에 인명이 섞여 있을 수 있다).
"""

from __future__ import annotations

import datetime as dt
import difflib
import hashlib
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

import openpyxl
import yaml

from engenius_onto.config import CONFIG_DIR, ConfigError, load_config, load_yaml, read_yaml
from engenius_onto.form_spec import Column, FormSpec, load_form_spec, norm_header
from engenius_onto.normalize import GENERIC_KEY_PREFIX, Normalizer, merge_keys_from_pairs, nfc_strip, read_merge_pairs

USAGE_SHEET, IO_SHEET = "SW기본정보", "SW입출력"      # 스키마의 시트 이름 (실제 파일의 시트 이름은 설정으로 찾는다)
EXCEL_SUFFIXES = {".xlsx", ".xlsm", ".xls"}
PERSON_MASK = "[인명 유사 — 값 생략]"                  # 경고·로그에 인용할 값이 인명 유사일 때 대신 쓰는 문구 (Loader._q, docs/09 #20·C5)
ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿"), None)


def id_key(s) -> str:
    """Tool ID 연결용 키 (docs/09 #18): NFKC·앞뒤 공백·보이지 않는 문자 제거·대문자, '-' 뒤 숫자 앞 0 무시 (MDC-01 = MDC-1)."""
    k = unicodedata.normalize("NFKC", "" if s is None else str(s)).translate(ZERO_WIDTH).strip().upper()
    return re.sub(r"(?<=-)0+(?=\d)", "", re.sub(r"\s+", "", k))


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

    @property
    def loaded_files(self) -> list[FileReport]:
        return [f for f in self.files if f.superseded_by is None and f.unreadable is None and f.duplicate_of is None]

    @property
    def complete(self) -> bool:
        """모든 파일을 읽었는가 — 아니면 이번 적재에 없다고 폐기 처리하지 않는다 (#7)."""
        return all(f.unreadable is None for f in self.files)

    def per_file(self) -> dict:
        return {f.name: f.stats() for f in self.files}


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
        self.spec: FormSpec = load_form_spec(schema_file, self.config_dir)
        self.examples = load_yaml("template_examples.yaml", self.config_dir)
        self.aliases_cfg = self._cfg("tool_aliases.yaml")
        self.person_re = re.compile(self.rules["person_pattern"])
        self.person_all = [re.compile(p) for p in self.rules.get("person_patterns_all") or []]
        self.free_text = set(self.rules["free_text_slots"])
        self.month_slots = set(self.lcfg.get("month_slots", ["license_expiry"]))
        d = self.rules["direction"]
        self.dir_short = {**{x: "in" for x in d["consume"]}, **{x: "out" for x in d["produce"]}}
        sheets = self.lcfg["sheets"]
        self.sheet_cands = {USAGE_SHEET: sheets["usage"], IO_SHEET: sheets["io"]}
        self.choice_aliases = {name: [name, *alts] for name, alts in (self.lcfg.get("choice_list_aliases") or {}).items()}
        self.absent_ok = set(self.lcfg.get("absent_ok_slots") or [])
        parts_cfg = self._cfg("parts.yaml", optional=True)
        self.parts = parts_cfg.get("parts") or {}
        self.bundles = {k: list(v) for k, v in (parts_cfg.get("file_bundles") or {}).items()}
        self.synthetic_parts = set(parts_cfg.get("synthetic_parts") or [])
        self.value_aliases = self._value_aliases(self._cfg("value_aliases.yaml", optional=True))
        self.min_contain = int(self.rules.get("candidate_min_contain_len", 3))
        self.known_tool_keys: set[str] = set()                  # 레지스트리 활성 툴 키 (load() 가 받는다)
        self.prefix_held: list[tuple[str, str]] = []            # 접두 흡수를 보류한 그룹의 키 쌍 (_absorptions → _candidates '제조사 접두')

    def _cfg(self, name: str, optional: bool = False) -> dict:
        """config/<name> (+ 오버레이). 덮은 파일 이름은 overlay_files 에 남긴다."""
        data, used = load_config(name, self.config_dir, self.overlay_dir, optional=optional)
        if used:
            self._note_overlay(name)
        return data

    def _note_overlay(self, name: str) -> None:
        if self.overlay_dir and (self.overlay_dir / name).is_file() and name not in self.overlay_files:
            self.overlay_files.append(name)

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

    @property
    def known_codes(self) -> set[str]:
        return set(self.parts) | set(self.bundles) | self.synthetic_parts

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
        유일화한 이름도 파일명 규칙에 맞지 않는다). 규칙 안 이름이 겹치는 것(NFC 로 같아지는 두 이름)도 해시 이름으로 돌린다."""
        used = used if used is not None else set()
        code, date, copy = self.parse_name(name)
        label = unicodedata.normalize("NFC", name)
        if code is not None and code in self.known_codes and Path(name).suffix == ".xlsx" and label not in used:
            return label, code, date, copy
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
        reports: list[FileReport] = []
        used: set[str] = set()
        for idx, p in enumerate(paths, start=1):
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
            label, code, date, copy = self.file_label(p.name, sha, used)
            used.add(label)
            reports.append(FileReport(label, sha, code, date, path=p, copy=copy, index=idx))
        # 재발송 (I33): 같은 파트는 (날짜, 사본 번호, 파일명) 최신만 — 같은 날짜면 브라우저 사본 '(n)' 의 번호가 큰 쪽(나중에 받은 파일)
        latest: dict[str, FileReport] = {}
        for r in reports:
            if r.field is None:
                continue
            if r.field not in latest or (r.date, r.copy, r.name) > (latest[r.field].date, latest[r.field].copy, latest[r.field].name):
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
        conflicts = self._conflicts(tools)
        labels = {u.field: self.part_label(u.field) for u in usages if u.field}
        return LoadResult(reports, usages, ios, tools, warnings, excluded, candidates, conflicts, alias_map,
                          self.issues, labels)

    def _same_content(self, reports: list[FileReport], warnings: list) -> None:
        """I33 뒤에: 대체되지 않은 파일 가운데 내용(sha256)이 같은 파일은 한 번만 적재한다 — 규칙 안 파일 우선, 다음 입력 순서.
        나머지는 duplicate_of + 경고 '같은 내용 파일' (제외 건수에 넣지 않는다 — I33 과 같은 원칙). 같은 날짜 '(n)' 사본처럼 규칙 안
        같은 약칭이면 이미 I33 이 '(내용 같음)' 으로 처리했다. 두 규칙 안 파일의 약칭이 다르면 어느 파트 파일인지 확인을 덧붙인다."""
        groups: dict[str, list[FileReport]] = defaultdict(list)
        for r in reports:
            if r.superseded_by is None:
                groups[r.sha256].append(r)
        for group in groups.values():
            if len(group) < 2:
                continue
            keep = min(group, key=lambda r: (r.field is None, r.index))
            for r in group:
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
        """수정 요청표 한 줄 (값은 사내 파일에만 — diag 는 값을 쓰지 않는다)."""
        self.issues.append({"file": rep.name, "part": rep.field, "sheet": sheet, "row": row,
                            "tool_id": nfc_strip(tool_id) if tool_id is not None else "",
                            "column": (header or "").rstrip(" *"), "value": "" if value is None else cell_key(value),
                            "kind": kind, "hint": hint})

    # ---- 시트 읽기 ----------------------------------------------------------------
    def _read_sheet(self, wb, sheet: str, rep: FileReport, warnings: list, excluded: list):
        """([(행 번호, {슬롯: 셀 값})], 이 파일에 있는 슬롯). 빈 행은 건너뛰고, 연속 빈 행이 blank_rows_end 개면 끝으로 본다."""
        fname = rep.name
        actual = resolve_sheet(wb.sheetnames, self.sheet_cands[sheet])
        if actual is None:
            warnings.append(f"시트 없음: {fname} '{sheet}' — 이 시트는 적재하지 않음 (찾은 이름 후보: config/rules.yaml loader.sheets)")
            rep.warnings += 1
            return [], set()
        ws = wb[actual]
        hr, start = self.lcfg["header_row"], self.lcfg["data_start_row"]
        header = [c.value for c in ws[hr]] if ws.max_row >= hr else []
        mapping, by_h = {}, self.spec.by_header(sheet)
        for idx, h in enumerate(header):
            if _blank(h):
                continue
            nh = norm_header(h)
            if nh in by_h:
                col = by_h[nh]
                if col in mapping.values():                                   # #19 중복 헤더 — 앞 열 사용
                    warnings.append(f"중복 헤더: {fname} {sheet} '{nfc_strip(h)}' — 앞 열만 읽음")
                    rep.warnings += 1
                    continue
                mapping[idx] = col
            elif nh not in self.spec.ignored[sheet]:
                warnings.append(f"매핑 안 된 헤더: {fname} {sheet} '{nfc_strip(h)}'")
                rep.warnings += 1
        present = {c.slot for c in mapping.values()}
        missing = [c.header for c in self.spec.columns[sheet] if c.slot not in present and c.slot not in self.absent_ok]
        if missing:
            warnings.append(f"양식 열 없음: {fname} {sheet} {missing}")
            rep.warnings += 1
        fill = self._merged_fill(ws, start, mapping, fname, sheet, rep, warnings)
        rows, blanks, ended, tail = [], 0, False, []
        for n in range(start, ws.max_row + 1):
            v = {c.slot: fill.get((n, i), ws.cell(n, i + 1).value) for i, c in mapping.items()}
            if all(_blank(x) for x in v.values()):
                blanks += 1
                if blanks >= self.lcfg["blank_rows_end"]:
                    ended = True
                continue
            blanks = 0
            if ended:                                                          # #6 빈 행 뒤 내용은 적재 안 함, 기록
                tail.append(n)
                continue
            rows.append((n, v))
        if tail:
            warnings.append(f"빈 행 {self.lcfg['blank_rows_end']}개 뒤 내용 행: {fname} {sheet} {len(tail)}행 — 적재하지 않음 "
                            f"(첫 행 {tail[0]})")
            rep.warnings += 1
            for n in tail:
                excluded.append({"file": fname, "sheet": sheet, "row": n, "reason": "빈 행 뒤 내용 행 (시트 끝으로 봄, #6)"})
                rep.excluded += 1
                self._issue(rep, sheet, n, None, None, None, "빈 행 뒤 내용",
                            f"빈 행 {self.lcfg['blank_rows_end']}개 이상 뒤에 있어 읽지 않았다 — 빈 행을 지우고 위로 붙여 주세요")
        return rows, present

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
            top = ws.cell(rng.min_row, rng.min_col).value
            if _blank(top):
                continue
            for r in range(max(rng.min_row, start), rng.max_row + 1):
                for i in idxs:
                    fill[(r, i)] = top
            warnings.append(f"병합 셀: {fname} {sheet} {rng.coord} — 위 칸 값으로 채움")
            rep.warnings += 1
        return fill

    def _read_choices(self, wb) -> dict[str, list[str]]:
        """{정규화 목록 이름: 값}. 목록 이름 행은 2행 (1행 제목)."""
        name = resolve_sheet(wb.sheetnames, self.lcfg["choices_sheet"])
        if name is None:
            return {}
        ws = wb[name]
        out = {}
        for c in range(1, ws.max_column + 1):
            vals = [nfc_strip(ws.cell(r, c).value) for r in range(2, ws.max_row + 1) if not _blank(ws.cell(r, c).value)]
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

    # ---- 셀 규칙 (D5) -------------------------------------------------------------
    def _convert(self, col: Column, value, where: str, warnings: list, rep: FileReport):
        """문자열 슬롯의 숫자·날짜 셀 변환 (I27). 정수 슬롯은 (정수 | None, 원문 | None)."""
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
        return nfc_strip(value), None

    def _apply_value_aliases(self, v: dict, rep: FileReport) -> int:
        n = 0
        for slot, mapping in self.value_aliases.items():
            val = v.get(slot)
            if isinstance(val, str) and nfc_strip(val) in mapping:
                v[slot] = mapping[nfc_strip(val)]
                n += 1
        return n

    def _check(self, sheet: str, v: dict, present: set, choices: dict, where: str, warnings: list, rep: FileReport,
               row: int, tool_id, missing_lists: set) -> None:
        for col in self.spec.columns[sheet]:
            if col.slot not in present:
                continue
            val = v.get(col.slot)
            if col.required and _blank(val):
                warnings.append(f"필수값 누락: {where} '{col.header}'")
                rep.warnings += 1
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
                    warnings.append(f"선택지 밖 값: {where} '{col.header}' = '{val}'")
                    rep.warnings += 1
                    self._issue(rep, sheet, row, tool_id, col.header, val, "선택지 밖 값",
                                "드롭다운에서 고르세요. 목록에 없으면 '기타'를 고르고 비고에 적어 주세요")
            if isinstance(val, str) and not _blank(val) and (
                    (col.slot in self.free_text and self.person_re.search(val)) or any(p.search(val) for p in self.person_all)):
                warnings.append(f"인명 유사 패턴: {where} '{col.header}'")
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
        try:
            choices = self._read_choices(wb)
            if not choices:
                warnings.append(f"선택지 시트 없음: {fname} — 선택지 검사를 하지 않음")
                rep.warnings += 1
            urows, upresent = self._read_sheet(wb, USAGE_SHEET, rep, warnings, excluded)
            irows, ipresent = self._read_sheet(wb, IO_SHEET, rep, warnings, excluded)
        finally:
            wb.close()
        cols_u = {c.slot: c for c in self.spec.columns[USAGE_SHEET]}
        cols_i = {c.slot: c for c in self.spec.columns[IO_SHEET]}
        missing_lists: set = set()
        aliased = 0
        self._na_cells = 0
        self._na_int_cells = 0

        def exclude(sheet, row, reason):
            excluded.append({"file": fname, "sheet": sheet, "row": row, "reason": reason})
            rep.excluded += 1

        usages, by_id = [], {}
        for n, raw in urows:
            if self._is_example(USAGE_SHEET, raw):
                exclude(USAGE_SHEET, n, "템플릿 예시 행 (내용 일치, I15)")
                continue
            if _blank(raw.get("source_key")):
                name = nfc_strip(raw.get("reported_tool_name"))
                warnings.append(f"SW ID 없는 내용 행: {fname} {USAGE_SHEET} '{name}' — 건너뜀")
                rep.warnings += 1
                exclude(USAGE_SHEET, n, "SW ID 없음 (I22)")
                self._issue(rep, USAGE_SHEET, n, "", "Tool ID", None, "Tool ID 없음", "Tool ID(부서약칭-번호)를 적어 주세요")
                continue
            where = f"{fname} {USAGE_SHEET} {cell_key(raw.get('source_key'))}"
            v, rawvals = {}, {}
            for slot, val in raw.items():
                v[slot], r = self._convert(cols_u[slot], val, where, warnings, rep)
                if r is not None:
                    rawvals[slot] = r
            aliased += self._apply_value_aliases(v, rep)
            self._check(USAGE_SHEET, v, upresent, choices, where, warnings, rep, n, v.get("source_key"), missing_lists)
            u = UsageRec(fname, rep.field, n, v, rawvals, part=self._part_of(rep, v.get("source_key"), warnings, n))
            k = id_key(u.sw_id)
            if k in by_id:
                warnings.append(f"중복 SW ID: {fname} {u.sw_id} — 먼저 나온 행 사용, "
                                f"'{nfc_strip(v.get('reported_tool_name'))}' 행 제외")
                rep.warnings += 1
                exclude(USAGE_SHEET, n, f"중복 SW ID {u.sw_id} (먼저 나온 {by_id[k].row}행 사용)")
                self._issue(rep, USAGE_SHEET, n, u.sw_id, "Tool ID", u.sw_id, "Tool ID 중복",
                            f"{by_id[k].row}행과 같은 Tool ID — 번호를 다르게 해 주세요")
                continue
            dom = nfc_strip(v.get("reported_domain"))
            allowed = self._domains(u.part)
            if u.part and dom and allowed and dom not in allowed:
                warnings.append(f"파일 분야 ≠ 담당 부서: {fname} {u.sw_id} → '{dom}'")
                rep.warnings += 1
            for slot, r in rawvals.items():
                warnings.append(f"{cols_u[slot].header.rstrip(' *')} 정수 변환 실패: {fname} {u.sw_id} '{r}' — 원문 보존")
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
                prev_n = prev_id = None
                continue
            if _blank(raw.get("owner_source_key")) and fill_down and prev_id is not None and prev_n == n - 1:
                # 같은 툴의 입출력을 여러 행에 적으며 첫 행에만 ID 를 적은 경우 (Leo 2026-10-09) — 바로 위 행과 붙어 있을 때만
                raw = {**raw, "owner_source_key": prev_id}
                warnings.append(f"Tool ID 이어받음: {fname} {IO_SHEET} '{nfc_strip(raw.get('data_name'))}' → '{nfc_strip(prev_id)}' (바로 위 행)")
                rep.warnings += 1
            if _blank(raw.get("owner_source_key")):
                prev_n = prev_id = None
                warnings.append(f"SW ID 없는 내용 행: {fname} {IO_SHEET} '{nfc_strip(raw.get('data_name'))}' — 건너뜀")
                rep.warnings += 1
                exclude(IO_SHEET, n, "SW ID 없음 (I22)")
                self._issue(rep, IO_SHEET, n, "", "Tool ID", None, "Tool ID 없음",
                            "이 입출력이 어느 Tool 것인지 Tool ID 를 적어 주세요")
                continue
            prev_n, prev_id = n, raw.get("owner_source_key")
            where = f"{fname} {IO_SHEET} {cell_key(raw.get('owner_source_key'))} '{cell_key(raw.get('data_name'))}'"
            v = {}
            for slot, val in raw.items():
                v[slot], _ = self._convert(cols_i[slot], val, where, warnings, rep)
            aliased += self._apply_value_aliases(v, rep)
            self._check(IO_SHEET, v, ipresent, choices, where, warnings, rep, n, v.get("owner_source_key"), missing_lists)
            sw = nfc_strip(v.get("owner_source_key"))
            owner = by_id.get(id_key(sw))                            # D3: 소유는 같은 파일 안에서 (#18 표기 차이 흡수)
            dval = nfc_strip(v.get("direction"))
            x = IORec(fname, rep.field, n, v, owner, self.dir_short.get(dval, "?"))
            if owner is None:
                warnings.append(f"고아 입출력: {fname} SW ID '{sw}' ({x.name}) — SW기본정보에 없음")
                rep.warnings += 1
                self._issue(rep, IO_SHEET, n, sw, "Tool ID", sw, "Tool ID 가 기본정보에 없음",
                            "Tool 기본정보 시트의 Tool ID 와 똑같이 적어 주세요")
            elif owner.sw_id != sw:
                warnings.append(f"Tool ID 표기 차이: {fname} '{sw}' → '{owner.sw_id}' 로 연결")
                rep.warnings += 1
            if dval and x.direction_short == "?":                      # #11 방향을 못 읽으면 연결 계산에서 빠진다
                warnings.append(f"방향 값 인식 못 함: {where} '{dval}' — 연결 계산에서 빠짐 (config/value_aliases.yaml 로 대응)")
                rep.warnings += 1
            x.exts, x.inhouse, x.bad_ext = self.norm.extensions(v.get("extensions_raw"))
            self._check_extensions(rep, x, n, sw, cols_i["extensions_raw"].header, warnings)
            x.partner_names = self.norm.split_partners(v.get("partner_raw"))
            ios.append(x)
            rep.io_rows += 1
        if aliased:
            warnings.append(f"값 대응표 적용: {fname} {aliased}건 (config/value_aliases.yaml)")
            rep.warnings += 1
        if self._na_cells:
            warnings.append(f"빈 값 표기(NA·-·해당없음 등) 드롭다운 칸: {fname} {self._na_cells}칸 — 선택지 검사에서 뺌 (원문 보존)")
            rep.warnings += 1
        if self._na_int_cells:
            warnings.append(f"빈 값 표기 정수 칸: {fname} {self._na_int_cells}칸 — 빈칸으로 봄 (docs/09 #21)")
            rep.warnings += 1
        # 입출력이 하나도 없는 툴사용 — 정상 고립일 수 있어 '확인 요청' 으로만 수정 요청표에 싣는다 (docs/11 3장 6번, 경고 아님)
        owners = {id(x.owner) for x in ios if x.owner is not None}
        for u in usages:
            if id(u) not in owners:
                self._issue(rep, USAGE_SHEET, u.row, u.sw_id, "Tool ID", None, "입출력 없음",
                            "확인 요청 — 정상일 수 있음: 이 Tool 의 입출력이 Tool 입출력 시트에 없습니다. "
                            "주고받는 데이터가 있으면 적어 주세요 (없으면 그대로 두셔도 됩니다)")
        return usages, ios

    def _part_of(self, rep: FileReport, tool_id, warnings: list, row: int) -> str | None:
        """행의 파트: 보통 파일 약칭, 묶음 파일(parts.yaml file_bundles)은 Tool ID 앞부분 (docs/10 3-1)."""
        if rep.field not in self.bundles:
            return rep.field
        prefix = id_key(tool_id).split("-")[0]
        if prefix in self.bundles[rep.field]:
            return prefix
        warnings.append(f"묶음 파일 파트 미정: {rep.name} {nfc_strip(tool_id)} — Tool ID 앞부분이 {self.bundles[rep.field]} 가 아님, "
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
            warnings.append(f"확장자 매핑 실패: {rep.name} {sw} '{self._q(x.name)}' 토큰 {PERSON_MASK if masked else x.bad_ext} — 원문 보존")
            rep.warnings += 1
        if multi:
            warnings.append(f"확장자 다중 점 확인: {rep.name} {sw} '{self._q(x.name)}' 토큰 {PERSON_MASK if masked else multi} — 그대로 사용 "
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
                    if warnings is not None:
                        warnings.append(f"툴 별칭 순환: {' ↔ '.join(cyc)} — 가장 작은 키 '{cyc[0]}' 를 대표로 (config/tool_aliases.yaml 확인)")
                    return cyc[0]
                path.append(nxt)
            return path[-1]

        closed = {k: root(k) for k in list(amap)}
        closed = {k: v for k, v in closed.items() if k != v}
        distinct = {tuple(sorted(p)) for p in (self.aliases_cfg.get("distinct") or [])}
        for k, v in closed.items():
            if tuple(sorted((k, v))) in distinct and warnings is not None:
                warnings.append(f"툴 별칭과 별개 판정이 충돌: {k} / {v} — 통합이 적용됨 (config/tool_aliases.yaml distinct 확인)")
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

        접두 흡수는 2단계 — 먼저 모든 툴사용의 키를 정하고, 그 키 집합 위에서 흡수 쌍(k, rest)을 구한 뒤 모든 툴사용에 적용한다
        (행 순서에 따라 결과가 달라지지 않게). 생존 키는 _absorptions() 가 고른다. 흡수된 키는 alias_map 에도 넣어
        레지스트리의 옛 행이 통합됨으로 바뀌게 한다."""
        warnings = warnings if warnings is not None else []
        raw_keys: dict[int, str] = {}
        for u in usages:
            k = self.norm.tool_key(u.v.get("reported_tool_name"), u.v.get("reported_vendor"))
            if self.norm.is_generic_key(k):
                k = f"{GENERIC_KEY_PREFIX}{u.field}/{u.reg_key}"          # 파일 간 충돌 행은 구분 꼬리까지 (I34·I36)
                warnings.append(f"툴 이름 범용/비어 있음: {u.file} {u.sw_id} — 통합하지 않고 행별 툴로 둠 (툴 이름 요청)")
                rep = (reports or {}).get(u.file)
                if rep is not None:
                    rep.warnings += 1
                    self._issue(rep, USAGE_SHEET, u.row, u.sw_id, "Tool명(정식)", u.v.get("reported_tool_name"), "툴 이름 범용/비어 있음",
                                "툴 이름을 지어 주세요 — 분야마다 자체개발 툴이 달라 통합할 수 없습니다 "
                                "(예: '<업무>용 <무엇> 계산기' 처럼 다른 파트가 알아볼 이름)")
            raw_keys[id(u)] = amap.get(k, k)
        absorb, reasons, self.prefix_held = self._absorptions(set(raw_keys.values()), usages, amap, warnings)
        for key, v in list(amap.items()):                        # 흡수 뒤 별칭 사슬을 다시 닫는다 — '엑셀'→excel→microsoftexcel 이 한 번에
            if v in absorb:                                      # (연계 SW명 해석·레지스트리 통합됨 표시는 amap.get 한 번만 본다)
                amap[key] = absorb[v]
        tools: dict[str, ToolGroup] = {}
        for u in usages:
            k = raw_keys[id(u)]
            if k in absorb:
                survivor = absorb[k]
                warnings.append(f"제조사 접두 흡수: {u.file} {u.sw_id} '{k}' → '{survivor}' ({reasons[k]})")
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
                    warnings.append(f"제조사 접두 흡수와 별개 판정이 충돌: {a} / {b} — 흡수하지 않음")
                continue
            active = sorted(k for k in members if k in known)
            if len(active) >= 2:
                warnings.append(f"제조사 접두 흡수 보류: 기존 툴 둘 이상 ({', '.join(active)}) — 검토표에서 판정")
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

    def _resolve_partners(self, ios, usages, tools, amap, warnings: list) -> None:
        """연계 SW명 → 툴 (I1): 키가 같거나, 조사에 나온 제조사명(범용 제조사 제외)을 앞에서 뗀 키가 같으면 그 툴.
        사람 이름처럼 보이는 표기는 조사 누락 후보에 올리지 않는다 (#20-2)."""
        vendors = self.norm.survey_vendors(u.v.get("reported_vendor") for u in usages)

        def resolve(name: str) -> str | None:
            k = self.norm.tool_key(name)
            k = amap.get(k, k)
            if k in tools:
                return k
            for vk in vendors:
                rest = k[len(vk):]
                if k.startswith(vk) and rest:
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
                    warnings.append(f"연계 Tool명이 인명처럼 보임: {x.file} {x.sw_id} '{x.name}' — 조사 누락 후보에서 뺌")
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
                                "names_a": tools[a].names, "names_b": tools[b].names})
        return out

    @staticmethod
    def _conflicts(tools) -> dict:
        out = {}
        for k, g in tools.items():
            for attr, slot in (("vendor", "reported_vendor"), ("kind", "reported_kind")):
                c = Counter(nfc_strip(u.v.get(slot)) for u in g.usages)
                if len(c) > 1:
                    out.setdefault(k, {})[attr] = {"majority": g.majority(slot), "values": dict(sorted(c.items()))}
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
                    warnings.append(f"완전 중복 입출력 행: {x.key} — 경고 후 순번")
                    reports[x.file].warnings += 1
                seen[sig] += 1


# --------------------------------------------------------------------------- 템플릿 예시
def extract_template_examples(form_xlsx: Path, config_dir: Path | None = None) -> dict:
    """양식의 예시 행(데이터 시작 행부터 내용이 있는 행)을 슬롯 이름으로 뽑는다 → config/template_examples.yaml."""
    rules = load_yaml("rules.yaml", config_dir)["loader"]
    spec = load_form_spec(config_dir=config_dir)
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


def write_template_examples(forms: list[Path], config_dir: Path | None = None) -> Path:
    """여러 양식판의 예시 행을 합쳐 쓴다 (v1.0 + v1.1, M3.1)."""
    data: dict[str, list] = {USAGE_SHEET: [], IO_SHEET: []}
    for form in forms:
        for sheet, rows in extract_template_examples(form, config_dir).items():
            data[sheet] += [r for r in rows if r not in data[sheet]]
    path = (config_dir or CONFIG_DIR) / "template_examples.yaml"
    head = (f"# 템플릿 예시 행 (docs/02 2장, 골든 I15) — {', '.join(f.name for f in forms)} 에서 추출.\n"
            "# 다시 만들기: python -m engenius_onto template-examples --form <양식 xlsx> [--form <양식 xlsx> ...]\n"
            "# 적재 열(스키마 양식 열) 전체가 여기 한 행과 같으면 위치와 무관하게 적재에서 제외한다.\n"
            "# 수식 열(SW명·Tool명 자동)과 '실무 문의처' 열은 적재 열이 아니라 여기에도 없다 (인명 미저장).\n")
    body = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000)
    path.write_text(head + body, encoding="utf-8", newline="\n")
    return path
