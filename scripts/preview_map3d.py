"""툴 연결 지도 3D — 합성 데이터 미리보기 (M4 전 시안, Leo 요청 2026-09-28 "3차원 공간을 돌아다니게").
골든 참조 계산(tests/golden/oracle.py)으로 Feed·착수 순위·고립을 얻어 JSON 으로 박고, 외부 JS·CDN·WebGL 라이브러리 없이
브라우저의 <canvas> 에 직접 원근 투영으로 그린다 (폐쇄망에서 그대로 열림, 반입 추가 0).
조작: 왼쪽 드래그 회전 · 휠 줌 · 휠(가운데) 또는 오른쪽 드래그 이동 · 더블클릭 초기화 · 노드 클릭 선택.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests" / "golden"))
sys.path.insert(0, str(REPO / "src"))
import oracle  # noqa: E402
from engenius_onto import synth  # noqa: E402

R = oracle.compute(synth.load_spec(), REPO)
usages = R["usages"]
feeds = R["feeds"]
isolated = set(R["no_io"]) | set(R["unlinked"])


def fib_sphere(n: int, radius: float, phase: float = 0.0) -> list[tuple[float, float, float]]:
    """피보나치 구 — n 점을 구 표면에 고르게."""
    pts = []
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        y = 1 - (2 * (i + 0.5) / n) if n > 1 else 0.0
        r = math.sqrt(max(0.0, 1 - y * y))
        th = golden * i + phase
        pts.append((radius * r * math.cos(th), radius * y, radius * r * math.sin(th)))
    return pts


# ---------------------------------------------------------------- 3D 배치: 분야 묶음 = 큰 구 위, 툴사용 = 묶음 중심 둘레의 작은 구
fields = sorted({u.field for u in usages})
by_field = defaultdict(list)
for u in usages:
    by_field[u.field].append(u)
centers = dict(zip(fields, fib_sphere(len(fields), 250.0, phase=0.7)))
nodes: list[dict] = []
index: dict[str, int] = {}
clusters: list[dict] = []
for f in fields:
    cx, cy, cz = centers[f]
    members = sorted(by_field[f], key=lambda u: u.sw_id)
    rc = 38.0 + 9.0 * len(members)
    clusters.append({"field": f, "x": cx, "y": cy, "z": cz, "r": rc})
    for u, (dx, dy, dz) in zip(members, fib_sphere(len(members), rc, phase=1.3)):
        iso = u.key in isolated or f"{u.field}/{u.name}" in isolated
        index[u.key] = len(nodes)
        nodes.append({
            "id": u.key, "name": u.name, "sw_id": u.sw_id, "field": f,
            "x": cx + dx, "y": cy + dy, "z": cz + dz,
            "auto": bool(u.automatable), "airgap": u.airgap, "op": u.op, "auto_if": u.auto_if,
            "kind": u.kind, "freq": u.freq, "users": u.users, "isolated": iso,
        })

# ---------------------------------------------------------------- 연결 집계 (공급, 소비) 쌍
GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "제외": 3, None: 4}
agg: dict[tuple[str, str], dict] = {}
for fd in feeds:
    key = (fd.o.owner.key, fd.i.owner.key)
    e = agg.setdefault(key, {"n": 0, "manual": False, "note": False, "grade": None, "items": []})
    e["n"] += 1
    if fd.manual and fd.manual_basis == "전달방법":
        e["manual"] = True
    if fd.manual_basis == "비고" and not fd.manual:
        e["note"] = True
    if GRADE_ORDER[fd.grade] < GRADE_ORDER[e["grade"]]:
        e["grade"] = fd.grade
    e["items"].append(f"{fd.o.name} → {fd.i.name} [{'/'.join(fd.matched) or '?'}]")
edges = [{"s": index[a], "t": index[b], "n": e["n"], "kind": "manual" if e["manual"] else ("note" if e["note"] else "auto"),
          "grade": e["grade"], "items": e["items"][:8]} for (a, b), e in agg.items()]

ranked = [{"rank": i, "grade": row[3], "kind": row[2], "s": index[row[0].key], "t": index[row[1].key],
           "data": ", ".join(sorted({k.split("/")[-1] for k in row[4]}))} for i, row in enumerate(R["ranked"], 1)]

data = {"nodes": nodes, "edges": edges, "clusters": clusters, "ranked": ranked,
        "counts": {"fields": len(fields), "usages": len(usages), "feeds": len(feeds),
                   "manual": sum(1 for f in feeds if f.manual and f.manual_basis == "전달방법"),
                   "note": sum(1 for f in feeds if f.manual_basis == "비고" and not f.manual),
                   "isolated": len(isolated)}}
data["counts"]["auto"] = data["counts"]["feeds"] - data["counts"]["manual"] - data["counts"]["note"]

PAGE = r"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>툴 연결 지도 3D — 합성 데이터 미리보기</title>
<style>
 :root{--bg:#0f1720;--panel:#16212c;--line:#2a3a4a;--fg:#e6edf3;--muted:#9fb0c0;--manual:#ff9a2e;--note:#c9925a;--auto:#7f8c99;--ok:#3fbf73;--no:#aab3bc;--iso:#ff5a5a}
 html,body{margin:0;height:100%;background:var(--bg);color:var(--fg);font-family:"Malgun Gothic","Apple SD Gothic Neo","Noto Sans KR",sans-serif;font-size:13px;overflow:hidden}
 #top{position:absolute;left:0;right:0;top:0;display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;padding:8px 12px;background:rgba(22,33,44,.92);border-bottom:1px solid var(--line);z-index:5}
 #top h1{font-size:15px;margin:0 10px 0 0;font-weight:700}
 #top label{display:inline-flex;align-items:center;gap:4px;color:var(--muted);cursor:pointer}
 #top select,#top button{background:#0f1720;color:var(--fg);border:1px solid var(--line);border-radius:5px;padding:2px 7px;font:inherit}
 #top button{cursor:pointer}
 .sw{display:inline-block;width:22px;height:3px;vertical-align:middle;margin-right:3px}
 canvas{display:block;width:100vw;height:100vh;cursor:grab}
 canvas.drag{cursor:grabbing}
 #tip{position:absolute;pointer-events:none;background:rgba(22,33,44,.96);border:1px solid var(--line);border-radius:6px;padding:7px 9px;max-width:340px;white-space:pre-line;display:none;z-index:6;line-height:1.35}
 #side{position:absolute;right:0;top:0;bottom:0;width:min(340px,46vw);box-sizing:border-box;background:rgba(22,33,44,.95);border-left:1px solid var(--line);padding:56px 14px 14px;overflow:auto;display:none;z-index:4}
 #side h2{font-size:14px;margin:6px 0 4px} #side .m{color:var(--muted);font-size:12px} #side ul{padding-left:16px;margin:4px 0} #side li{margin:2px 0}
 #side .close{position:absolute;right:10px;top:52px;cursor:pointer;color:var(--muted)}
 #help{position:absolute;left:12px;bottom:10px;max-width:54vw;color:var(--muted);font-size:12px;background:rgba(15,23,32,.75);padding:4px 8px;border-radius:5px;line-height:1.4}
 #counts{position:absolute;right:12px;bottom:10px;max-width:38vw;text-align:right;color:var(--muted);font-size:12px;background:rgba(15,23,32,.75);padding:4px 8px;border-radius:5px;line-height:1.4}
 b.m{color:var(--manual)} b.n{color:var(--note)} b.i{color:var(--iso)}
 .gA{color:var(--manual);font-weight:700} .gB{color:#ffd28a} .gC{color:var(--muted)} .g제외{color:#6b7785}
</style></head><body>
<div id="top">
 <h1>툴 연결 지도 3D <span style="color:var(--muted);font-weight:400;font-size:12px">합성 데이터 · M4 전 시안</span></h1>
 <label><input type="checkbox" id="fManual" checked><span class="sw" style="background:var(--manual)"></span>수기 전달</label>
 <label><input type="checkbox" id="fNote" checked><span class="sw" style="background:var(--note);height:0;border-top:3px dashed var(--note)"></span>비고 신호</label>
 <label><input type="checkbox" id="fAuto" checked><span class="sw" style="background:var(--auto)"></span>자동 연결</label>
 <label>등급 <select id="fGrade"><option value="">전체</option><option value="A">A만</option><option value="AB">A·B</option></select></label>
 <label>이름 <select id="fLabel"><option value="near">가까운 것</option><option value="all">전부</option><option value="sel">선택·연결만</option><option value="none">없음</option></select></label>
 <label><input type="checkbox" id="fCluster" checked>분야 묶음</label>
 <label><input type="checkbox" id="fSpin" checked>자동 회전</label>
 <button id="reset">시점 초기화</button>
</div>
<canvas id="c"></canvas>
<div id="tip"></div>
<div id="side"><span class="close" id="closeSide">✕ 닫기</span><div id="sideBody"></div></div>
<div id="help">왼쪽 드래그 회전 · 휠 줌 · 휠(가운데)/오른쪽 드래그 이동 · 더블클릭 초기화 · 노드 클릭 선택 · 초록=자동화 가능 · 회색=불가/모름 · 빨간 테두리=고립</div>
<div id="counts"></div>
<script>
const DATA = __DATA__;
const N = DATA.nodes, E = DATA.edges, C = DATA.clusters;
const cv = document.getElementById('c'), ctx = cv.getContext('2d');
const tip = document.getElementById('tip'), side = document.getElementById('side'), sideBody = document.getElementById('sideBody');
const S = { yaw: 0.6, pitch: 0.35, dist: 900, fov: 700, panX: 0, panY: 0, hover: -1, sel: -1, spin: true, dirty: true };
const COL = { manual: '#ff9a2e', note: '#c9925a', auto: '#7f8c99', ok: '#3fbf73', no: '#aab3bc', iso: '#ff5a5a', fg: '#e6edf3', muted: '#9fb0c0' };
const ui = id => document.getElementById(id);
const adj = N.map(() => new Set());
E.forEach((e, k) => { adj[e.s].add(k); adj[e.t].add(k); });
const rankedByNode = N.map(() => []);
DATA.ranked.forEach(r => { rankedByNode[r.s].push(r); rankedByNode[r.t].push(r); });

function resize() {
  const dpr = window.devicePixelRatio || 1;
  cv.width = Math.floor(innerWidth * dpr); cv.height = Math.floor(innerHeight * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); S.dirty = true;
}
addEventListener('resize', resize); resize();

// ---- 투영: 회전(yaw: Y축, pitch: X축) → 카메라 거리 dist 원근
let P = [];   // 노드 투영 결과 {x,y,s,d}
let PC = [];  // 묶음 투영
function rot(x, y, z) {
  const cy = Math.cos(S.yaw), sy = Math.sin(S.yaw), cp = Math.cos(S.pitch), sp = Math.sin(S.pitch);
  let x1 = x * cy + z * sy, z1 = -x * sy + z * cy;
  let y1 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
  return [x1, y1, z2];
}
function proj(x, y, z) {
  const [rx, ry, rz] = rot(x, y, z);
  const depth = S.dist - rz;                    // 카메라는 +z 쪽에서 원점을 본다
  const s = S.fov / Math.max(80, depth);
  return { x: innerWidth / 2 + S.panX + rx * s, y: innerHeight / 2 + S.panY - ry * s, s, d: rz };
}
function project() {
  P = N.map(n => proj(n.x, n.y, n.z));
  PC = C.map(c => Object.assign(proj(c.x, c.y, c.z), { r: c.r }));
}

// ---- 필터
function edgeVisible(e) {
  if (e.kind === 'manual' && !ui('fManual').checked) return false;
  if (e.kind === 'note' && !ui('fNote').checked) return false;
  if (e.kind === 'auto' && !ui('fAuto').checked) return false;
  const g = ui('fGrade').value;
  if (g && e.kind !== 'auto') { if (g === 'A' && e.grade !== 'A') return false; if (g === 'AB' && e.grade !== 'A' && e.grade !== 'B') return false; }
  return true;
}
function focusNode() { return S.sel >= 0 ? S.sel : S.hover; }
function isNeighbor(i, f) { if (f < 0) return true; if (i === f) return true; for (const k of adj[f]) { const e = E[k]; if (e.s === i || e.t === i) return true; } return false; }

// ---- 그리기
function depthAlpha(d) { // 가까울수록 진하게
  const t = Math.max(0, Math.min(1, (d + 420) / 840));
  return 0.35 + 0.65 * t;
}
function draw() {
  project();
  ctx.clearRect(0, 0, innerWidth, innerHeight);
  const f = focusNode();
  const labelMode = ui('fLabel').value;
  // 묶음 (뒤에서 앞으로)
  if (ui('fCluster').checked) {
    [...PC.keys()].sort((a, b) => PC[a].d - PC[b].d).forEach(i => {
      const c = PC[i]; const r = c.r * c.s * 1.35;
      const g = ctx.createRadialGradient(c.x, c.y, r * 0.2, c.x, c.y, r);
      g.addColorStop(0, 'rgba(120,150,190,0.22)'); g.addColorStop(1, 'rgba(120,150,190,0.02)');
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(c.x, c.y, r, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = 'rgba(200,215,230,' + (0.55 * depthAlpha(c.d) + 0.2) + ')'; ctx.font = '700 ' + Math.max(11, 15 * c.s) + 'px sans-serif';
      ctx.textAlign = 'center'; ctx.fillText(C[i].field, c.x, c.y - r - 4);
    });
  }
  // 선: 뒤에서 앞으로, 자동 → 비고 → 수기 순 (수기가 위)
  const order = { auto: 0, note: 1, manual: 2 };
  const es = E.map((e, k) => k).filter(k => edgeVisible(E[k]))
    .sort((a, b) => (order[E[a].kind] - order[E[b].kind]) || ((P[E[a].s].d + P[E[a].t].d) - (P[E[b].s].d + P[E[b].t].d)));
  for (const k of es) {
    const e = E[k], a = P[e.s], b = P[e.t];
    const touches = f >= 0 && (e.s === f || e.t === f);
    let alpha = depthAlpha((a.d + b.d) / 2) * (e.kind === 'auto' ? 0.45 : 0.95);
    if (f >= 0 && !touches) alpha *= 0.12;
    if (touches) alpha = 1;
    const w = ((e.kind === 'manual' ? 3 : e.kind === 'note' ? 2 : 1.1) + Math.min(2, (e.n - 1) * 0.4)) * Math.max(0.6, Math.min(1.6, (a.s + b.s) / 2)) * (touches ? 1.4 : 1);
    ctx.strokeStyle = COL[e.kind]; ctx.globalAlpha = alpha; ctx.lineWidth = w;
    ctx.setLineDash(e.kind === 'note' ? [7, 5] : []);
    // 양방향 겹침 방지: 진행 방향 오른쪽으로 살짝 휨
    const dx = b.x - a.x, dy = b.y - a.y, L = Math.hypot(dx, dy) || 1, nx = -dy / L, ny = dx / L, bend = Math.min(22, L * 0.1);
    const mx = (a.x + b.x) / 2 + nx * bend, my = (a.y + b.y) / 2 + ny * bend;
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.quadraticCurveTo(mx, my, b.x, b.y); ctx.stroke();
    // 화살촉 (소비 쪽)
    const tx = b.x - mx, ty = b.y - my, tl = Math.hypot(tx, ty) || 1, ux = tx / tl, uy = ty / tl, rb = nodeR(e.t) + 2, hs = 5 + w * 1.2;
    const px = b.x - ux * rb, py = b.y - uy * rb;
    ctx.setLineDash([]); ctx.fillStyle = COL[e.kind]; ctx.beginPath();
    ctx.moveTo(px, py); ctx.lineTo(px - ux * hs - (-uy) * hs * 0.55, py - uy * hs - ux * hs * 0.55); ctx.lineTo(px - ux * hs + (-uy) * hs * 0.55, py - uy * hs + ux * hs * 0.55); ctx.closePath(); ctx.fill();
  }
  ctx.globalAlpha = 1; ctx.setLineDash([]);
  // 노드: 뒤에서 앞으로
  const ns = [...N.keys()].sort((a, b) => P[a].d - P[b].d);
  for (const i of ns) {
    const n = N[i], p = P[i], r = nodeR(i);
    const dim = f >= 0 && !isNeighbor(i, f);
    ctx.globalAlpha = dim ? 0.18 : depthAlpha(p.d);
    ctx.fillStyle = n.auto ? COL.ok : COL.no;
    ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, Math.PI * 2); ctx.fill();
    ctx.lineWidth = n.isolated ? 3 : 1.2; ctx.strokeStyle = n.isolated ? COL.iso : (i === f ? '#ffffff' : '#0f1720');
    ctx.setLineDash(n.airgap === '불가' ? [3, 2] : []); ctx.stroke(); ctx.setLineDash([]);
    if (i === f) { ctx.lineWidth = 2; ctx.strokeStyle = '#ffffff'; ctx.beginPath(); ctx.arc(p.x, p.y, r + 4, 0, Math.PI * 2); ctx.stroke(); }
    const showLabel = labelMode === 'all' || (labelMode === 'near' && (p.s > 0.78 || i === f || (f >= 0 && isNeighbor(i, f)))) || (labelMode === 'sel' && f >= 0 && isNeighbor(i, f));
    if (showLabel && !dim) {
      ctx.font = (i === f ? '700 ' : '') + Math.max(10, 11.5 * Math.min(1.4, p.s)) + 'px sans-serif';
      ctx.textAlign = 'left'; ctx.fillStyle = COL.fg; ctx.globalAlpha = Math.min(1, depthAlpha(p.d) + 0.15);
      ctx.fillText(n.name, p.x + r + 4, p.y + 4);
      ctx.fillStyle = COL.muted; ctx.font = Math.max(9, 9.5 * Math.min(1.4, p.s)) + 'px sans-serif';
      ctx.fillText(n.sw_id, p.x + r + 6 + ctx.measureText(n.name).width * 1.15, p.y + 4);
    }
  }
  ctx.globalAlpha = 1;
  const c = DATA.counts;
  ui('counts').innerHTML = `분야 ${c.fields} · 툴사용 ${c.usages} · 연결 ${c.feeds} (<b class="m">수기 ${c.manual}</b> · <b class="n">비고 ${c.note}</b> · 자동 ${c.auto}) · <b class="i">고립 ${c.isolated}</b>` + (S.sel >= 0 ? ` · 선택: ${N[S.sel].name}` : '');
}
function nodeR(i) { return Math.max(3, 7 * Math.min(1.8, P[i].s)); }

// ---- 조작
let drag = null, moved = 0, lastT = 0;
cv.addEventListener('contextmenu', ev => ev.preventDefault());
cv.addEventListener('mousedown', ev => {
  drag = { x: ev.clientX, y: ev.clientY, btn: ev.button, shift: ev.shiftKey }; moved = 0; cv.classList.add('drag'); S.spin = false; ui('fSpin').checked = false;
});
addEventListener('mousemove', ev => {
  if (drag) {
    const dx = ev.clientX - drag.x, dy = ev.clientY - drag.y; drag.x = ev.clientX; drag.y = ev.clientY; moved += Math.abs(dx) + Math.abs(dy);
    if (drag.btn === 0 && !drag.shift) { S.yaw += dx * 0.006; S.pitch = Math.max(-1.5, Math.min(1.5, S.pitch + dy * 0.006)); }
    else { S.panX += dx; S.panY += dy; }
    S.dirty = true; tip.style.display = 'none'; return;
  }
  // 호버
  const best = hit(ev.clientX, ev.clientY);
  if (best !== S.hover) { S.hover = best; S.dirty = true; }
  if (best >= 0) {
    const n = N[best];
    tip.innerText = `${n.name}  (${n.sw_id}, ${n.field})\n조작 ${n.op} · 자동화 IF ${n.auto_if} · 폐쇄망 ${n.airgap}\n자동화 ${n.auto ? '가능' : '불가/모름'} · 연결 ${adj[best].size}쌍` + (n.isolated ? '\n고립: 어떤 연결에도 없음' : '') + '\n클릭하면 연결 목록';
    tip.style.display = 'block'; tip.style.left = Math.min(innerWidth - 350, ev.clientX + 14) + 'px'; tip.style.top = (ev.clientY + 14) + 'px';
  } else tip.style.display = 'none';
});
function hit(x, y) { // 화면 좌표에서 가장 가까운 노드 (12px 안)
  let best = -1, bd = 12 * 12;
  for (let i = 0; i < N.length; i++) { const p = P[i]; const d = (p.x - x) ** 2 + (p.y - y) ** 2; if (d < bd) { bd = d; best = i; } }
  return best;
}
addEventListener('mouseup', ev => {
  if (drag && moved < 4 && drag.btn === 0) { // 클릭 = 선택 (마우스 이동 없이 바로 클릭해도 좌표로 찾는다)
    const h = hit(ev.clientX, ev.clientY);
    S.sel = (h >= 0 && h !== S.sel) ? h : -1; S.hover = h; showSide(); S.dirty = true;
  }
  drag = null; cv.classList.remove('drag');
});
cv.addEventListener('wheel', ev => { ev.preventDefault(); S.dist = Math.max(220, Math.min(3200, S.dist * (ev.deltaY > 0 ? 1.1 : 0.9))); S.dirty = true; }, { passive: false });
cv.addEventListener('dblclick', resetView);
ui('reset').addEventListener('click', resetView);
function resetView() { S.yaw = 0.6; S.pitch = 0.35; S.dist = 900; S.panX = 0; S.panY = 0; S.sel = -1; showSide(); S.dirty = true; }
['fManual', 'fNote', 'fAuto', 'fGrade', 'fLabel', 'fCluster'].forEach(id => ui(id).addEventListener('change', () => { S.dirty = true; }));
ui('fSpin').addEventListener('change', ev => { S.spin = ev.target.checked; });
ui('closeSide').addEventListener('click', () => { S.sel = -1; showSide(); S.dirty = true; });
// 터치: 한 손가락 회전, 두 손가락 핀치 줌
let touches = null;
cv.addEventListener('touchstart', ev => { touches = [...ev.touches].map(t => ({ x: t.clientX, y: t.clientY })); S.spin = false; ui('fSpin').checked = false; }, { passive: true });
cv.addEventListener('touchmove', ev => {
  const t = [...ev.touches].map(t => ({ x: t.clientX, y: t.clientY }));
  if (touches && t.length === 1 && touches.length === 1) { S.yaw += (t[0].x - touches[0].x) * 0.006; S.pitch = Math.max(-1.5, Math.min(1.5, S.pitch + (t[0].y - touches[0].y) * 0.006)); }
  else if (touches && t.length === 2 && touches.length === 2) { const d0 = Math.hypot(touches[0].x - touches[1].x, touches[0].y - touches[1].y), d1 = Math.hypot(t[0].x - t[1].x, t[0].y - t[1].y); S.dist = Math.max(220, Math.min(3200, S.dist * d0 / Math.max(1, d1))); }
  touches = t; S.dirty = true; ev.preventDefault();
}, { passive: false });

function showSide() {
  if (S.sel < 0) { side.style.display = 'none'; return; }
  const n = N[S.sel];
  const out = [], inn = [];
  for (const k of adj[S.sel]) { const e = E[k]; (e.s === S.sel ? out : inn).push(e); }
  const li = (e, other) => `<li><b style="color:${COL[e.kind]}">${e.kind === 'manual' ? '수기' : e.kind === 'note' ? '비고' : '자동'}</b>${e.grade ? ' <span class="g' + e.grade + '">' + e.grade + '</span>' : ''} ${N[other].field} / ${N[other].name} <span class="m">(${e.n}건)</span><div class="m">${e.items.join('<br>')}</div></li>`;
  const rk = rankedByNode[S.sel].map(r => `<li><span class="g${r.grade}">${r.grade}</span> #${r.rank} ${r.kind} — ${N[r.s].name} → ${N[r.t].name} <span class="m">${r.data}</span></li>`);
  sideBody.innerHTML = `<h2>${n.name} <span class="m">${n.sw_id} · ${n.field}</span></h2>
   <div class="m">${n.kind} · 조작 ${n.op} · 자동화 IF ${n.auto_if} · 폐쇄망 ${n.airgap} · 사용 ${n.users ?? '?'}명 · ${n.freq}</div>
   <h2>이 툴이 내놓는 것 → ${out.length}쌍</h2><ul>${out.map(e => li(e, e.t)).join('') || '<li class="m">없음</li>'}</ul>
   <h2>이 툴이 받는 것 ← ${inn.length}쌍</h2><ul>${inn.map(e => li(e, e.s)).join('') || '<li class="m">없음</li>'}</ul>
   <h2>착수 순위에 오른 구간</h2><ul>${rk.join('') || '<li class="m">없음</li>'}</ul>`;
  side.style.display = 'block';
}

function loop(t) {
  if (S.spin) { S.yaw += 0.0025; S.dirty = true; }
  if (S.dirty) { draw(); S.dirty = false; }
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
</script></body></html>
"""

out = REPO / "output" / "preview_map3d.html"
out.write_text(PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False)), encoding="utf-8", newline="\n")
print(f"wrote {out} ({out.stat().st_size:,} bytes): nodes={len(nodes)} edges={len(edges)} clusters={len(clusters)} ranked={len(ranked)}")
