"""툴 연결 지도 — 합성 데이터 미리보기 (M4 전 시안).
M3 적재 결과와 같은 합성 명세를 골든 참조 계산(tests/golden/oracle.py)으로 돌려 Feed(연결)·착수 순위·고립을 얻고,
외부 JS·CDN 없이 파이썬이 SVG 를 직접 그려 HTML 한 장으로 만든다 (폐쇄망에서 그대로 열림 — docs/08 5장 5).
"""
from __future__ import annotations

import html
import math
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# 지도 판 번호 — 반입 브랜치에 올릴 때 파일명에 붙인다 (덮어쓰지 않는다, Leo 2026-09-29). 그림을 바꾸면 올린다. v1 2026-09-28 회의용
MAP_VERSION = "v1"
sys.path.insert(0, str(REPO / "tests" / "golden"))
sys.path.insert(0, str(REPO / "src"))
import oracle  # noqa: E402
from engenius_onto import synth  # noqa: E402

R = oracle.compute(synth.load_spec(), REPO)
usages = R["usages"]
feeds = R["feeds"]
isolated = set(R["no_io"]) | set(R["unlinked"])

# ---------------------------------------------------------------- 배치: 분야 = 큰 타원 위의 묶음, 툴사용 = 묶음 둘레의 원
W, H = 1180, 900
CX, CY, RX, RY = 590, 440, 420, 320
fields = sorted({u.field for u in usages})
by_field = defaultdict(list)
for u in usages:
    by_field[u.field].append(u)
pos: dict[str, tuple[float, float]] = {}
centers: dict[str, tuple[float, float]] = {}
NODE_R = 9
for k, f in enumerate(fields):
    a = -math.pi / 2 + 2 * math.pi * k / len(fields)
    cx, cy = CX + RX * math.cos(a), CY + RY * math.sin(a)
    centers[f] = (cx, cy)
    members = sorted(by_field[f], key=lambda u: u.sw_id)
    rc = 34 + 11 * len(members)
    for j, u in enumerate(members):
        b = a + 2 * math.pi * j / len(members)  # 묶음 바깥쪽부터 시계 방향
        pos[u.key] = (cx + rc * math.cos(b), cy + rc * math.sin(b))

# ---------------------------------------------------------------- 연결 집계: (공급 툴사용, 소비 툴사용) 당 선 하나
GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "제외": 3, None: 4}
edges: dict[tuple[str, str], dict] = {}
for fd in feeds:
    key = (fd.o.owner.key, fd.i.owner.key)
    e = edges.setdefault(key, {"n": 0, "manual": False, "note": False, "grade": None, "names": []})
    e["n"] += 1
    if fd.manual and fd.manual_basis == "전달방법":
        e["manual"] = True
    if fd.manual_basis == "비고" and not fd.manual:
        e["note"] = True
    if GRADE_ORDER[fd.grade] < GRADE_ORDER[e["grade"]]:
        e["grade"] = fd.grade
    e["names"].append(f"{fd.o.name} → {fd.i.name} [{'/'.join(fd.matched) or '?'}]")

def kind_of(e: dict) -> str:
    return "manual" if e["manual"] else ("note" if e["note"] else "auto")

STYLE = {
    "auto":   {"stroke": "#9aa4ad", "width": 1.3, "dash": "", "marker": "arrow-auto", "label": "자동 연결(파일·DB·직접 연동)"},
    "note":   {"stroke": "#8b5a2b", "width": 2.2, "dash": "6 4", "marker": "arrow-note", "label": "비고 신호(수작업 언급)"},
    "manual": {"stroke": "#e07b00", "width": 3.2, "dash": "", "marker": "arrow-manual", "label": "수기 전달(메일·수기) — 착수 후보"},
}

def esc(s: object) -> str:
    return html.escape(str(s), quote=True)

def edge_path(a: tuple[float, float], b: tuple[float, float]) -> str:
    """양방향 선이 겹치지 않게 진행 방향 오른쪽으로 살짝 휜 2차 곡선. 양 끝은 노드 반지름만큼 줄인다."""
    (x1, y1), (x2, y2) = a, b
    dx, dy = x2 - x1, y2 - y1
    d = math.hypot(dx, dy) or 1.0
    ux, uy = dx / d, dy / d
    nx, ny = -uy, ux
    bend = min(28.0, d * 0.12)
    mx, my = (x1 + x2) / 2 + nx * bend, (y1 + y2) / 2 + ny * bend
    # 곡선 끝점을 노드 가장자리로: 제어점 방향 기준으로 줄임
    def trim(px, py, qx, qy, r):
        vx, vy = qx - px, qy - py
        l = math.hypot(vx, vy) or 1.0
        return px + vx / l * r, py + vy / l * r
    sx, sy = trim(x1, y1, mx, my, NODE_R + 2)
    ex, ey = trim(x2, y2, mx, my, NODE_R + 6)
    return f"M{sx:.1f},{sy:.1f} Q{mx:.1f},{my:.1f} {ex:.1f},{ey:.1f}"

# ---------------------------------------------------------------- SVG
svg: list[str] = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px;font-family:Malgun Gothic,Apple SD Gothic Neo,Noto Sans KR,sans-serif">')
svg.append("<defs>")
for k, st in STYLE.items():
    svg.append(f'<marker id="{st["marker"]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
               f'<path d="M0,0 L10,5 L0,10 z" fill="{st["stroke"]}"/></marker>')
svg.append("</defs>")
svg.append(f'<rect width="{W}" height="{H}" fill="#fbfbfa"/>')
# 분야 묶음 배경
for f, (cx, cy) in centers.items():
    rc = 34 + 11 * len(by_field[f])
    svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rc + 26}" fill="#eef2f6" stroke="#cfd6de"/>')
    svg.append(f'<text x="{cx:.1f}" y="{cy + 4:.1f}" text-anchor="middle" font-size="13" font-weight="700" fill="#2b3a4a">{esc(f)}</text>')
# 선: 자동 → 비고 → 수기 순으로 그려 수기가 위에 오게
for kind in ("auto", "note", "manual"):
    st = STYLE[kind]
    for (a, b), e in edges.items():
        if kind_of(e) != kind:
            continue
        w = st["width"] + min(2.0, (e["n"] - 1) * 0.5)
        dash = f' stroke-dasharray="{st["dash"]}"' if st["dash"] else ""
        tip = f"{a} → {b}: {e['n']}건 ({st['label'].split('(')[0].strip()}" + (f", 착수 등급 {e['grade']}" if e["grade"] else "") + ")\n" + "\n".join(e["names"][:6]) + ("\n…" if e["n"] > 6 else "")
        opacity = 0.45 if kind == "auto" else 0.95  # 자동 연결은 흐리게 — 수기·비고가 도드라지게
        svg.append(f'<path d="{edge_path(pos[a], pos[b])}" fill="none" stroke="{st["stroke"]}" stroke-width="{w:.1f}"{dash} marker-end="url(#{st["marker"]})" opacity="{opacity}"><title>{esc(tip)}</title></path>')
# 노드
for u in usages:
    x, y = pos[u.key]
    fill = "#3a9d5d" if u.automatable else "#b8bec5"
    stroke, sw = ("#d23c3c", 3.2) if u.key in isolated or f"{u.field}/{u.name}" in isolated else ("#33404d", 1.2)
    dash = ' stroke-dasharray="3 2"' if u.airgap == "불가" else ""
    tip = (f"{u.name}  ({u.sw_id}, {u.field})\n조작 방식: {u.op} · 자동화 IF: {u.auto_if} · 폐쇄망: {u.airgap}\n"
           f"자동화 {'가능' if u.automatable else '불가/모름'}" + ("\n고립: 어떤 연결에도 없음" if u.key in isolated or f'{u.field}/{u.name}' in isolated else ""))
    svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{NODE_R}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dash}><title>{esc(tip)}</title></circle>')
    cx, cy = centers[u.field]
    side = 1 if x >= cx else -1
    anchor = "start" if side > 0 else "end"
    name = u.name if len(u.name) <= 14 else u.name[:13] + "…"
    svg.append(f'<text x="{x + side * (NODE_R + 4):.1f}" y="{y + 4:.1f}" text-anchor="{anchor}" font-size="10.5" fill="#1f2933">{esc(name)}'
               f'<tspan font-size="8.5" fill="#6b7785"> {esc(u.sw_id)}</tspan></text>')
svg.append("</svg>")

# ---------------------------------------------------------------- 착수 순위 표 (골든 15행)
rows = []
for rank, row in enumerate(R["ranked"], 1):
    sup, con, kind, grade, ios = row
    data = ", ".join(sorted({k.split("/")[-1] for k in ios}))
    rows.append(f"<tr><td>{rank}</td><td class='g{esc(grade)}'>{esc(grade)}</td><td>{esc(kind)}</td>"
                f"<td>{esc(sup.field)} / {esc(sup.name)}</td><td>{esc(con.field)} / {esc(con.name)}</td><td>{esc(data)}</td></tr>")

n_manual = sum(1 for f in feeds if f.manual and f.manual_basis == "전달방법")
n_note = sum(1 for f in feeds if f.manual_basis == "비고" and not f.manual)
n_auto = len(feeds) - n_manual - n_note
legend = "".join(
    f'<span class="lg"><svg width="46" height="12"><line x1="2" y1="6" x2="44" y2="6" stroke="{st["stroke"]}" stroke-width="{st["width"]}"'
    f'{" stroke-dasharray=" + chr(34) + st["dash"] + chr(34) if st["dash"] else ""}/></svg>{st["label"]}</span>' for st in STYLE.values())
legend += ('<span class="lg"><svg width="16" height="14"><circle cx="8" cy="7" r="6" fill="#3a9d5d" stroke="#33404d"/></svg>자동화 가능(CLI·API 등)</span>'
           '<span class="lg"><svg width="16" height="14"><circle cx="8" cy="7" r="6" fill="#b8bec5" stroke="#33404d"/></svg>자동화 불가·모름(GUI 전용 등)</span>'
           '<span class="lg"><svg width="16" height="14"><circle cx="8" cy="7" r="6" fill="#b8bec5" stroke="#d23c3c" stroke-width="3"/></svg>고립(연결 없음)</span>'
           '<span class="lg"><svg width="16" height="14"><circle cx="8" cy="7" r="6" fill="#3a9d5d" stroke="#33404d" stroke-dasharray="3 2"/></svg>폐쇄망 구동 불가</span>')

page = f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>툴 연결 지도 — 합성 데이터 미리보기</title>
<style>
 body{{margin:0;padding:18px 22px;background:#fff;color:#1f2933;font-family:"Malgun Gothic","Apple SD Gothic Neo","Noto Sans KR",sans-serif;font-size:14px}}
 h1{{font-size:19px;margin:0 0 4px}} .sub{{color:#5b6773;margin:0 0 12px}}
 .legend{{display:flex;flex-wrap:wrap;gap:6px 18px;margin:8px 0 10px;font-size:12.5px}} .lg{{display:inline-flex;align-items:center;gap:6px}}
 .counts{{display:flex;gap:14px;flex-wrap:wrap;margin:6px 0 10px;font-size:13px}} .counts b{{font-size:16px}}
 .card{{background:#f6f8fa;border:1px solid #dfe5ec;border-radius:8px;padding:8px 12px}}
 table{{border-collapse:collapse;font-size:12.5px;margin-top:8px}} th,td{{border:1px solid #d9e0e7;padding:4px 8px;text-align:left;vertical-align:top}}
 th{{background:#eef2f6}} td.gA{{background:#ffe3c2;font-weight:700}} td.gB{{background:#fff3d6}} td.gC{{background:#f2f4f6}} td.g제외{{color:#8a949e}}
 .note{{font-size:12px;color:#5b6773;margin-top:10px}}
</style></head><body>
<h1>툴 연결 지도 — 합성 데이터 미리보기</h1>
<p class="sub">M3 적재와 같은 합성 조사 8개 분야를 골든 참조 계산으로 돌린 결과. 선 위에 마우스를 올리면 어떤 데이터가 오가는지, 노드에 올리면 툴 정보가 뜬다.
M4 에서는 이 그림을 적재된 그래프(Fuseki)에서 직접 만든다 — 지금은 M4 전 시안이다.</p>
<div class="counts card"><span>분야 <b>{len(fields)}</b></span><span>툴사용 <b>{len(usages)}</b></span><span>연결(Feed) <b>{len(feeds)}</b></span>
<span>수기 <b style="color:#e07b00">{n_manual}</b></span><span>비고 신호 <b style="color:#8b5a2b">{n_note}</b></span><span>자동 <b>{n_auto}</b></span>
<span>고립 <b style="color:#d23c3c">{len(isolated)}</b></span><span>착수 순위 <b>{len(R["ranked"])}</b>행</span></div>
<div class="legend">{legend}</div>
{''.join(svg)}
<h2 style="font-size:16px;margin:16px 0 4px">수기 구간 착수 순위 (골든 15행 — 보고서 시트 2 의 원형)</h2>
<table><tr><th>#</th><th>등급</th><th>종류</th><th>공급 (분야 / 툴)</th><th>소비 (분야 / 툴)</th><th>데이터</th></tr>{''.join(rows)}</table>
<p class="note">등급: A = 양쪽 다 자동화 가능(에이전트로 바로 이을 수 있음) · B = 한쪽만 · C = 양쪽 다 불가 · 제외 = 대상 아님(범용 확장자 등). 종류 '비고' 는 전달 방법은 자동인데 비고에 수작업이 적힌 구간.
합성 데이터라 툴 이름은 공개 상용 툴이거나 '가상-' 이름이다.</p>
</body></html>
"""
out = REPO / "output" / "preview_map.html"
out.write_text(page, encoding="utf-8", newline="\n")
print(f"wrote {out} ({out.stat().st_size:,} bytes): fields={len(fields)} usages={len(usages)} feeds={len(feeds)} "
      f"edges(pairs)={len(edges)} manual={n_manual} note={n_note} auto={n_auto} isolated={sorted(isolated)}")
