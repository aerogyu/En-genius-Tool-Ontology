"""조사 엑셀 적재 (docs/02 5·6장, M3).

분야별 xlsx 를 읽어 툴사용(SW기본정보 행)·입출력(SW입출력 행)으로 만들고, 툴 통합·확장자·연계 SW명을 정규화한다.
RDF 로 쓰는 것은 rdf_writer, ID 고정은 registry 가 맡는다. 세부 해석의 정본은 골든 interpretations (I번호).

- 헤더 이름으로 매핑 (NFKC 후 공백·'*' 무시, I30) — 매핑 안 된 헤더는 경고, 의도적 제외 열(B 수식·K 문의처)은 읽지 않는다.
- 예시 행은 위치가 아니라 적재 열 전체가 템플릿 예시와 같은지로 판별 (I15) — config/template_examples.yaml.
- 같은 분야 파일이 여럿이면 (날짜, 파일명) 최신 1개만 적재 (I33).
- 어떤 행도 조용히 버리지 않는다 — 제외는 사유와 함께 excluded_rows, 문제는 warnings (5장 6).
- 인명 열(실무 문의처)은 읽지 않는다 (CLAUDE.md 절대 규칙 5). 자유 텍스트의 인명 유사 패턴은 경고만 (D6).
"""

from __future__ import annotations

import datetime as dt
import difflib
import hashlib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl
import yaml

from engenius_onto.config import CONFIG_DIR, load_yaml
from engenius_onto.form_spec import Column, FormSpec, load_form_spec, norm_header
from engenius_onto.normalize import Normalizer, nfc_strip

USAGE_SHEET, IO_SHEET = "SW기본정보", "SW입출력"


# --------------------------------------------------------------------------- 레코드
@dataclass
class UsageRec:
    file: str
    file_field: str | None
    row: int
    v: dict                         # 슬롯 → 값 (문자열·정수·None)
    raw: dict = field(default_factory=dict)   # 정수 변환 실패 원문 (슬롯 → 원문)
    tool_key: str = ""
    node_id: str = ""                # 레지스트리 USE ID (rdf_writer 가 채움)

    @property
    def sw_id(self) -> str:
        return nfc_strip(self.v.get("source_key"))

    @property
    def field(self) -> str:
        return nfc_strip(self.v.get("usage_field"))

    @property
    def key(self) -> str:
        return f"{self.field}/{self.sw_id}"


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
        owner = self.owner.key if self.owner else f"{self.file_field}/{self.sw_id}(고아)"
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
    name: str
    sha256: str
    field: str | None
    date: str | None
    superseded_by: str | None = None
    usage_rows: int = 0
    io_rows: int = 0
    excluded: int = 0
    warnings: int = 0

    def stats(self) -> dict:
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

    @property
    def loaded_files(self) -> list[FileReport]:
        return [f for f in self.files if f.superseded_by is None]

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


# --------------------------------------------------------------------------- 적재기
class Loader:
    def __init__(self, config_dir: Path | None = None, schema_file: Path | None = None):
        self.config_dir = config_dir or CONFIG_DIR
        self.rules = load_yaml("rules.yaml", self.config_dir)
        self.lcfg = self.rules["loader"]
        self.norm = Normalizer.from_config(self.config_dir)
        self.spec: FormSpec = load_form_spec(schema_file, self.config_dir)
        self.examples = load_yaml("template_examples.yaml", self.config_dir)
        self.aliases_cfg = load_yaml("tool_aliases.yaml", self.config_dir)
        self.person_re = re.compile(self.rules["person_pattern"])
        self.free_text = set(self.rules["free_text_slots"])
        self.month_slots = set(self.lcfg.get("month_slots", ["license_expiry"]))
        d = self.rules["direction"]
        self.dir_short = {**{x: "in" for x in d["consume"]}, **{x: "out" for x in d["produce"]}}

    # ---- 파일 ------------------------------------------------------------------
    def discover(self, data_dir: Path) -> list[Path]:
        return sorted(p for p in Path(data_dir).glob(self.lcfg["file_pattern"])
                      if p.is_file() and not p.name.startswith("~$"))

    def parse_name(self, name: str) -> tuple[str | None, str | None]:
        m = re.match(self.lcfg["file_name_regex"], name)
        return (m.group("field"), m.group("date")) if m else (None, None)

    def load(self, paths: list[Path]) -> LoadResult:
        warnings: list[str] = []
        reports = []
        for p in paths:
            fld, date = self.parse_name(p.name)
            reports.append(FileReport(p.name, hashlib.sha256(p.read_bytes()).hexdigest(), fld, date))
        by_name = {r.name: r for r in reports}
        # 재발송 (I33): 같은 분야는 (날짜, 파일명) 최신만
        latest: dict[str, FileReport] = {}
        for r in reports:
            if r.field is None:
                continue
            if r.field not in latest or (r.date, r.name) > (latest[r.field].date, latest[r.field].name):
                latest[r.field] = r
        for r in reports:
            if r.field is None:
                warnings.append(f"파일명 규칙 밖: {r.name} — 분야를 알 수 없어 재발송 판정·담당 부서 대조를 하지 않음")
                r.warnings += 1
            elif latest[r.field] is not r:
                r.superseded_by = latest[r.field].name
                warnings.append(f"재발송으로 대체: {r.name} → {r.superseded_by} (적재 안 함)")
                r.warnings += 1

        usages: list[UsageRec] = []
        ios: list[IORec] = []
        excluded: list[dict] = []
        for p in paths:
            rep = by_name[p.name]
            if rep.superseded_by:
                continue
            u, i = self._load_file(p, rep, warnings, excluded)
            usages += u
            ios += i

        alias_map, alias_labels = self._alias_map()
        tools = self._group_tools(usages, alias_map, alias_labels)
        self._resolve_partners(ios, usages, tools, alias_map)
        self._disambiguate(ios, by_name, warnings)
        candidates = self._candidates(tools)
        conflicts = self._conflicts(tools)
        return LoadResult(reports, usages, ios, tools, warnings, excluded, candidates, conflicts, alias_map)

    # ---- 시트 읽기 ----------------------------------------------------------------
    def _read_sheet(self, wb, sheet: str, fname: str, rep: FileReport, warnings: list) -> list[tuple[int, dict]]:
        """(행 번호, {슬롯: 셀 값}) — 빈 행은 건너뛰고, 연속 빈 행이 blank_rows_end 개면 끝."""
        if sheet not in wb.sheetnames:
            warnings.append(f"시트 없음: {fname} '{sheet}' — 이 시트는 적재하지 않음")
            rep.warnings += 1
            return []
        ws = wb[sheet]
        hr, start = self.lcfg["header_row"], self.lcfg["data_start_row"]
        header = next(ws.iter_rows(min_row=hr, max_row=hr, values_only=True), ())
        mapping, by_h = {}, self.spec.by_header(sheet)
        for idx, h in enumerate(header):
            if _blank(h):
                continue
            nh = norm_header(h)
            if nh in by_h:
                mapping[idx] = by_h[nh]
            elif nh not in self.spec.ignored[sheet]:
                warnings.append(f"매핑 안 된 헤더: {fname} {sheet} '{nfc_strip(h)}'")
                rep.warnings += 1
        missing = [c.header for c in self.spec.columns[sheet] if c not in mapping.values()]
        if missing:
            warnings.append(f"양식 열 없음: {fname} {sheet} {missing}")
            rep.warnings += 1
        rows, blanks = [], 0
        for n, cells in enumerate(ws.iter_rows(min_row=start, values_only=True), start=start):
            v = {c.slot: cells[i] if i < len(cells) else None for i, c in mapping.items()}
            if all(_blank(x) for x in v.values()):
                blanks += 1
                if blanks >= self.lcfg["blank_rows_end"]:
                    break
                continue
            blanks = 0
            rows.append((n, v))
        return rows

    def _read_choices(self, wb) -> dict[str, list[str]]:
        name = self.lcfg["choices_sheet"]
        if name not in wb.sheetnames:
            return {}
        rows = list(wb[name].iter_rows(min_row=2, values_only=True))
        out = {}
        for col in zip(*rows):
            vals = [nfc_strip(v) for v in col if not _blank(v)]
            if vals:
                out[vals[0]] = vals[1:]
        return out

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

    def _check(self, sheet: str, v: dict, choices: dict, where: str, warnings: list, rep: FileReport) -> None:
        for col in self.spec.columns[sheet]:
            val = v.get(col.slot)
            if col.required and _blank(val):
                warnings.append(f"필수값 누락: {where} '{col.header}'")
                rep.warnings += 1
                continue
            if col.choice_list and not _blank(val) and choices and str(val) not in choices.get(col.choice_list, []):
                warnings.append(f"선택지 밖 값: {where} '{col.header}' = '{val}'")
                rep.warnings += 1
            if col.slot in self.free_text and not _blank(val) and self.person_re.search(str(val)):
                warnings.append(f"인명 유사 패턴: {where} '{col.header}'")
                rep.warnings += 1

    # ---- 파일 1개 -----------------------------------------------------------------
    def _load_file(self, path: Path, rep: FileReport, warnings: list, excluded: list):
        fname = rep.name
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            choices = self._read_choices(wb)
            if not choices:
                warnings.append(f"선택지 시트 없음: {fname} — 선택지 검사를 하지 않음")
                rep.warnings += 1
            urows = self._read_sheet(wb, USAGE_SHEET, fname, rep, warnings)
            irows = self._read_sheet(wb, IO_SHEET, fname, rep, warnings)
        finally:
            wb.close()
        cols_u = {c.slot: c for c in self.spec.columns[USAGE_SHEET]}
        cols_i = {c.slot: c for c in self.spec.columns[IO_SHEET]}

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
                continue
            where = f"{fname} {USAGE_SHEET} {cell_key(raw.get('source_key'))}"
            v, rawvals = {}, {}
            for slot, val in raw.items():
                v[slot], r = self._convert(cols_u[slot], val, where, warnings, rep)
                if r is not None:
                    rawvals[slot] = r
            self._check(USAGE_SHEET, v, choices, where, warnings, rep)
            u = UsageRec(fname, rep.field, n, v, rawvals)
            if u.sw_id in by_id:
                warnings.append(f"중복 SW ID: {fname} {u.sw_id} — 먼저 나온 행 사용, "
                                f"'{nfc_strip(v.get('reported_tool_name'))}' 행 제외")
                rep.warnings += 1
                exclude(USAGE_SHEET, n, f"중복 SW ID {u.sw_id} (먼저 나온 {by_id[u.sw_id].row}행 사용)")
                continue
            if rep.field is not None and u.field and u.field != rep.field:
                warnings.append(f"파일 분야 ≠ 담당 부서: {fname} {u.sw_id} → '{u.field}'")
                rep.warnings += 1
            for slot, r in rawvals.items():
                warnings.append(f"{cols_u[slot].header.rstrip(' *')} 정수 변환 실패: {fname} {u.sw_id} '{r}' — 원문 보존")
                rep.warnings += 1
            by_id[u.sw_id] = u
            usages.append(u)
            rep.usage_rows += 1

        ios = []
        for n, raw in irows:
            if self._is_example(IO_SHEET, raw):
                exclude(IO_SHEET, n, "템플릿 예시 행 (내용 일치, I15)")
                continue
            if _blank(raw.get("owner_source_key")):
                warnings.append(f"SW ID 없는 내용 행: {fname} {IO_SHEET} '{nfc_strip(raw.get('data_name'))}' — 건너뜀")
                rep.warnings += 1
                exclude(IO_SHEET, n, "SW ID 없음 (I22)")
                continue
            where = f"{fname} {IO_SHEET} {cell_key(raw.get('owner_source_key'))} '{cell_key(raw.get('data_name'))}'"
            v = {}
            for slot, val in raw.items():
                v[slot], _ = self._convert(cols_i[slot], val, where, warnings, rep)
            self._check(IO_SHEET, v, choices, where, warnings, rep)
            sw = nfc_strip(v.get("owner_source_key"))
            owner = by_id.get(sw)                                   # D3: 소유는 같은 파일 안에서
            x = IORec(fname, rep.field, n, v, owner, self.dir_short.get(nfc_strip(v.get("direction")), "?"))
            if owner is None:
                warnings.append(f"고아 입출력: {fname} SW ID '{sw}' ({x.name}) — SW기본정보에 없음")
                rep.warnings += 1
            x.exts, x.inhouse, x.bad_ext = self.norm.extensions(v.get("extensions_raw"))
            if x.bad_ext:
                warnings.append(f"확장자 매핑 실패: {fname} {sw} '{x.name}' 토큰 {x.bad_ext} — 원문 보존")
                rep.warnings += 1
            x.partner_names = self.norm.split_partners(v.get("partner_raw"))
            ios.append(x)
            rep.io_rows += 1
        return usages, ios

    # ---- 툴 통합 (6.1) --------------------------------------------------------------
    def _alias_map(self) -> tuple[dict[str, str], dict[str, str]]:
        """정규화 키 → 대표 키, 대표 키 → 대표 이름 (config/tool_aliases.yaml)."""
        amap, labels = {}, {}
        for rep_name, variants in (self.aliases_cfg.get("aliases") or {}).items():
            rk = self.norm.tool_key(rep_name)
            labels[rk] = nfc_strip(rep_name)
            for name in [rep_name, *(variants or [])]:
                amap[self.norm.tool_key(name)] = rk
        return amap, labels

    def _group_tools(self, usages, amap, labels) -> dict[str, ToolGroup]:
        tools: dict[str, ToolGroup] = {}
        for u in usages:
            k = self.norm.tool_key(u.v.get("reported_tool_name"), u.v.get("reported_vendor"))
            u.tool_key = amap.get(k, k)
            tools.setdefault(u.tool_key, ToolGroup(u.tool_key, [], labels.get(u.tool_key))).usages.append(u)
        return dict(sorted(tools.items()))

    def _resolve_partners(self, ios, usages, tools, amap) -> None:
        """연계 SW명 → 툴 (I1): 키가 같거나, 조사에 나온 제조사명을 앞에서 뗀 키가 같으면 그 툴."""
        vendors = sorted({self.norm.vendor_key(u.v.get("reported_vendor")) for u in usages} - {""},
                         key=len, reverse=True)

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
                else:
                    x.partner_unresolved.append(self.norm.tool_key(p))

    def _candidates(self, tools) -> list[dict]:
        """통합 후보 (I23) — 자동 통합하지 않는다. 별개 판정 쌍(distinct)은 제외."""
        distinct = {tuple(sorted(p)) for p in (self.aliases_cfg.get("distinct") or [])}
        th = float(self.rules["fuzzy_threshold"])
        keys = sorted(tools)
        out = []
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                if (a, b) in distinct:
                    continue
                r = max(difflib.SequenceMatcher(None, a, b).ratio(), difflib.SequenceMatcher(None, b, a).ratio())
                if a in b or b in a or r >= th:
                    out.append({"a": a, "b": b, "similarity": round(r, 3),
                                "reason": "포함" if (a in b or b in a) else "유사도",
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
    """원본 양식의 예시 행(데이터 시작 행부터 내용이 있는 행)을 슬롯 이름으로 뽑는다 → config/template_examples.yaml."""
    rules = load_yaml("rules.yaml", config_dir)["loader"]
    spec = load_form_spec(config_dir=config_dir)
    wb = openpyxl.load_workbook(form_xlsx, read_only=True, data_only=True)
    out = {}
    try:
        for sheet in (USAGE_SHEET, IO_SHEET):
            ws = wb[sheet]
            header = next(ws.iter_rows(min_row=rules["header_row"], max_row=rules["header_row"], values_only=True))
            by_h = spec.by_header(sheet)
            idx = {i: by_h[norm_header(h)].slot for i, h in enumerate(header) if not _blank(h) and norm_header(h) in by_h}
            rows = []
            for cells in ws.iter_rows(min_row=rules["data_start_row"], values_only=True):
                v = {s: cells[i] for i, s in idx.items() if i < len(cells) and not _blank(cells[i])}
                if v:
                    rows.append({s: (x if isinstance(x, (int, float)) else cell_key(x)) for s, x in v.items()})
            out[sheet] = rows
    finally:
        wb.close()
    return out


def write_template_examples(form_xlsx: Path, config_dir: Path | None = None) -> Path:
    data = extract_template_examples(form_xlsx, config_dir)
    path = (config_dir or CONFIG_DIR) / "template_examples.yaml"
    head = (f"# 템플릿 예시 행 (docs/02 2장, 골든 I15) — {form_xlsx.name} 에서 추출.\n"
            "# 다시 만들기: python -m engenius_onto template-examples --form <양식 xlsx>\n"
            "# 적재 열(스키마 양식 열) 전체가 여기 한 행과 같으면 위치와 무관하게 적재에서 제외한다.\n"
            "# B 'SW명(자동)' 수식 열과 K '실무 문의처' 열은 적재 열이 아니라 여기에도 없다 (인명 미저장).\n")
    body = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000)
    path.write_text(head + body, encoding="utf-8", newline="\n")
    return path
