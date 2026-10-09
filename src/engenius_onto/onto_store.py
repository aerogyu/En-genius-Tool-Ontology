"""적재한 온톨로지(survey 그래프)를 읽는 질의 층 — MCP 서버(M6 v0)가 쓰고, 테스트는 MCP 없이 이것을 직접 부른다.

- 데이터: 기본은 최신 실행 폴더(실데이터 우선)의 survey.ttl 을 rdflib 로 읽는다 (Fuseki 불필요). backend="fuseki" 면 같은 SPARQL 을
  Fuseki 기본 그래프(= named graph 합집합)에 보낸다 — 두 백엔드 같은 결과 (CLAUDE.md 코드 규칙).
- 정의는 3D 뷰어(scripts/graph_view3d.py)와 같다: 활성 툴만, 방향·수기 값·자동화 판정은 적재가 쓴 rules.yaml(오버레이 포함),
  '연결 상대' = 조사표 연계 Tool명으로 신고된 것 (자기 신고 ∪ 상대 언급, 툴 단위). M4 의 계산 연결(Feed)은 아직 없다.
- 읽기 전용. 자유 텍스트 열에서 인명처럼 보이는 표기는 가린다 (rules.yaml person_pattern·person_patterns_all — 절대 규칙 5).
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from engenius_onto.config import REPO_ROOT, default_overlay_dir, load_config, namespaces
from engenius_onto.registry import ACTIVE

RDFS = "http://www.w3.org/2000/01/rdf-schema#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
MASK = "[인명 추정 가림]"
FREE_TEXT = ("task_summary", "purpose_detail", "automation_detail", "automation_wish", "pain_points", "roadmap_note", "note")


def part_code(label: str) -> str:
    """파트 라벨 '정식 이름 (약칭)' 에서 약칭 — 없으면 라벨 그대로 (graph_view3d.part_code 와 같다)."""
    m = re.match(r"^.*\(([^()]+)\)\s*$", label)
    return m.group(1).strip() if m else label


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s or "")).lower()


def _overlay_of(run: Path) -> Path | None:
    """적재가 쓴 오버레이 폴더 — load_log 의 config_overlay 를 따른다 (graph_view3d.overlay_dir_of 와 같은 규칙)."""
    try:
        log = json.loads((run / "load_log.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default_overlay_dir()
    ov = log.get("config_overlay")
    if ov is None:
        return default_overlay_dir()
    if not ov.get("used") or not ov.get("dir"):
        return None
    d = Path(ov["dir"])
    d = d if d.is_absolute() else REPO_ROOT / d
    return d if d.is_dir() else None


@dataclass
class Snapshot:
    """한 실행 폴더를 읽어 만든 메모리 표 — 툴·툴사용·입출력 (DB 비유: 질의용 뷰를 한 번 만들어 둔 것)."""
    run: str
    dataset: str
    tools: dict = field(default_factory=dict)      # 툴 IRI → {name, alt, vendor, kind}
    parts: dict = field(default_factory=dict)      # 파트 IRI → {code, name}
    usages: dict = field(default_factory=dict)     # 툴사용 IRI → {tool, part, sw_id, name, props…, auto}
    ios: list = field(default_factory=list)        # [{owner, dir, name, cat, exts, tm, kind, partners, partner_raw, note}]
    aliases: dict = field(default_factory=dict)    # 대표 이름(정규화) → {변형 표기(정규화)} — tool_aliases.yaml (+ 오버레이)


class OntologyStore:
    def __init__(self, run: Path | None = None, output_root: Path | None = None, backend: str = "local", prefer: str = "real"):
        self.fixed_run = Path(run) if run else None
        self.output_root = Path(output_root or REPO_ROOT / "output")
        self.backend, self.prefer = backend, prefer
        self._snap: Snapshot | None = None
        self._key = None

    # ---- 실행 폴더 고르기 · 다시 읽기 ----------------------------------------------------------
    def _run_dir(self) -> Path:
        from engenius_onto.survey_load import latest_run

        run = self.fixed_run or latest_run(self.output_root, prefer=self.prefer)
        if not run or not (Path(run) / "survey.ttl").is_file():
            raise FileNotFoundError("적재 결과(survey.ttl)가 없다 — 먼저 scripts\\load.bat 로 적재한다")
        return Path(run)

    def snapshot(self) -> Snapshot:
        """최신 실행이 바뀌었으면(재적재) 다시 읽는다 — MCP 서버는 오래 떠 있으므로 호출마다 확인한다."""
        run = self._run_dir()
        key = (str(run), (run / "survey.ttl").stat().st_mtime_ns)
        if self._snap is None or key != self._key:
            self._snap, self._key = self._build(run), key
        return self._snap

    def _select(self, run: Path, q: str) -> list[dict]:
        if self.backend == "fuseki":
            from engenius_onto.backends import select
            from engenius_onto.config import fuseki_config

            return select(fuseki_config(), q)
        if getattr(self, "_graph_run", None) != run:
            from rdflib import Graph

            g = Graph()
            g.parse(run / "survey.ttl", format="turtle")
            self._graph, self._graph_run = g, run
        return [{k: str(v) for k, v in r.asdict().items()} for r in self._graph.query(q)]

    def _build(self, run: Path) -> Snapshot:
        from engenius_onto.survey_load import run_dataset

        ns = namespaces()
        pfx = f"PREFIX eg: <{ns['eg']}>\nPREFIX rdfs: <{RDFS}>\nPREFIX skos: <{SKOS}>\n"
        rules, _ = load_config("rules.yaml", overlay_dir=_overlay_of(run))
        consume, produce = set(rules["direction"]["consume"]), set(rules["direction"]["produce"])
        manual_values = set(rules["manual_transfer_values"])
        note_keywords = list(rules["manual_note_keywords"])
        auto_modes, non_auto_if = set(rules["automatable"]["operation_modes"]), set(rules["automatable"]["non_automation_if"])
        self._person = [re.compile(rules["person_pattern"])] + [re.compile(p) for p in rules.get("person_patterns_all") or []]
        snap = Snapshot(run=run.name, dataset=run_dataset(run))
        aliases_cfg, _ = load_config("tool_aliases.yaml", overlay_dir=_overlay_of(run))
        for rep, vs in (aliases_cfg.get("aliases") or {}).items():
            snap.aliases.setdefault(_norm(rep), set()).update(_norm(v) for v in vs or [])
        sel = lambda q: self._select(run, pfx + q)  # noqa: E731

        for r in sel("SELECT ?t ?tl ?st ?v ?k WHERE { ?t a eg:Tool ; rdfs:label ?tl . OPTIONAL { ?t eg:status ?st } "
                     "OPTIONAL { ?t eg:vendor ?v } OPTIONAL { ?t eg:kind ?k } }"):
            if r.get("st") and r["st"] != ACTIVE:
                continue                                     # 통합됨·폐기 툴은 빼고 (뷰어와 같다)
            snap.tools[r["t"]] = {"name": r["tl"], "alt": [], "vendor": r.get("v", ""), "kind": r.get("k", "")}
        for r in sel("SELECT ?t ?a WHERE { ?t a eg:Tool ; skos:altLabel ?a }"):
            if r["t"] in snap.tools:
                snap.tools[r["t"]]["alt"].append(r["a"])
        for r in sel("SELECT ?f ?fl WHERE { ?f a eg:Field ; rdfs:label ?fl }"):
            snap.parts[r["f"]] = {"code": part_code(r["fl"]), "name": r["fl"]}

        props: dict[str, dict] = defaultdict(dict)
        for r in sel("SELECT ?u ?p ?o WHERE { ?u a eg:ToolUsage ; ?p ?o . FILTER(isLiteral(?o)) }"):
            props[r["u"]][r["p"].rsplit("/", 1)[-1].rsplit("#", 1)[-1]] = r["o"]
        for r in sel("SELECT ?u ?t ?f WHERE { ?u a eg:ToolUsage ; eg:usage_tool ?t ; eg:usage_field ?f }"):
            if r["t"] not in snap.tools:
                continue
            p = props.get(r["u"], {})
            op, aif = p.get("operation_mode", ""), p.get("automation_if", "")
            snap.usages[r["u"]] = {"tool": r["t"], "part": snap.parts.get(r["f"], {}).get("code", ""), "sw_id": p.get("source_key", ""),
                                   "name": p.get("reported_tool_name", ""), "props": p,
                                   "auto": op in auto_modes or (bool(aif) and aif not in non_auto_if)}

        cats = {r["c"]: r["cl"] for r in sel("SELECT ?c ?cl WHERE { ?c a eg:DataCategory ; rdfs:label ?cl }")}
        partners: dict[str, list] = defaultdict(list)                # 입출력 하나가 상대 툴 여럿을 적을 수 있다 (연계 Tool명 '·' 구분)
        for r in sel("SELECT ?io ?pt WHERE { ?io a eg:IOSpec ; eg:partner_tools ?pt }"):
            if r["pt"] in snap.tools:
                partners[r["io"]].append(r["pt"])
        for r in sel("""SELECT ?io ?u ?dir ?name ?cat ?tm ?praw ?note (GROUP_CONCAT(DISTINCT STR(?ext); separator=", ") AS ?exts) WHERE {
                          ?io a eg:IOSpec ; eg:io_owner ?u ; eg:direction ?dir ; eg:data_name ?name ; eg:transfer_method ?tm .
                          OPTIONAL { ?io eg:io_category ?cat } OPTIONAL { ?io eg:partner_raw ?praw }
                          OPTIONAL { ?io eg:note ?note } OPTIONAL { ?io eg:extensions ?ext }
                        } GROUP BY ?io ?u ?dir ?name ?cat ?tm ?praw ?note"""):
            if r["u"] not in snap.usages:
                continue
            d = "입력" if r["dir"] in consume else "출력" if r["dir"] in produce else "?"
            note = r.get("note", "")
            kind = "수기" if r["tm"] in manual_values else "비고" if any(k in note for k in note_keywords) else ""
            snap.ios.append({"io": r["io"], "owner": r["u"], "dir": d, "name": r["name"], "cat": cats.get(r.get("cat", ""), ""),
                             "exts": r.get("exts", ""), "tm": r["tm"], "kind": kind, "partners": sorted(partners.get(r["io"], [])),
                             "partner_raw": r.get("praw", ""), "note": note})
        snap.ios.sort(key=lambda x: x["io"])
        return snap

    def _partner_text(self, snap: Snapshot, x: dict) -> str:
        return " · ".join(snap.tools[p]["name"] for p in x["partners"]) if x["partners"] else x["partner_raw"]

    # ---- 공통 ---------------------------------------------------------------------------------
    def redact(self, s: str) -> str:
        """인명처럼 보이는 표기를 가린다 — 값은 그래프에 보존돼 있지만(D6) 에이전트·LLM 으로는 내보내지 않는다."""
        if not s:
            return s
        for p in self._person:
            s = p.sub(MASK, s)
        return s

    def resolve_tools(self, query: str) -> list[str]:
        """툴 이름(대표·다른 이름·조사표 표기)으로 툴 찾기 — 정확히 같은 것이 있으면 그것만, 없으면 부분 일치 전부."""
        snap, q = self.snapshot(), _norm(query)
        names: dict[str, set] = defaultdict(set)
        for t, v in snap.tools.items():
            names[t] |= {_norm(v["name"]), *(_norm(a) for a in v["alt"])}
        for u in snap.usages.values():
            names[u["tool"]].add(_norm(u["name"]))
        for t, ns in names.items():                                             # tool_aliases.yaml 의 변형 표기 (엑셀 → Excel 등)
            ns |= {v for rep, vs in snap.aliases.items() if rep in ns for v in vs}
        if not q:
            return sorted(snap.tools, key=lambda t: snap.tools[t]["name"])           # 빈 검색어 = 전체 목록
        exact = [t for t, ns in names.items() if q in ns]
        if exact:
            return sorted(exact, key=lambda t: snap.tools[t]["name"])
        return sorted((t for t, ns in names.items() if any(q in n for n in ns)), key=lambda t: snap.tools[t]["name"])

    def resolve_part(self, query: str) -> str | None:
        snap, q = self.snapshot(), _norm(query)
        for p in snap.parts.values():
            if q in (_norm(p["code"]), _norm(p["name"])):
                return p["code"]
        hits = [p["code"] for p in snap.parts.values() if q and q in _norm(p["name"])]
        return hits[0] if len(hits) == 1 else None

    # ---- 질의 (MCP 도구 하나에 하나) ------------------------------------------------------------
    def overview(self) -> dict:
        snap = self.snapshot()
        per_part = defaultdict(lambda: {"usages": 0, "ios": 0})
        for u in snap.usages.values():
            per_part[u["part"]]["usages"] += 1
        for x in snap.ios:
            per_part[snap.usages[x["owner"]]["part"]]["ios"] += 1
        return {"run": snap.run, "dataset": snap.dataset, "tools": len(snap.tools), "usages": len(snap.usages), "ios": len(snap.ios),
                "parts": sorted(({"code": p["code"], "name": p["name"], **per_part[p["code"]]} for p in snap.parts.values()
                                 if per_part[p["code"]]["usages"]), key=lambda p: p["code"])}

    def find_tool(self, query: str) -> list[dict]:
        snap = self.snapshot()
        out = []
        for t in self.resolve_tools(query):
            us = [u for u in snap.usages.values() if u["tool"] == t]
            out.append({"tool": snap.tools[t]["name"], "alt": snap.tools[t]["alt"], "vendor": snap.tools[t]["vendor"],
                        "usages": len(us), "parts": sorted({u["part"] for u in us})})
        return out

    def tool_info(self, tool: str) -> dict:
        snap = self.snapshot()
        ts = self.resolve_tools(tool)
        if len(ts) != 1:
            return {"matches": [snap.tools[t]["name"] for t in ts]}
        t = ts[0]
        uses = []
        for key, u in sorted(snap.usages.items(), key=lambda kv: (kv[1]["part"], kv[1]["sw_id"])):
            if u["tool"] != t:
                continue
            p = u["props"]
            row = {"part": u["part"], "tool_id": u["sw_id"], "reported_name": u["name"], "auto": u["auto"],
                   "ios_in": sum(1 for x in snap.ios if x["owner"] == key and x["dir"] == "입력"),
                   "ios_out": sum(1 for x in snap.ios if x["owner"] == key and x["dir"] == "출력")}
            for k in ("version", "purpose_class", "purpose_detail", "phase", "task_summary", "frequency", "user_count", "operation_mode",
                      "batch_capable", "automation_if", "automation_detail", "headless", "automation_wish", "pain_points", "priority_opinion",
                      "essential_tool", "runtime_env"):
                if p.get(k):
                    row[k] = self.redact(p[k]) if k in FREE_TEXT else p[k]
            uses.append(row)
        v = snap.tools[t]
        return {"tool": v["name"], "alt": v["alt"], "vendor": v["vendor"], "kind": v["kind"], "usages": uses}

    def part_tools(self, part: str) -> dict:
        snap = self.snapshot()
        code = self.resolve_part(part)
        if code is None:
            return {"error": f"파트 '{part}' 를 찾지 못함", "parts": sorted(p["code"] for p in snap.parts.values())}
        rows = []
        for key, u in sorted(snap.usages.items(), key=lambda kv: kv[1]["sw_id"]):
            if u["part"] != code:
                continue
            mine = [x for x in snap.ios if x["owner"] == key]
            rows.append({"tool_id": u["sw_id"], "tool": snap.tools[u["tool"]]["name"], "purpose": u["props"].get("purpose_class", ""),
                         "operation_mode": u["props"].get("operation_mode", ""), "automation_if": u["props"].get("automation_if", ""),
                         "auto": u["auto"], "ios_in": sum(x["dir"] == "입력" for x in mine), "ios_out": sum(x["dir"] == "출력" for x in mine),
                         "manual": sum(x["kind"] == "수기" for x in mine)})
        return {"part": code, "name": next(p["name"] for p in snap.parts.values() if p["code"] == code), "usages": rows}

    def tool_io(self, tool: str, part: str | None = None) -> dict:
        snap = self.snapshot()
        ts = self.resolve_tools(tool)
        if len(ts) != 1:
            return {"matches": [snap.tools[t]["name"] for t in ts]}
        code = self.resolve_part(part) if part else None
        rows = []
        for x in snap.ios:
            u = snap.usages[x["owner"]]
            if u["tool"] != ts[0] or (code and u["part"] != code):
                continue
            rows.append({"part": u["part"], "tool_id": u["sw_id"], "dir": x["dir"], "data": x["name"], "category": x["cat"], "ext": x["exts"],
                         "transfer": x["tm"], "partner": self._partner_text(snap, x), "note": self.redact(x["note"])})
        rows.sort(key=lambda r: (r["part"], r["tool_id"], r["dir"], r["data"]))
        return {"tool": snap.tools[ts[0]]["name"], "ios": rows}

    def tool_partners(self, tool: str) -> dict:
        """신고된 연결 상대 — 이 툴의 입출력이 상대를 적은 것(자기 신고) + 다른 툴의 입출력이 이 툴을 적은 것(상대 언급)."""
        snap = self.snapshot()
        ts = self.resolve_tools(tool)
        if len(ts) != 1:
            return {"matches": [snap.tools[t]["name"] for t in ts]}
        t = ts[0]
        agg: dict[tuple, dict] = {}
        for x in snap.ios:
            owner = snap.usages[x["owner"]]
            hits = []
            if owner["tool"] == t:
                hits = [(p, "자기 신고", "받음" if x["dir"] == "입력" else "보냄" if x["dir"] == "출력" else "?") for p in x["partners"] if p != t]
            elif t in x["partners"]:
                hits = [(owner["tool"], "상대 언급", "보냄" if x["dir"] == "입력" else "받음" if x["dir"] == "출력" else "?")]
            for k, how, flow in hits:
                e = agg.setdefault((k, flow), {"partner": snap.tools[k]["name"], "flow": flow, "how": set(), "parts": set(), "data": [], "manual": 0})
                e["how"].add(how)
                e["parts"].add(owner["part"])
                e["data"].append(f"{x['name']} [{x['exts'] or '?'}] · {x['tm']}")
                e["manual"] += x["kind"] == "수기"
        rows = [{**e, "how": sorted(e["how"]), "parts": sorted(e["parts"])} for e in agg.values()]
        rows.sort(key=lambda e: (-e["manual"], e["partner"], e["flow"]))
        return {"tool": snap.tools[t]["name"], "partners": rows}

    def manual_handoffs(self, part: str | None = None) -> dict:
        """사람 손으로 옮기는 구간의 원자료 — 전달 방법이 수기 값이거나 비고에 수기 신호. M4 의 착수 등급·순위 계산 전 단계."""
        snap = self.snapshot()
        code = self.resolve_part(part) if part else None
        rows = []
        for x in snap.ios:
            u = snap.usages[x["owner"]]
            if not x["kind"] or (code and u["part"] != code):
                continue
            rows.append({"kind": x["kind"], "part": u["part"], "tool_id": u["sw_id"], "tool": snap.tools[u["tool"]]["name"], "dir": x["dir"],
                         "data": x["name"], "ext": x["exts"], "transfer": x["tm"], "partner": self._partner_text(snap, x),
                         "frequency": u["props"].get("frequency", ""), "auto": u["auto"], "note": self.redact(x["note"])})
        rows.sort(key=lambda r: (r["kind"] != "수기", r["part"], r["tool_id"], r["data"]))
        return {"part": code, "handoffs": rows}

    def hub_candidates(self) -> list[dict]:
        """툴 기준 에이전트 후보 (잠정) — 3D 뷰어 '툴 기준 후보' 와 같은 정의·정렬 (docs/02 7.5 결정: 툴사용 단위, 연결 상대 수 1순위)."""
        snap = self.snapshot()
        agg: dict[tuple, dict] = {}
        for x in snap.ios:
            d = {"입력": "in", "출력": "out"}.get(x["dir"])
            for pt in x["partners"] if d else []:
                e = agg.setdefault((x["owner"], pt, d), {"n": 0, "kind": "auto"})
                e["n"] += 1
                if x["kind"] == "수기" or (x["kind"] == "비고" and e["kind"] == "auto"):
                    e["kind"] = "manual" if x["kind"] == "수기" else "note"
        parts_of_tool: dict[str, set] = defaultdict(set)
        for u in snap.usages.values():
            parts_of_tool[u["tool"]].add(u["part"])
        rank = []
        for key, u in snap.usages.items():
            declared = {pt for (uu, pt, d) in agg if uu == key}
            mentioned = {snap.usages[v]["tool"] for (v, pt, d) in agg if pt == u["tool"] and v != key}
            partners = (declared | mentioned) - {u["tool"]}
            manual = sum(e["n"] for (uu, pt, d), e in agg.items() if e["kind"] == "manual" and (uu == key or (pt == u["tool"] and uu != key)))
            rank.append({"tool": snap.tools[u["tool"]]["name"], "part": u["part"], "tool_id": u["sw_id"], "partners": len(partners),
                         "declared": len(declared - {u["tool"]}), "mentioned": len(mentioned - {u["tool"]}), "manual": manual,
                         "auto": u["auto"], "parts": len(parts_of_tool[u["tool"]]), "_name": u["name"]})
        rank.sort(key=lambda r: (-r["partners"], -r["manual"], not r["auto"], -r["parts"], r["_name"]))
        for r in rank:
            del r["_name"]
        return rank

    def hub_candidates_by_tool(self) -> list[dict]:
        """툴로 묶은 순위 — 3D 뷰어 순위표(v10~ '1 Excel / 1-1 FS / 1-2 ACT')와 같다: 툴 순서 = 그 툴의 툴사용 중 가장 앞선 순위.
        LLM 이 툴사용 행을 받아 스스로 툴 순위를 다시 매기면 '많이 쓰는 툴' 순으로 바뀌어 버린다 (Leo 2026-10-09) — 집계는 여기서 끝낸다."""
        groups: dict[str, dict] = {}
        for r in self.hub_candidates():
            g = groups.get(r["tool"])
            if g is None:
                g = groups[r["tool"]] = {"rank": len(groups) + 1, "tool": r["tool"], "partners": r["partners"], "manual": r["manual"],
                                         "auto": r["auto"], "parts": r["parts"], "detail": []}
            g["detail"].append(f"{g['rank']}-{len(g['detail']) + 1} {r['part']} (연결 {r['partners']}·수기 {r['manual']})")
        return list(groups.values())
