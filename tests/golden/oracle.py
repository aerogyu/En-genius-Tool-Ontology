"""M2 독립 참조 계산 — docs/02 5~7장 규칙을 합성 명세(survey_spec.yaml)에 그대로 적용한다.

목적: 골든 기대값(expected.yaml)의 집계를 사람이 손으로 세지 않고 재현 가능하게 만들고, M3·M4 구현
(적재기·SPARQL 규칙)과 **서로 독립인** 두 번째 구현으로 대조하는 것. 그래서 src/ 코드를 import 하지 않는다.
docs/02 가 정하지 않은 세부는 여기서 정한 해석을 expected.yaml 'interpretations' 에 적고 M3·M4 가 따른다.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field

# docs/02 9장 rules.yaml 예시값 그대로
MANUAL_TRANSFER = {"메일·수기 전달"}
NOTE_KEYWORDS = ("수기", "수작업", "손으로", "복사", "재입력")
AUTO_OPS = {"CLI 지원", "GUI+CLI"}
NON_AUTO_IF = {"없음", "모름"}
AIRGAP_EXCLUDED = {"불가"}
GENERIC_EXT = {"xlsx", "xls", "csv", "txt", "pdf", "docx", "pptx", "hwp"}
FREQ_RANK = {"매일": 4, "주 1회 이상": 3, "월 1회 이상": 2, "분기 이하": 1}
PRIO_RANK = {"상": 3, "중": 2, "하": 1}
GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "제외": 3}
FUZZY = 0.85

EXT_ALIAS = {"step": "stp", "iges": "igs", "jpeg": "jpg", "tif": "tiff", "yml": "yaml",
             "엑셀": "xlsx", "워드": "docx", "파워포인트": "pptx", "한글": "hwp", "텍스트": "txt"}
EXT_EMPTY = {"없음", "모름", "-", ""}
EXT_OK = re.compile(r"^[a-z0-9_+\-]+(\.[a-z0-9_+\-]+)*$")
VERSION_TOKEN = re.compile(r"^(v\d+(\.\d+)*|\d{4}r\d+|r\d+[a-z]?|sp\d+|\d+(\.\d+)+)$")


# --------------------------------------------------------------------------- 정규화 (docs/02 6장)
def _base(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").lower()
    return re.sub(r"\([^)]*\)", " ", s)


def _alnum(s: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", s)


def tool_key(name: str, vendor: str | None = None) -> str:
    """NFKC → 소문자 → 괄호 주석 제거 → 버전 토큰 제거 → 영숫자·한글만 → 제조사 접두 제거 (6.1-2)."""
    tokens = [t for t in re.split(r"\s+", _base(name).strip()) if t and not VERSION_TOKEN.match(t)]
    key = _alnum("".join(tokens))
    v = _alnum(_base(vendor or ""))
    if v and key.startswith(v) and len(key) > len(v):
        key = key[len(v):]
    return key


def split_partners(raw: str | None) -> list[str]:
    return [p.strip() for p in re.split(r"[,;/·]", raw or "") if p.strip()]


def normalize_extensions(raw) -> tuple[list[str], bool, list[str]]:
    """(정규화 확장자 목록, 사내 표기 여부, 매핑 못 한 토큰) — docs/02 6.2."""
    s = unicodedata.normalize("NFKC", str(raw or "")).lower()
    inhouse = "사내" in s
    s = s.replace("(사내)", " ").replace("사내", " ")
    out, bad = [], []
    for tok in re.split(r"[/,;·\s]+", s):
        tok = tok.strip().lstrip(".*").strip()
        if tok in EXT_EMPTY:
            continue
        tok = EXT_ALIAS.get(tok, tok)
        (out if EXT_OK.match(tok) else bad).append(tok)
    return sorted(set(out)), inhouse, bad


# --------------------------------------------------------------------------- 모델
@dataclass
class Usage:
    file_field: str
    field: str
    sw_id: str
    name: str
    vendor: str
    kind: str
    op: str
    auto_if: str
    airgap: str
    freq: str
    users: object
    prio: str
    row: int
    tool: str = ""          # tool key

    @property
    def key(self) -> str:
        return f"{self.field}/{self.sw_id}"

    @property
    def automatable(self) -> bool:
        return self.op in AUTO_OPS or bool(self.auto_if and self.auto_if not in NON_AUTO_IF)

    def sort_key(self):
        users = self.users if isinstance(self.users, int) else -1
        return (FREQ_RANK.get(self.freq, 0), users, PRIO_RANK.get(self.prio, 0))


@dataclass
class IO:
    file_field: str
    sw_id: str
    direction: str          # in / out
    name: str
    cat: str
    ext_raw: str
    exts: list
    inhouse: bool
    ext_bad: list
    transfer: str
    partner_raw: str
    note: str
    owner: Usage | None
    seq: int = 0            # 같은 키 완전 중복 행 순번 (D2)
    partner_tools: set = field(default_factory=set)
    partner_unresolved: list = field(default_factory=list)

    @property
    def key(self) -> str:
        owner = self.owner.key if self.owner else f"{self.file_field}/{self.sw_id}(고아)"
        k = f"{owner}/{self.direction}/{self.name}"
        if self.transfer_differs:
            k += f"[{self.transfer}|{self.partner_raw}]"
        return k + (f"#{self.seq}" if self.seq else "")

    transfer_differs: bool = False


@dataclass
class Feed:
    o: IO
    i: IO
    matched: list
    confidence: str
    declared: bool
    manual: bool
    manual_basis: str | None
    grade: str | None


# --------------------------------------------------------------------------- 계산
def grade(supplier: Usage, consumer: Usage) -> str:
    if supplier.airgap in AIRGAP_EXCLUDED or consumer.airgap in AIRGAP_EXCLUDED:
        return "제외"
    n = supplier.automatable + consumer.automatable
    return {2: "A", 1: "B", 0: "C"}[n]


def compute(spec: dict) -> dict:
    du, di = spec["defaults"]["usage"], spec["defaults"]["io"]
    usages: list[Usage] = []
    warnings: list[str] = []
    by_file_id: dict[tuple[str, str], Usage] = {}
    for f in spec["files"]:
        ff = f["field"]
        for n, u in enumerate(f["usages"]):
            v = {**du, **u}
            us = Usage(ff, v.get("field_cell", ff), str(v["sw_id"]), v["name"], v["vendor"], v["kind"], v["op"],
                       v["auto_if"], v["airgap"], v["freq"], v["users"], v["prio"], n)
            if (ff, us.sw_id) in by_file_id:
                warnings.append(f"중복 SW ID: {ff} 파일 {us.sw_id} — 먼저 나온 행 사용, '{us.name}' 행 제외")
                continue
            if us.field != ff:
                warnings.append(f"파일 분야 ≠ 담당 부서: {ff} 파일 {us.sw_id} → 담당 부서 '{us.field}'")
            if not isinstance(us.users, int):
                warnings.append(f"사용 인원수 정수 변환 실패: {us.key} '{us.users}' — 원문 보존")
            by_file_id[(ff, us.sw_id)] = us
            usages.append(us)

    vendors = {_alnum(_base(u.vendor)) for u in usages if _alnum(_base(u.vendor))}
    for u in usages:
        u.tool = tool_key(u.name, u.vendor)
    tools = defaultdict(list)
    for u in usages:
        tools[u.tool].append(u)

    def resolve(name: str) -> str | None:
        k = tool_key(name)
        if k in tools:
            return k
        for v in sorted(vendors, key=len, reverse=True):   # 연계 SW명에는 제조사 열이 없다 — 알려진 제조사 접두 제거
            if k.startswith(v) and k[len(v):] in tools:
                return k[len(v):]
        return None

    ios: list[IO] = []
    for f in spec["files"]:
        ff = f["field"]
        for r in f["ios"]:
            if r.get("blank"):
                continue
            v = {**di, **r}
            exts, inhouse, bad = normalize_extensions(v["ext"])
            owner = by_file_id.get((ff, str(v["sw_id"])))
            io = IO(ff, str(v["sw_id"]), v["dir"], v["name"], v["cat"], str(v["ext"]), exts, inhouse, bad,
                    v["transfer"], v.get("partner") or "", v.get("note") or "", owner)
            if owner is None:
                warnings.append(f"고아 입출력: {ff} 파일 SW ID '{io.sw_id}' ({io.name}) — SW기본정보에 없음")
            if bad:
                warnings.append(f"확장자 매핑 실패: {io.key} 토큰 {bad} — 원문 보존")
            for p in split_partners(io.partner_raw):
                t = resolve(p)
                if t:
                    io.partner_tools.add(t)
                else:
                    io.partner_unresolved.append(tool_key(p))
            ios.append(io)

    # D2 IO 키: 같은 (소유, 방향, 명칭) 인데 전달·연계가 다르면 구분, 완전히 같으면 순번
    groups = defaultdict(list)
    for io in ios:
        groups[(io.owner.key if io.owner else io.sw_id, io.direction, io.name, io.cat, io.ext_raw)].append(io)
    for g in groups.values():
        if len(g) > 1:
            sigs = Counter((x.transfer, x.partner_raw) for x in g)
            seen = Counter()
            for x in g:
                sig = (x.transfer, x.partner_raw)
                x.transfer_differs = len(sigs) > 1
                if sigs[sig] > 1:
                    x.seq = seen[sig]
                    if seen[sig]:
                        warnings.append(f"완전 중복 입출력 행: {x.key} — 경고 후 순번")
                    seen[sig] += 1

    owned = [x for x in ios if x.owner]
    feeds: list[Feed] = []
    for o in owned:
        if o.direction != "out":
            continue
        for i in owned:
            if i.direction != "in" or o.cat != i.cat or o.owner is i.owner:
                continue
            m = sorted(set(o.exts) & set(i.exts))
            if not o.exts or not i.exts or not m:
                continue
            manual = o.transfer in MANUAL_TRANSFER or i.transfer in MANUAL_TRANSFER
            basis = "전달방법" if manual else ("비고" if any(k in (o.note + i.note) for k in NOTE_KEYWORDS) else None)
            feeds.append(Feed(
                o, i, m, "낮음" if all(e in GENERIC_EXT for e in m) else "보통",
                (i.owner.tool in o.partner_tools) or (o.owner.tool in i.partner_tools),
                manual, basis, grade(o.owner, i.owner) if manual else None))

    # CQ04 대조 (단위 = 입출력 명세 × 상대 Tool)
    recon = []
    for x in owned:
        comp = {f.o.owner.tool for f in feeds if f.i is x} if x.direction == "in" else \
               {f.i.owner.tool for f in feeds if f.o is x}
        for t in sorted(comp | x.partner_tools):
            if t in comp and t in x.partner_tools:
                v = "확정"
            elif t in x.partner_tools:
                v = "숨은변환 의심"
            else:
                v = "잠재(연계 미기재)" if not x.partner_raw.strip() else "잠재(신고와 다름)"
            recon.append((x, t, v))

    # 착수 순위: 수기 Feed + 변환 구간 (D1-2: 상대 Tool 의 툴사용 각각으로 펼침, 같은 쌍은 한 행)
    handoffs = {}
    for f in feeds:
        if f.manual:
            handoffs[(f.o.owner.key, f.i.owner.key, "수기")] = (f.o.owner, f.i.owner, "수기", f.grade, [f.o.key, f.i.key])
    for x, t, v in recon:
        if v != "숨은변환 의심":
            continue
        for u in tools[t]:
            s, c = (u, x.owner) if x.direction == "in" else (x.owner, u)
            k = (s.key, c.key, "변환")
            ent = handoffs.setdefault(k, (s, c, "변환", grade(s, c), []))
            ent[4].append(x.key)
    ranked = sorted(handoffs.values(), key=lambda h: (
        GRADE_ORDER[h[3]], *[-v for v in h[1].sort_key()], *[-v for v in h[0].sort_key()], h[0].key, h[1].key))

    # CQ05 고립
    has_io = {x.owner.key for x in owned}
    linked = {f.o.owner.key for f in feeds} | {f.i.owner.key for f in feeds}
    resolved_partner = {x.owner.key for x in owned if x.partner_tools}
    no_io = sorted(u.key for u in usages if u.key not in has_io)
    unlinked = sorted(u.key for u in usages if u.key in has_io and u.key not in linked | resolved_partner)

    # CQ08 허브 (Tool 별 Feed 로 이어진 서로 다른 상대 Tool 수)
    partners = defaultdict(set)
    for f in feeds:
        a, b = f.o.owner.tool, f.i.owner.tool
        if a != b:
            partners[a].add(b)
            partners[b].add(a)

    # CQ09 조사 누락 후보
    missing = defaultdict(lambda: {"mentions": 0, "fields": set()})
    for x in ios:
        for k in x.partner_unresolved:
            missing[k]["mentions"] += 1
            missing[k]["fields"].add(x.owner.field if x.owner else x.file_field)

    # CQ10 표기 변형·통합 후보·제조사/구분 엇갈림
    keys = sorted(tools)
    candidates = sorted({tuple(sorted((a, b))) for a in keys for b in keys if a < b and (
        a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() >= FUZZY)})
    conflicts = {}
    for k, us in tools.items():
        for attr in ("vendor", "kind"):
            c = Counter(getattr(u, attr) for u in us)
            if len(c) > 1:
                conflicts.setdefault(k, {})[attr] = {"majority": c.most_common(1)[0][0], "values": dict(c)}

    # CQ07 분야 매트릭스
    matrix, matrix_manual = Counter(), Counter()
    for f in feeds:
        matrix[(f.o.owner.field, f.i.owner.field)] += 1
        if f.manual:
            matrix_manual[(f.o.owner.field, f.i.owner.field)] += 1

    return dict(usages=usages, tools=tools, ios=ios, feeds=feeds, recon=recon, ranked=ranked,
                no_io=no_io, unlinked=unlinked, partners=partners, missing=missing,
                candidates=candidates, conflicts=conflicts, matrix=matrix, matrix_manual=matrix_manual,
                warnings=warnings)


def downstream(result: dict, start_keys: set[str]) -> list[str]:
    """eg:feeds+ 로 도달하는 하류 툴사용 (CQ01·CQ06)."""
    succ = defaultdict(set)
    for f in result["feeds"]:
        succ[f.o.owner.key].add(f.i.owner.key)
    seen, stack = set(), list(start_keys)
    while stack:
        for n in succ[stack.pop()]:
            if n not in seen:
                seen.add(n)
                stack.append(n)
    return sorted(seen)


def summarize(result: dict) -> dict:
    """expected.yaml 'aggregates' 와 같은 모양의 요약 (사람이 읽고 커밋하는 값)."""
    feeds = result["feeds"]
    tools = result["tools"]

    def tname(k):   # 툴은 정규화 키로 가리킨다 — 대표 이름(prefLabel) 선정은 M3 몫이라 골든에서 검사하지 않음
        return k

    rv = Counter(v for _, _, v in result["recon"])
    impact_start = {f.i.owner.key for f in feeds if f.i.cat == "해석-결과" and "csv" in f.i.exts} | \
                   {x.owner.key for x in result["ios"] if x.owner and x.direction == "in"
                    and x.cat == "해석-결과" and "csv" in x.exts}
    return {
        "counts": {
            "usages": len(result["usages"]), "tools": len(tools), "io_specs": len(result["ios"]),
            "orphan_io_specs": sum(1 for x in result["ios"] if not x.owner),
            "fields": len({u.field for u in result["usages"]}),
            "categories": len({x.cat for x in result["ios"]}),
            "feeds": len(feeds), "feeds_manual": sum(f.manual for f in feeds),
            "feeds_note_signal": sum(f.manual_basis == "비고" for f in feeds),
            "feeds_low_confidence": sum(f.confidence == "낮음" for f in feeds),
            "feeds_declared": sum(f.declared for f in feeds),
        },
        "reconciliation_counts": dict(sorted(rv.items())),
        "handoff_ranking": [
            {"supplier": h[0].key, "consumer": h[1].key, "kind": h[2], "grade": h[3]} for h in result["ranked"]],
        "isolated": {"no_io": result["no_io"], "unlinked": result["unlinked"]},
        "hub_partner_counts": dict(sorted(((tname(k), len(v)) for k, v in result["partners"].items()),
                                          key=lambda kv: (-kv[1], kv[0]))),
        "missing_tools": {k: {"mentions": v["mentions"], "fields": sorted(v["fields"])}
                          for k, v in sorted(result["missing"].items())},
        "tools": {k: sorted({u.name for u in us}) for k, us in sorted(tools.items())},
        "merge_candidates": [[tname(a), tname(b)] for a, b in result["candidates"]],
        "attribute_conflicts": {tname(k): v for k, v in sorted(result["conflicts"].items())},
        "field_matrix": {f"{a} → {b}": n for (a, b), n in sorted(result["matrix"].items())},
        "field_matrix_manual": {f"{a} → {b}": n for (a, b), n in sorted(result["matrix_manual"].items())},
        "impact_해석결과_csv": sorted(impact_start | set(downstream(result, impact_start))),
        "downstream_of_성능_PERF-01": downstream(result, {"성능/PERF-01"}),
        "warnings": sorted(result["warnings"]),
    }
