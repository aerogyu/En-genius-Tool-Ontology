"""적재한 온톨로지 3D 보기 — 골든 계산이 아니라 **적재 결과 그래프**를 읽는다 (Leo 2026-09-30 "내가 구축한 온톨로지를 보여주는 건 아니잖아").

    python scripts/graph_view3d.py [--run output/<실행ID>] [--open]     (기본: survey.ttl 이 있는 최신 실행)
    → output/<실행ID>/graph3d.html   ※ 적재한 데이터를 그대로 담는다 — 실데이터로 만들면 사내에만 둔다 (반출 금지)

그래프에서 SPARQL(표준 1.1, rdflib)로 읽는 것:
  배치: 파트(eg:Field) 묶음을 큰 원 둘레에, 그 툴사용(eg:ToolUsage)은 묶음 원판에, 툴(eg:Tool)은 살짝 위 — 공용일수록 가운데
  선   = 사용(툴사용 → 툴, eg:usage_tool) · 신고된 주고받음(입출력 행의 eg:io_owner ↔ eg:partner_tools, 방향·전달 방법 그대로)
확장자·데이터명을 맞춰 계산하는 연결(Feed)은 M4 도출(derive) 뒤 derived.ttl 에서 더한다 — 아직 없다.
자동화 가능 색·수기 판정 값은 config/rules.yaml (docs/02 7장). 외부 JS·CDN 없음 — canvas 원근 투영 (preview_map3d 와 같은 조작).
M4 에서 보고서 지도로 옮긴다.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import webbrowser
from collections import Counter, defaultdict
from pathlib import Path

import yaml
from rdflib import Graph

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from engenius_onto.config import SCHEMA_FILE, load_yaml, namespaces  # noqa: E402

VIEW_VERSION = "v10"  # 판 번호. v10 2026-10-01: 층 간격·두께·높낮이, 툴로 묶은 순위표 · v9 파트 이름은 약칭만 · v8 실데이터 실행 우선·제목에 데이터 종류 · v7 선은 전달 방식별 색 복원 · v6 점 색 최소(회색·흰색) · v5 담백하게·넓게·툴 기준 후보 · v4 꾸밈 · v3 2층 배치 · v2: 데이터 수에 맞춘 간격 · v1: 고정 간격
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
HIDDEN = {"source_row"}  # 패널에 안 보이는 속성
FIXED = {"label": "이름", "prefLabel": "대표 이름", "altLabel": "다른 이름", "status": "상태", "vendor": "제조사",
         "kind": "구분", "usage_tool": "툴", "usage_field": "분야"}


def latest_run(root: Path) -> Path | None:
    """최근 실행 — 실데이터 실행이 있으면 그것을 먼저 (적재 명령과 같은 규칙)."""
    from engenius_onto.survey_load import latest_run as pick

    return pick(root)


DATASET_LABEL = {"real": "실데이터", "synthetic": "합성 데이터", "custom": "지정 폴더"}


def fib_sphere(n: int, radius: float, phase: float = 0.0) -> list[tuple[float, float, float]]:
    """피보나치 구 — n 점을 구 표면에 고르게."""
    golden = math.pi * (3 - math.sqrt(5))
    pts = []
    for i in range(n):
        y = 1 - (2 * (i + 0.5) / n) if n > 1 else 0.0
        r = math.sqrt(max(0.0, 1 - y * y))
        th = golden * i + phase
        pts.append((radius * r * math.cos(th), radius * y, radius * r * math.sin(th)))
    return pts


def slot_labels() -> dict[str, str]:
    """슬롯 → 양식 헤더(한국어, '*' 뺌). 스키마 annotations.form_header 에서 — 없으면 슬롯 이름 그대로."""
    sch = yaml.safe_load(SCHEMA_FILE.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    specs = [(sch.get("slots") or {})] + [c.get(k) or {} for c in sch["classes"].values() for k in ("attributes", "slot_usage")]
    for block in specs:
        for name, spec in block.items():
            hdr = ((spec or {}).get("annotations") or {}).get("form_header")
            if hdr:
                out.setdefault(name, str(hdr).replace("*", "").strip())
    return {**out, **FIXED}


def part_code(label: str) -> str:
    """지도에는 파트 약칭만 (Leo 2026-10-01 "글자가 너무 많다") — 라벨 '정식 이름 (약칭)' 에서 괄호 안, 없으면 라벨 그대로."""
    m = re.match(r"^.*\(([^()]+)\)\s*$", label)
    return m.group(1).strip() if m else label


def local(iri: str) -> str:
    return iri.rsplit("/", 1)[-1].rsplit("#", 1)[-1]


def build(run: Path) -> tuple[dict, Path]:
    g = Graph()
    g.parse(run / "survey.ttl", format="turtle")
    ns = namespaces()
    pfx = f"PREFIX eg: <{ns['eg']}>\nPREFIX rdfs: <{RDFS}>\n"
    rules = load_yaml("rules.yaml")
    consume, produce = set(rules["direction"]["consume"]), set(rules["direction"]["produce"])
    manual_values = set(rules["manual_transfer_values"])
    note_keywords = list(rules["manual_note_keywords"])
    auto_modes, non_auto_if = set(rules["automatable"]["operation_modes"]), set(rules["automatable"]["non_automation_if"])
    labels = slot_labels()

    # ---- 툴사용 · 툴 · 분야
    usages: dict[str, dict] = {}
    for r in g.query(pfx + """
        SELECT ?u ?name ?sw ?fl ?t ?tl ?op ?aif WHERE {
          ?u a eg:ToolUsage ; eg:reported_tool_name ?name ; eg:source_key ?sw ; eg:usage_field ?f ; eg:usage_tool ?t .
          ?f rdfs:label ?fl . ?t rdfs:label ?tl .
          OPTIONAL { ?u eg:operation_mode ?op } OPTIONAL { ?u eg:automation_if ?aif }
        }"""):
        op, aif = (str(r.op) if r.op else ""), (str(r.aif) if r.aif else "")
        usages[str(r.u)] = {"id": local(str(r.u)), "type": "u", "name": str(r.name), "sw_id": str(r.sw),
                            "field": part_code(str(r.fl)), "field_name": str(r.fl),
                            "tool": str(r.t), "tool_name": str(r.tl),
                            "auto": op in auto_modes or (bool(aif) and aif not in non_auto_if)}
    tools: dict[str, dict] = {}
    for r in g.query(pfx + "SELECT ?t ?tl WHERE { ?t a eg:Tool ; rdfs:label ?tl }"):
        tools[str(r.t)] = {"id": local(str(r.t)), "type": "t", "name": str(r.tl), "field": ""}

    props: dict[str, list] = defaultdict(list)
    for r in g.query(pfx + "SELECT ?s ?p ?o WHERE { VALUES ?c { eg:ToolUsage eg:Tool } ?s a ?c ; ?p ?o . FILTER(isLiteral(?o)) }"):
        key = local(str(r.p))
        if key not in HIDDEN:
            props[str(r.s)].append([labels.get(key, key), str(r.o)])

    # ---- 입출력 행 (신고된 주고받음)
    ios: dict[str, list] = defaultdict(list)          # 툴사용 → 입출력 행 (패널용)
    agg: dict[tuple, dict] = {}                        # (툴사용, 상대 툴, 방향) → 선
    io_count, no_partner = 0, 0
    seen_io = set()
    for r in g.query(pfx + """
        SELECT ?io ?u ?dir ?name ?tm ?pt ?praw ?note (GROUP_CONCAT(DISTINCT STR(?ext); separator=", ") AS ?exts) WHERE {
          ?io a eg:IOSpec ; eg:io_owner ?u ; eg:direction ?dir ; eg:data_name ?name ; eg:transfer_method ?tm .
          OPTIONAL { ?io eg:partner_tools ?pt } OPTIONAL { ?io eg:partner_raw ?praw }
          OPTIONAL { ?io eg:note ?note } OPTIONAL { ?io eg:extensions ?ext }
        } GROUP BY ?io ?u ?dir ?name ?tm ?pt ?praw ?note"""):
        u = str(r.u)
        if u not in usages:
            continue
        d = "in" if str(r.dir) in consume else "out" if str(r.dir) in produce else "?"
        tm, note = str(r.tm), (str(r.note) if r.note else "")
        kind = "manual" if tm in manual_values else "note" if any(k in note for k in note_keywords) else "auto"
        pt = str(r.pt) if r.pt else None
        io_id = str(r.io)
        if io_id not in seen_io:
            seen_io.add(io_id)
            io_count += 1
            no_partner += pt is None
        ios[u].append({"dir": d, "name": str(r.name), "ext": str(r.exts or ""), "tm": tm, "kind": kind,
                       "partner": tools[pt]["name"] if pt in tools else (str(r.praw) if r.praw else "")})
        if pt in tools and d in ("in", "out"):
            e = agg.setdefault((u, pt, d), {"n": 0, "kind": "auto", "items": []})
            e["n"] += 1
            if kind == "manual" or (kind == "note" and e["kind"] == "auto"):
                e["kind"] = kind
            e["items"].append(f"{r.name} [{r.exts or '?'}] · {tm}")

    # ---- 3D 배치: 2층 (Leo 2026-09-30 "파트 레이어와 툴 레이어가 영리하게 분리되면").
    #   아래층 y=0 : 파트 묶음을 큰 원 위에 두르고, 묶음마다 그 파트의 툴사용을 해바라기 원판으로 펼친다.
    #   위층 y=+H  : 툴. 한 파트만 쓰는 툴은 그 파트 바로 위, 여러 파트가 쓰는 툴은 쓰는 곳들의 무게중심을 가운데로 당긴 자리.
    #   간격은 데이터 수로 정한다 — 묶음 반지름은 툴사용 수의 제곱근, 큰 원 둘레는 묶음 지름 합보다 넉넉하게.
    by_field: dict[str, list] = defaultdict(list)
    for key, u in usages.items():
        by_field[u["field"]].append(key)
    fields = sorted(by_field)
    spacing = 46.0                                                    # 툴사용 사이 대략 간격 (v5: 더 넓게)
    radius = {f: spacing * (0.8 + math.sqrt(len(by_field[f]))) for f in fields}
    rmax = max(radius.values(), default=40.0)
    ring_r = max(3.4 * rmax, 1.7 * sum(2 * r for r in radius.values()) / (2 * math.pi))
    height = 0.55 * ring_r                                            # 툴 층 높이 (v10: 더 띄움)
    thick = 0.06 * ring_r                                             # 층 두께 — 한 층 안에서도 점마다 높낮이
    golden = math.pi * (3 - math.sqrt(5))
    centers, clusters, nodes, index = {}, [], [], {}
    ang = 0.0
    total = sum(2 * r for r in radius.values()) or 1.0
    for f in fields:
        half = math.pi * (2 * radius[f]) / total                       # 묶음 크기에 비례한 원호
        ang += half
        cx, cz = ring_r * math.cos(ang), ring_r * math.sin(ang)
        ang += half
        centers[f] = (cx, 0.0, cz)
        members = sorted(by_field[f], key=lambda k: usages[k]["sw_id"])
        rc = radius[f]
        clusters.append({"field": f, "x": cx, "y": 0.0, "z": cz, "r": rc})
        n = len(members)
        for j, key in enumerate(members):                              # 해바라기 원판 — 고르게 펼쳐진다
            rr, th = rc * math.sqrt((j + 0.5) / n), golden * j
            index[key] = len(nodes)
            wob = math.sin(j * 2.399963 + len(fields) * 0.7) * thick          # 결정적인 높낮이 (실행마다 같다)
            nodes.append({**usages[key], "x": cx + rr * math.cos(th), "y": wob, "z": cz + rr * math.sin(th)})
    users_of: dict[str, list] = defaultdict(list)
    for key, u in usages.items():
        users_of[u["tool"]].append(index[key])
    per_part: dict[str, int] = defaultdict(int)                        # 같은 파트 위 툴끼리 겹치지 않게 원판 순번
    for key, t in sorted(tools.items(), key=lambda kv: kv[1]["name"]):
        idx = users_of.get(key, [])
        parts_using = sorted({nodes[i]["field"] for i in idx})
        if len(parts_using) == 1:
            f = parts_using[0]
            cx, _, cz = centers[f]
            j = per_part[f]
            per_part[f] += 1
            m = max(1, sum(1 for tk in tools if {nodes[i]["field"] for i in users_of.get(tk, [])} == {f}))
            rr, th = 0.8 * radius[f] * math.sqrt((j + 0.5) / m), golden * j + 0.5
            x, z = cx + rr * math.cos(th), cz + rr * math.sin(th)
        elif idx:
            x = sum(nodes[i]["x"] for i in idx) / len(idx) * 0.45
            z = sum(nodes[i]["z"] for i in idx) / len(idx) * 0.45
        else:
            x = z = 0.0
        index[key] = len(nodes)
        # 툴 층 안 높이: 여러 파트가 쓸수록 조금 더 위 + 작은 흔들림 (공용 툴이 눈에 띄게)
        lift = thick * 2.2 * min(1.0, (len(parts_using) - 1) / 5) if parts_using else 0.0
        y = height + lift + math.sin(len(nodes) * 2.399963) * thick * 0.6
        nodes.append({**t, "x": x, "y": y, "z": z, "uses": len(idx), "parts": len(parts_using),
                      "home": parts_using[0] if len(parts_using) == 1 else None})
    big = ring_r

    edges = [{"s": index[u], "t": index[usages[u]["tool"]], "kind": "use", "n": 1, "items": []} for u in usages]
    for (u, pt, d), e in agg.items():
        s, t = (index[u], index[pt]) if d == "out" else (index[pt], index[u])
        edges.append({"s": s, "t": t, "kind": e["kind"], "n": e["n"], "items": e["items"][:8]})
    for key, n in index.items():
        nodes[n]["props"] = props.get(key, [])
        nodes[n]["ios"] = ios.get(key, [])
        nodes[n]["noio"] = nodes[n]["type"] == "u" and not ios.get(key)

    parts_of_tool: dict[str, set] = defaultdict(set)
    for key, u in usages.items():
        parts_of_tool[u["tool"]].add(u["field"])
    rank = []
    for key, u in usages.items():
        declared = {pt for (uu, pt, d) in agg if uu == key}
        mentioned = {usages[v]["tool"] for (v, pt, d) in agg if pt == u["tool"] and v != key}
        partners = (declared | mentioned) - {u["tool"]}
        manual = sum(e["n"] for (uu, pt, d), e in agg.items() if e["kind"] == "manual" and (uu == key or (pt == u["tool"] and uu != key)))
        rank.append({"i": index[key], "t": index[u["tool"]], "partners": len(partners), "declared": len(declared - {u["tool"]}),
                     "mentioned": len(mentioned - {u["tool"]}), "manual": manual, "auto": u["auto"],
                     "parts": len(parts_of_tool[u["tool"]])})
    rank.sort(key=lambda r: (-r["partners"], -r["manual"], not r["auto"], -r["parts"], nodes[r["i"]]["name"]))

    kinds = Counter(e["kind"] for e in edges)
    data = {"nodes": nodes, "edges": edges, "clusters": clusters, "run": run.name, "rank": rank, "extent": ring_r + rmax * 1.2, "height": height,
            "counts": {"fields": len(fields), "tools": len(tools), "usages": len(usages), "ios": io_count,
                       "no_partner": no_partner, "pairs": len(agg), "manual": kinds["manual"], "note": kinds["note"],
                       "auto": kinds["auto"], "noio": sum(1 for n in nodes if n["noio"])}}
    out = run / "graph3d.html"
    from engenius_onto.survey_load import run_dataset

    ds = DATASET_LABEL.get(run_dataset(run), "데이터 종류 모름")
    out.write_text(PAGE.replace("__VER__", VIEW_VERSION).replace("__DS__", ds).replace("__DATA__", json.dumps(data, ensure_ascii=False)),
                   encoding="utf-8", newline="\n")
    return data, out


PAGE = r"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>내 온톨로지 3D __VER__</title>
<style>
 :root{--bg:#0f1720;--line:#2a3a4a;--fg:#e6edf3;--muted:#9fb0c0;--manual:#ff9a2e;--note:#c9925a;--auto:#8a98a6;--use:#4f8fd6;--ok:#e6edf3;--no:#9aa7b4;--tool:#e6edf3;--iso:#9aa7b4}
 html,body{margin:0;height:100%;background:var(--bg);color:var(--fg);font-family:"Malgun Gothic","Apple SD Gothic Neo","Noto Sans KR",sans-serif;font-size:13px;overflow:hidden}
 #top{position:absolute;left:0;right:0;top:0;display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;padding:8px 12px;background:rgba(22,33,44,.92);border-bottom:1px solid var(--line);z-index:5}
 #top h1{font-size:15px;margin:0 10px 0 0;font-weight:700}
 #top label{display:inline-flex;align-items:center;gap:4px;color:var(--muted);cursor:pointer}
 #top select,#top button{background:#0f1720;color:var(--fg);border:1px solid var(--line);border-radius:5px;padding:2px 7px;font:inherit}
 #top button{cursor:pointer}
 .sw{display:inline-block;width:22px;height:3px;vertical-align:middle;margin-right:3px}
 canvas{display:block;width:100vw;height:100vh;cursor:grab} canvas.drag{cursor:grabbing}
 #tip{position:absolute;pointer-events:none;background:rgba(22,33,44,.96);border:1px solid var(--line);border-radius:6px;padding:7px 9px;max-width:360px;white-space:pre-line;display:none;z-index:6;line-height:1.35}
 #side{position:absolute;right:0;top:56px;bottom:0;width:min(400px,50vw);box-sizing:border-box;background:rgba(22,33,44,.96);border-left:1px solid var(--line);padding:12px 14px 14px;overflow:auto;display:none;z-index:4}
 #side h2{font-size:14px;margin:8px 0 4px;padding-right:56px} #side h3{font-size:13px;margin:10px 0 4px}
 #side .m{color:var(--muted);font-size:12px} #side ul{padding-left:16px;margin:4px 0} #side li{margin:3px 0}
 #side .close{position:absolute;right:10px;top:10px;cursor:pointer;color:var(--muted)}
 #side.wide{width:min(760px,80vw)}
 #side table.rank{table-layout:auto} #side table.rank td,#side table.rank th{white-space:nowrap} #side table.rank td.tool{white-space:normal;font-weight:700;vertical-align:top}
 #side table.rank td.num{width:2.5em;color:var(--muted);text-align:right} #side table.rank td.pri{width:2em;text-align:right;font-weight:700;vertical-align:top}
 #side td[data-tool]{cursor:pointer} #side td[data-tool]:hover{text-decoration:underline dotted}
 #side tr[data-r]{cursor:pointer} #side tr[data-r]:hover{background:rgba(255,255,255,.05)} #side tr.on{background:rgba(255,154,46,.18)}
 #side th{color:var(--muted);font-weight:400;text-align:left;border-bottom:1px solid var(--line);padding:3px 4px} #side td.n{text-align:right}
 #side table{border-collapse:collapse;width:100%;font-size:12px} #side td{border-bottom:1px solid var(--line);padding:3px 4px;vertical-align:top}
 #side td:first-child{color:var(--muted);white-space:nowrap;width:34%}
 #side [data-n]{cursor:pointer;text-decoration:underline dotted}
 #help{position:absolute;left:12px;bottom:10px;max-width:54vw;color:var(--muted);font-size:12px;background:rgba(15,23,32,.75);padding:4px 8px;border-radius:5px;line-height:1.4}
 #counts{position:absolute;right:12px;bottom:10px;max-width:40vw;text-align:right;color:var(--muted);font-size:12px;background:rgba(15,23,32,.75);padding:4px 8px;border-radius:5px;line-height:1.4}
 b.m{color:var(--manual)} b.n{color:var(--note)} b.i{color:var(--iso)} .km{color:var(--manual);font-weight:700} .kn{color:var(--note)} .ka{color:var(--muted)}
</style></head><body>
<div id="top">
 <h1>내 온톨로지 3D <span style="color:var(--muted);font-weight:400;font-size:12px">__VER__ · <b style="color:var(--fg)">__DS__</b> · 적재 결과 그대로 (survey.ttl)</span></h1>
 <label><input type="checkbox" id="fManual" checked><span class="sw" style="background:var(--manual)"></span>수기 전달</label>
 <label><input type="checkbox" id="fNote" checked><span class="sw" style="height:0;border-top:3px dashed var(--note)"></span>비고 신호</label>
 <label><input type="checkbox" id="fAuto" checked><span class="sw" style="background:var(--auto)"></span>그 밖의 전달</label>
 <label><input type="checkbox" id="fUse" checked><span class="sw" style="height:0;border-top:2px dotted var(--use)"></span>사용 (툴사용→툴)</label>
 <label>이름 <select id="fLabel"><option value="near">가까운 것</option><option value="all">전부</option><option value="sel">선택·연결만</option><option value="none">없음</option></select></label>
 <label><input type="checkbox" id="fCluster" checked>분야 묶음</label>
 <label><input type="checkbox" id="fSpin" checked>자동 회전</label>
 <button id="rankBtn">툴 기준 후보</button>
 <button id="reset">시점 초기화</button>
</div>
<canvas id="c"></canvas>
<div id="tip"></div>
<div id="side"><span class="close" id="closeSide">✕ 닫기</span><div id="sideBody"></div></div>
<div id="help">왼쪽 드래그 회전 · 휠 줌 · 휠(가운데)/오른쪽 드래그 이동 · 더블클릭 초기화 · 노드 클릭 = 그래프에 적힌 속성·입출력 ·
 회색 점 = 파트별 툴사용 · 흰 점 = 툴(여러 파트가 쓸수록 가운데, 클수록 많이 쓰임) · 선 = 주황 수기 전달 · 갈색 점선 비고 신호 · 회색 그 밖의 전달 · 파란 점선 사용 관계 · 선 = 조사표에 '연계 툴'로 신고된 주고받음 (계산된 연결은 M4)</div>
<div id="counts"></div>
<script>
const DATA = __DATA__;
const N = DATA.nodes, E = DATA.edges, C = DATA.clusters;
const cv = document.getElementById('c'), ctx = cv.getContext('2d');
const tip = document.getElementById('tip'), side = document.getElementById('side'), sideBody = document.getElementById('sideBody');
const ui = id => document.getElementById(id);
// 회전은 3x3 행렬 누적(트랙볼) — 어느 방향으로도 끝없이 돈다
function rotX(a) { const c = Math.cos(a), s = Math.sin(a); return [1, 0, 0, 0, c, -s, 0, s, c]; }
function rotY(a) { const c = Math.cos(a), s = Math.sin(a); return [c, 0, s, 0, 1, 0, -s, 0, c]; }
function mul(A, B) { const M = new Array(9); for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) M[i * 3 + j] = A[i * 3] * B[j] + A[i * 3 + 1] * B[3 + j] + A[i * 3 + 2] * B[6 + j]; return M; }
function initR() { return mul(rotX(0.62), rotY(0.3)); }   // 비스듬히 내려다보기 — 아래 파트 층과 위 툴 층이 갈라져 보이게
const S = { R: initR(), dist: 950, dist0: 950, sref: 700 / 950, fov: 700, panX: 0, panY: 0, hover: -1, sel: -1, rankSel: -1, panel: null, spin: true, dirty: true };
// 처음 거리 = 전체(DATA.extent)가 화면 짧은 변의 약 45% 에 들어오게. 크기·글자는 처음 배율(sref) 대비로 — 데이터가 많아도 같은 느낌 (2026-09-30)
function fitDist() { return S.fov * DATA.extent / (0.40 * Math.max(300, Math.min(innerWidth, (innerHeight - 60) / 0.62))) + DATA.extent * 0.15; }   // 비스듬히 보면 원이 세로로 약 0.62 로 눌린다
const rs = p => p.s / S.sref;   // 처음 배율 대비 크기 (반복문 변수 k 와 겹치지 않게)
function orbit(dx, dy) { S.R = mul(mul(rotX(dy * 0.006), rotY(dx * 0.006)), S.R); }
// 점은 회색·흰색 두 가지, 선은 전달 방식별 색 (Leo 2026-09-30: 선 종류는 방식을 나눈 것이라 다양해도 된다)
const COL = { manual: '#ff9a2e', note: '#c9925a', auto: '#8a98a6', use: '#4f8fd6', usage: '#9aa7b4', tool: '#e6edf3', fg: '#e6edf3', muted: '#9fb0c0' };
const adj = N.map(() => new Set()), nb = N.map(() => new Set());
E.forEach((e, k) => { adj[e.s].add(k); adj[e.t].add(k); nb[e.s].add(e.t); nb[e.t].add(e.s); });

function resize() {
  const dpr = window.devicePixelRatio || 1;
  cv.width = Math.floor(innerWidth * dpr); cv.height = Math.floor(innerHeight * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); S.dirty = true;
  side.style.top = ui('top').offsetHeight + 'px';
}
addEventListener('resize', resize); resize();
// 처음 거리 맞추기 — 창 크기가 바뀌면 사용자가 확대·축소하기 전까지 다시 맞춘다 (열리는 순간 창 폭이 0 에 가까운 경우 대비)
function refit() { if (S.userZoom) return; S.dist0 = S.dist = fitDist(); S.sref = S.fov / S.dist0; S.panY = -innerHeight * 0.04; S.dirty = true; }
refit(); addEventListener('resize', refit); requestAnimationFrame(refit);

let P = [], PC = [];
function rot(x, y, z) { const R = S.R; return [R[0] * x + R[1] * y + R[2] * z, R[3] * x + R[4] * y + R[5] * z, R[6] * x + R[7] * y + R[8] * z]; }
function proj(x, y, z) {
  const [rx, ry, rz] = rot(x, y - (DATA.height || 0) / 2, z), s = S.fov / Math.max(S.dist0 * 0.05, S.dist - rz);   // 두 층 사이를 중심으로 돈다
  return { x: innerWidth / 2 + S.panX + rx * s, y: innerHeight / 2 + S.panY - ry * s, s, d: rz };
}
function project() { P = N.map(n => proj(n.x, n.y, n.z)); PC = C.map(c => Object.assign(proj(c.x, c.y, c.z), { r: c.r })); }

function edgeVisible(e) {
  return !((e.kind === 'manual' && !ui('fManual').checked) || (e.kind === 'note' && !ui('fNote').checked) ||
           (e.kind === 'auto' && !ui('fAuto').checked) || (e.kind === 'use' && !ui('fUse').checked));
}
function focusSet() { const f = S.sel >= 0 ? S.sel : S.rankSel >= 0 ? S.rankSel : S.hover; return f >= 0 ? new Set([f]) : new Set(); }
function isNeighbor(i, F) { if (F.size === 0 || F.has(i)) return true; for (const f of F) if (nb[f].has(i)) return true; return false; }
function depthAlpha(d) { const t = Math.max(0, Math.min(1, (d + 440) / 880)); return 0.35 + 0.65 * t; }
function nodeR(i) { const b = 6.5 * Math.min(1.8, rs(P[i])); return Math.max(3, N[i].type === 't' ? b * (0.75 + 0.22 * Math.sqrt(N[i].uses || 1)) : b); }

// ---- 그리기 (v5 — Leo 2026-09-30: 꾸밈은 걷고 v2 처럼 담백하게. 파트 이름은 흰 회색 한 색, 노드는 점)
function draw() {
  project();
  ctx.clearRect(0, 0, innerWidth, innerHeight);
  const F = focusSet(), has = F.size > 0, labelMode = ui('fLabel').value;
  if (ui('fCluster').checked) {
    [...PC.keys()].sort((a, b) => PC[a].d - PC[b].d).forEach(i => {
      const c = PC[i], r = c.r * c.s * 1.3, g = ctx.createRadialGradient(c.x, c.y, r * 0.2, c.x, c.y, Math.max(1, r));
      g.addColorStop(0, 'rgba(120,150,190,0.16)'); g.addColorStop(1, 'rgba(120,150,190,0.01)');
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(c.x, c.y, r, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = 'rgba(214,222,230,' + (0.5 * depthAlpha(c.d) + 0.35) + ')';
      ctx.font = '700 ' + Math.max(11, Math.min(20, 14 * rs(c))) + 'px sans-serif';
      ctx.textAlign = 'center'; ctx.fillText(C[i].field, c.x, c.y - r - 4);
    });
  }
  const order = { use: 0, auto: 1, note: 2, manual: 3 };
  const es = E.map((e, k) => k).filter(k => edgeVisible(E[k]))  // 선이 많으면 평소 선을 흐리게 (선택한 것만 또렷하게)
    .sort((a, b) => (order[E[a].kind] - order[E[b].kind]) || ((P[E[a].s].d + P[E[a].t].d) - (P[E[b].s].d + P[E[b].t].d)));
  const crowd = Math.max(0.15, Math.min(1, 160 / Math.max(1, es.length)));
  // '가까운 것' 이름표: 앞쪽(가까운) 노드 중 최대 28개만 — 많으면 글자가 겹친다
  const near = new Set([...N.keys()].filter(i => rs(P[i]) > 1.05).sort((a, b) => P[b].s - P[a].s).slice(0, 28));
  const lift = (DATA.height || 0) * 0.3;
  for (const k of es) {
    const e = E[k], a = P[e.s], b = P[e.t], touches = has && (F.has(e.s) || F.has(e.t));
    let alpha = depthAlpha((a.d + b.d) / 2) * (e.kind === 'use' ? 0.3 : e.kind === 'auto' ? 0.5 : 0.9) * crowd;
    if (has && !touches) alpha *= 0.1;
    if (touches) alpha = 1;
    const w = ((e.kind === 'manual' ? 2.6 : e.kind === 'note' ? 2 : e.kind === 'use' ? 1 : 1.3) + Math.min(2, (e.n - 1) * 0.4))
      * Math.max(0.6, Math.min(1.6, (rs(a) + rs(b)) / 2)) * (touches ? 1.4 : 1);
    const A = N[e.s], B = N[e.t], m = proj((A.x + B.x) / 2, (A.y + B.y) / 2 + lift, (A.z + B.z) / 2);   // 위로 살짝 부푼 곡선
    ctx.strokeStyle = COL[e.kind]; ctx.globalAlpha = alpha; ctx.lineWidth = w;
    ctx.setLineDash(e.kind === 'note' ? [7, 5] : e.kind === 'use' ? [2, 4] : []);
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.quadraticCurveTo(m.x, m.y, b.x, b.y); ctx.stroke();
    if (e.kind !== 'use') { // 화살촉 = 데이터를 받는 쪽
      const tx = b.x - m.x, ty = b.y - m.y, tl = Math.hypot(tx, ty) || 1, ux = tx / tl, uy = ty / tl, rb = nodeR(e.t) + 2, hs = 5 + w * 1.2;
      const px = b.x - ux * rb, py = b.y - uy * rb;
      ctx.setLineDash([]); ctx.fillStyle = COL[e.kind]; ctx.beginPath();
      ctx.moveTo(px, py); ctx.lineTo(px - ux * hs + uy * hs * 0.55, py - uy * hs - ux * hs * 0.55);
      ctx.lineTo(px - ux * hs - uy * hs * 0.55, py - uy * hs + ux * hs * 0.55); ctx.closePath(); ctx.fill();
    }
  }
  ctx.globalAlpha = 1; ctx.setLineDash([]);
  for (const i of [...N.keys()].sort((a, b) => P[a].d - P[b].d)) {
    const n = N[i], p = P[i], r = nodeR(i), dim = has && !isNeighbor(i, F), on = F.has(i);
    ctx.globalAlpha = dim ? 0.18 : depthAlpha(p.d);
    ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
    ctx.fillStyle = n.type === 't' ? COL.tool : COL.usage; ctx.fill();
    ctx.lineWidth = 1.2; ctx.strokeStyle = on ? '#ffffff' : '#0f1720'; ctx.stroke();
    if (on) { ctx.lineWidth = 2; ctx.strokeStyle = '#ffffff'; ctx.beginPath(); ctx.arc(p.x, p.y, r + 5, 0, Math.PI * 2); ctx.stroke(); }
    const show = labelMode === 'all' || (labelMode === 'near' && (near.has(i) || on || (has && isNeighbor(i, F)))) || (labelMode === 'sel' && has && isNeighbor(i, F));
    if (show && !dim) {
      ctx.globalAlpha = Math.min(1, depthAlpha(p.d) + 0.15); ctx.textAlign = 'left';
      ctx.font = (on ? '700 ' : '') + Math.max(10, 11.5 * Math.min(1.4, rs(p))) + 'px sans-serif';
      ctx.fillStyle = n.type === 't' ? COL.tool : COL.fg; ctx.fillText(n.name, p.x + r + 4, p.y + 4);
      if (n.type === 'u') {
        ctx.fillStyle = COL.muted; ctx.font = Math.max(9, 9.5 * Math.min(1.4, rs(p))) + 'px sans-serif';
        ctx.fillText(n.sw_id, p.x + r + 6 + ctx.measureText(n.name).width * 1.15, p.y + 4);
      }
    }
  }
  ctx.globalAlpha = 1;
  const c = DATA.counts;
  ui('counts').innerHTML = `실행 ${DATA.run} · 분야 ${c.fields} · 툴 ${c.tools} · 툴사용 ${c.usages} · 입출력 ${c.ios} (상대 툴 없음·미해석 ${c.no_partner})<br>` +
    `신고된 주고받음 ${c.pairs}쌍: <b class="m">수기 ${c.manual}</b> · <b class="n">비고 ${c.note}</b> · 그 밖 ${c.auto} · <b class="i">입출력 없는 툴사용 ${c.noio}</b>` +
    (S.sel >= 0 ? ` · 선택: ${N[S.sel].name}` : '');
}

let drag = null, moved = 0;
cv.addEventListener('contextmenu', ev => ev.preventDefault());
cv.addEventListener('mousedown', ev => { drag = { x: ev.clientX, y: ev.clientY, btn: ev.button, shift: ev.shiftKey }; moved = 0; cv.classList.add('drag'); S.spin = false; ui('fSpin').checked = false; });
function hit(x, y) { let best = -1, bd = 12 * 12; for (let i = 0; i < N.length; i++) { const d = (P[i].x - x) ** 2 + (P[i].y - y) ** 2; if (d < bd) { bd = d; best = i; } } return best; }
addEventListener('mousemove', ev => {
  if (drag) {
    const dx = ev.clientX - drag.x, dy = ev.clientY - drag.y; drag.x = ev.clientX; drag.y = ev.clientY; moved += Math.abs(dx) + Math.abs(dy);
    if (drag.btn === 0 && !drag.shift) orbit(dx, dy); else { S.panX += dx; S.panY += dy; }
    S.dirty = true; tip.style.display = 'none'; return;
  }
  const h = hit(ev.clientX, ev.clientY);
  if (h !== S.hover) { S.hover = h; S.dirty = true; }
  if (h >= 0) {
    const n = N[h];
    tip.innerText = n.type === 't' ? `[툴] ${n.name}\n쓰는 툴사용 ${n.uses}곳 · 선 ${adj[h].size}개\n클릭하면 속성·쓰는 곳` :
      `[툴사용] ${n.name}  (${n.sw_id}, ${n.field})\n→ 툴: ${n.tool_name}\n입출력 ${n.ios.length}행 · 자동화 ${n.auto ? '가능' : '불가/모름'}` + (n.noio ? '\n입출력 없음' : '') + '\n클릭하면 속성·입출력';
    tip.style.display = 'block'; tip.style.left = Math.min(innerWidth - 370, ev.clientX + 14) + 'px'; tip.style.top = (ev.clientY + 14) + 'px';
  } else tip.style.display = 'none';
});
addEventListener('mouseup', ev => {
  if (drag && moved < 4 && drag.btn === 0) { const h = hit(ev.clientX, ev.clientY); select(h >= 0 && h !== S.sel ? h : -1); S.hover = h; }
  drag = null; cv.classList.remove('drag');
});
cv.addEventListener('wheel', ev => { ev.preventDefault(); S.userZoom = true; S.dist = Math.max(S.dist0 * 0.12, Math.min(S.dist0 * 4, S.dist * (ev.deltaY > 0 ? 1.1 : 0.9))); S.dirty = true; }, { passive: false });
cv.addEventListener('dblclick', resetView);
ui('reset').addEventListener('click', resetView);
function resetView() { S.userZoom = false; refit(); S.R = initR(); S.dist = S.dist0; S.panX = 0; S.panY = -innerHeight * 0.04; S.panel = null; S.rankSel = -1; select(-1); }
['fManual', 'fNote', 'fAuto', 'fUse', 'fLabel', 'fCluster'].forEach(id => ui(id).addEventListener('change', () => { S.dirty = true; }));
ui('fSpin').addEventListener('change', ev => { S.spin = ev.target.checked; });
ui('closeSide').addEventListener('click', () => { S.panel = null; S.rankSel = -1; select(-1); });
ui('rankBtn').addEventListener('click', () => {
  S.panel = S.panel === 'rank' && S.sel < 0 ? null : 'rank'; S.sel = -1; S.rankSel = -1; S.spin = false; ui('fSpin').checked = false;
  if (S.panel) renderRank(); else { side.style.display = 'none'; side.classList.remove('wide'); }
  S.dirty = true;
});
function renderRank() {
  // 툴로 묶는다: 툴 순서 = 그 툴의 툴사용 중 가장 앞선 순위 (Leo 2026-10-01 — 1 Excel / 1-1 FS / 1-2 ACT …)
  const groups = [], byTool = new Map();
  DATA.rank.forEach(r => { if (!byTool.has(r.t)) { byTool.set(r.t, []); groups.push(r.t); } byTool.get(r.t).push(r); });
  let num = 0;
  const rows = groups.map((tool, g) => byTool.get(tool).map((r, k, arr) => {
    num++;
    const n = N[r.i], head = k === 0
      ? `<td class="pri" rowspan="${arr.length}">${g + 1}</td><td class="tool" rowspan="${arr.length}" data-tool="${tool}">${esc(N[tool].name)}</td>` : '';
    return `<tr data-r="${r.i}" class="${r.i === S.rankSel ? 'on' : ''}"><td class="num">${num}</td>${head}
      <td>${g + 1}-${k + 1} ${esc(n.field)}</td><td class="n"><b>${r.partners}</b></td><td class="n">${r.manual}</td>
      <td>${r.auto ? '가능' : '<span class="m">불가·모름</span>'}</td><td class="n">${r.parts}</td></tr>`;
  }).join('')).join('');
  sideBody.innerHTML = `<h2>툴 기준 에이전트 후보 <span class="m">잠정 · 조사표에 신고된 연결 기준</span></h2>
   <p class="m">툴로 묶은 순위 — 툴 순서는 그 툴의 툴사용(파트) 중 가장 앞선 것 기준. 정렬: <b>연결 상대 수</b> → 수기 전달 → 자동화 가능 →
   같은 툴 쓰는 파트 수. 툴 이름을 누르면 그 툴을 쓰는 곳 전체, 파트 행을 누르면 그 툴사용만 강조. 맨 왼쪽 번호의 끝 = 조사된 툴사용 수.
   M4 에서 확장자·데이터명으로 계산한 연결로 바뀐다.</p>
   <table class="rank"><tr><th>번호</th><th>순위</th><th>툴</th><th>세부 순위 (파트)</th><th>연결 상대</th><th>수기 전달</th><th>자동화</th><th>같은 툴 쓰는 파트</th></tr>${rows}</table>`;
  side.classList.add('wide'); side.style.display = 'block';
}
sideBody.addEventListener('click', ev => {
  const tc = ev.target.closest('[data-tool]');
  if (tc) { const i = +tc.dataset.tool; S.rankSel = S.rankSel === i ? -1 : i; renderRank();
    if (S.rankSel >= 0) { project(); const q = P[i]; S.panX += (innerWidth - side.offsetWidth) / 2 - q.x; S.panY += innerHeight / 2 - q.y; }
    S.dirty = true; return; }
  const r = ev.target.closest('[data-r]');
  if (r) {
    const i = +r.dataset.r; S.rankSel = S.rankSel === i ? -1 : i; renderRank();
    if (S.rankSel >= 0) { project(); const q = P[i]; S.panX += (innerWidth - side.offsetWidth) / 2 - q.x; S.panY += innerHeight / 2 - q.y; }
    S.dirty = true; return;
  }
  const a = ev.target.closest('[data-n]'); if (a) select(+a.dataset.n);
});
let touches = null;
cv.addEventListener('touchstart', ev => { touches = [...ev.touches].map(t => ({ x: t.clientX, y: t.clientY })); S.spin = false; ui('fSpin').checked = false; }, { passive: true });
cv.addEventListener('touchmove', ev => {
  const t = [...ev.touches].map(t => ({ x: t.clientX, y: t.clientY }));
  if (touches && t.length === 1 && touches.length === 1) orbit(t[0].x - touches[0].x, t[0].y - touches[0].y);
  else if (touches && t.length === 2 && touches.length === 2) { S.userZoom = true; const d0 = Math.hypot(touches[0].x - touches[1].x, touches[0].y - touches[1].y), d1 = Math.hypot(t[0].x - t[1].x, t[0].y - t[1].y); S.dist = Math.max(S.dist0 * 0.12, Math.min(S.dist0 * 4, S.dist * d0 / Math.max(1, d1))); }
  touches = t; S.dirty = true; ev.preventDefault();
}, { passive: false });

const esc = s => String(s).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
const KIND = { manual: ['km', '수기'], note: ['kn', '비고'], auto: ['ka', ''] };
function link(i) { return `<span data-n="${i}">${esc(N[i].type === 't' ? N[i].name : N[i].name + ' (' + N[i].field + ')')}</span>`; }
function toolLink(n) { const t = N.findIndex(x => x.type === 't' && x.id === n.tool.split('/').pop()); return t >= 0 ? link(t) : esc(n.tool_name); }
function select(i) {
  S.sel = i; S.dirty = true;
  side.classList.remove('wide'); S.rankSel = -1;
  if (i < 0) { if (S.panel === 'rank') renderRank(); else side.style.display = 'none'; return; }
  const n = N[i];
  const rows = n.props.map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join('');
  let body = '';
  if (n.type === 'u') {
    const io = d => n.ios.filter(x => x.dir === d).map(x => `<li>${KIND[x.kind][1] ? `<span class="${KIND[x.kind][0]}">${KIND[x.kind][1]}</span> ` : ''}${esc(x.name)} <span class="m">[${esc(x.ext || '?')}] · ${esc(x.tm)}${x.partner ? ' · 상대 ' + esc(x.partner) : ''}</span></li>`).join('') || '<li class="m">없음</li>';
    body = `<h2>${esc(n.name)} <span class="m">${esc(n.sw_id)} · ${esc(n.field_name || n.field)} · 툴사용</span></h2>
      <div class="m">툴: ${toolLink(n)} · 자동화 ${n.auto ? '가능' : '불가/모름'}</div>
      <h3>내놓는 것 (출력)</h3><ul>${io('out')}</ul><h3>받는 것 (입력)</h3><ul>${io('in')}</ul>
      <h3>그래프에 적힌 속성</h3><table>${rows}</table>`;
  } else {
    const users = [...adj[i]].map(k => E[k]).filter(e => e.kind === 'use').map(e => `<li>${link(e.s)}</li>`).join('') || '<li class="m">없음</li>';
    const ex = [...adj[i]].map(k => E[k]).filter(e => e.kind !== 'use').map(e => {
      const other = e.s === i ? e.t : e.s, dir = e.s === i ? '→' : '←';
      return `<li>${KIND[e.kind][1] ? `<span class="${KIND[e.kind][0]}">${KIND[e.kind][1]}</span> ` : ''}${dir} ${link(other)} <span class="m">(${e.n}건)</span><div class="m">${e.items.map(esc).join('<br>')}</div></li>`;
    }).join('') || '<li class="m">없음</li>';
    body = `<h2>${esc(n.name)} <span class="m">툴</span></h2>
      <h3>이 툴을 쓰는 곳 (${n.uses})</h3><ul>${users}</ul>
      <h3>이 툴과 주고받는다고 신고한 곳</h3><ul>${ex}</ul>
      <h3>그래프에 적힌 속성</h3><table>${rows}</table>`;
  }
  sideBody.innerHTML = body; side.style.display = 'block';
}

function loop() { if (S.spin) { S.R = mul(rotY(0.0025), S.R); S.dirty = true; } if (S.dirty) { draw(); S.dirty = false; } requestAnimationFrame(loop); }
requestAnimationFrame(loop);
</script></body></html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="적재한 온톨로지(survey.ttl)를 3D HTML 한 장으로")
    ap.add_argument("--run", help="실행 폴더 (기본: survey.ttl 이 있는 최신 output/<실행ID>)")
    ap.add_argument("--open", action="store_true", help="만든 뒤 기본 브라우저로 연다")
    args = ap.parse_args()
    run = Path(args.run) if args.run else latest_run(REPO / "output")
    if not run or not (run / "survey.ttl").is_file():
        print("[NG] survey.ttl 이 있는 실행 폴더가 없다 — 먼저 scripts\\load.bat 로 적재한다")
        return 1
    data, out = build(run)
    c = data["counts"]
    print(f"[OK] {out} ({data['run']}) — 분야 {c['fields']} · 툴 {c['tools']} · 툴사용 {c['usages']} · 입출력 {c['ios']} · 신고된 주고받음 {c['pairs']}쌍 (수기 {c['manual']})")
    print("     적재한 데이터가 그대로 들어 있다 — 실데이터로 만들었으면 밖으로 가져가지 않는다.")
    if args.open:
        webbrowser.open(out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
