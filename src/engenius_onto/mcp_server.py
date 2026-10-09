"""Tool Ontology MCP 서버 (M6 v0, 2026-10-09) — 사내 AI 플랫폼 에이전트가 부르는 읽기 전용 도구 8개.

실행: python -X utf8 -m engenius_onto mcp            (stdio — 사내 플랫폼의 En-genius MCP 브리지가 프로세스로 띄운다)
      python -m engenius_onto mcp --check             (플랫폼 없이 도구를 한 번씩 불러 보는 자기 점검)
전송은 stdio 만 (Leo PC → 플랫폼 아웃바운드 구조, docs/12 4장). stdout 은 MCP 메시지 전용 — 여기서 print 하지 않는다 (로그는 stderr).

도구는 onto_store.OntologyStore 의 질의를 마크다운 표로 돌려준다 (어느 MCP 판·클라이언트에서도 읽히는 텍스트).
값은 적재한 실데이터 그대로 사내 LLM 으로 간다 (Leo 2026-10-09 승인); 자유 텍스트의 인명 유사 표기는 가린다 (절대 규칙 5).
에이전트는 판정하지 않는다 — 도구 설명과 결과 머리말이 '후보·잠정·원자료' 임을 밝힌다 (절대 규칙 6).
"""

from __future__ import annotations

import sys
from pathlib import Path

from engenius_onto.onto_store import OntologyStore

SERVER_NAME = "engenius-tool-ontology"
INSTRUCTIONS = (
    "한화에어로스페이스 엔진 연구소 각 파트의 툴 조사를 적재한 지식 그래프(Tool Ontology)다. "
    "툴(예: Excel, ANSYS Fluent), 툴사용(파트 × 툴 — 조사표 한 행), 입출력(툴사용이 받고 내놓는 데이터: 이름·분류·확장자·전달 방법·연계 툴)으로 이뤄진다. "
    "파트는 약칭(예: SAS, PRF)으로 부른다 — 먼저 overview 로 파트 목록과 규모를 본다. "
    "'연결 상대'는 조사표의 '연계 Tool명'으로 신고된 것만이다 (확장자·분류로 계산한 연결과 착수 등급은 아직 없다 — M4). "
    "결과는 후보·원자료이며 판정은 엔지니어가 한다. 표에 없는 사실을 지어내지 말고, 모르면 모른다고 답한다. "
    "도구가 준 순위·건수는 그대로 전하고, 행을 세거나 다른 기준으로 순위를 다시 매기지 않는다."
)
MAX_ROWS = 200


def _table(rows: list[dict], cols: list[tuple[str, str]], limit: int = MAX_ROWS, redact=lambda s: s) -> str:
    """[{…}] → 마크다운 표. cols = [(키, 머리글)]. 행이 많으면 앞에서 limit 개만 — 잘랐다고 밝힌다 (조용히 자르지 않는다).
    redact: 모든 칸에 인명 유사 표기 가리기 (자유 텍스트 열만이 아니라 데이터명·연계 Tool명 칸도 — 적재기는 경고만 하고 값을 보존한다)."""
    if not rows:
        return "(해당 없음)"

    def cell(v) -> str:
        if isinstance(v, bool):
            v = "예" if v else "아니오"
        elif isinstance(v, (list, tuple, set)):
            v = ", ".join(str(x) for x in v)
        return redact(str(v if v not in (None, "") else "-")).replace("|", "/").replace("\n", " ")

    out = ["| " + " | ".join(h for _, h in cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(cell(r.get(k)) for k, _ in cols) + " |" for r in rows[:limit]]
    if len(rows) > limit:
        out.append(f"\n(전체 {len(rows)}행 중 앞 {limit}행만 — 조건을 좁혀 다시 묻는다)")
    return "\n".join(out)


def _matches(res: dict, what: str) -> str | None:
    if "matches" not in res:
        return None
    m = res["matches"]
    if not m:
        return f"'{what}' 에 해당하는 툴이 없다. find_tool 로 이름 일부를 검색해 본다."
    return f"'{what}' 에 해당하는 툴이 여럿이다 — 하나를 골라 다시 묻는다: " + ", ".join(m)


class Tools:
    """도구 본문 — MCP 와 분리해 두어 --check·테스트가 그대로 부른다."""

    def __init__(self, store: OntologyStore):
        self.s = store

    def _table(self, rows, cols, limit: int = MAX_ROWS) -> str:
        return _table(rows, cols, limit, redact=self.s.redact)

    def _head(self) -> str:
        o = self.s.overview()
        kind = {"real": "실데이터", "synthetic": "합성 데이터"}.get(o["dataset"], o["dataset"])
        return f"(적재 {o['run']} · {kind})\n"

    def overview(self) -> str:
        o = self.s.overview()
        return (self._head() + f"툴 {o['tools']} · 툴사용 {o['usages']} · 입출력 {o['ios']} · 파트 {len(o['parts'])}\n\n"
                + self._table(o["parts"], [("code", "파트 약칭"), ("name", "파트 이름"), ("usages", "툴사용"), ("ios", "입출력")]))

    def find_tool(self, query: str) -> str:
        rows = self.s.find_tool(query)
        return self._head() + self._table(rows, [("tool", "툴 (대표 이름)"), ("alt", "다른 표기"), ("vendor", "제조사"),
                                            ("usages", "툴사용 수"), ("parts", "쓰는 파트")])

    def tool_info(self, tool: str) -> str:
        r = self.s.tool_info(tool)
        if (m := _matches(r, tool)) is not None:
            return m
        head = f"**{r['tool']}** · 제조사 {r['vendor'] or '-'} · 구분 {r['kind'] or '-'} · 다른 표기 {', '.join(r['alt']) or '-'}\n\n"
        cols = [("part", "파트"), ("tool_id", "Tool ID"), ("purpose_class", "용도"), ("purpose_detail", "세부 용도"), ("phase", "사용 단계"),
                ("frequency", "빈도"), ("user_count", "인원"), ("operation_mode", "조작 방식"), ("automation_if", "자동화 IF"),
                ("auto", "자동화 가능(잠정)"), ("ios_in", "입력 수"), ("ios_out", "출력 수"), ("pain_points", "애로 구간"),
                ("automation_wish", "자동화 희망"), ("priority_opinion", "우선순위 의견")]
        return self._head() + head + self._table(r["usages"], cols)

    def part_tools(self, part: str) -> str:
        r = self.s.part_tools(part)
        if "error" in r:
            return f"{r['error']} — 파트 약칭: {', '.join(r['parts'])}"
        return self._head() + f"**{r['part']}** ({r['name']}) 가 쓰는 툴\n\n" + self._table(r["usages"], [
            ("tool_id", "Tool ID"), ("tool", "툴"), ("purpose", "용도"), ("operation_mode", "조작 방식"), ("automation_if", "자동화 IF"),
            ("auto", "자동화 가능(잠정)"), ("ios_in", "입력 수"), ("ios_out", "출력 수"), ("manual", "수기 전달 수")])

    def tool_io(self, tool: str, part: str = "") -> str:
        r = self.s.tool_io(tool, part or None)
        if (m := _matches(r, tool)) is not None:
            return m
        return self._head() + f"**{r['tool']}** 의 입출력\n\n" + self._table(r["ios"], [
            ("part", "파트"), ("tool_id", "Tool ID"), ("dir", "방향"), ("data", "데이터"), ("category", "분류"), ("ext", "확장자"),
            ("transfer", "전달 방법"), ("partner", "연계 툴(신고)"), ("note", "비고")])

    def tool_partners(self, tool: str) -> str:
        r = self.s.tool_partners(tool)
        if (m := _matches(r, tool)) is not None:
            return m
        return (self._head() + f"**{r['tool']}** 와 데이터를 주고받는다고 **조사표에 신고된** 툴 (확장자로 계산한 연결은 M4 뒤)\n"
                "보냄 = 이 툴 → 상대, 받음 = 상대 → 이 툴. 자기 신고 = 이 툴 쪽 조사표, 상대 언급 = 상대 쪽 조사표.\n\n"
                + self._table(r["partners"], [("partner", "상대 툴"), ("flow", "방향"), ("how", "근거"), ("parts", "파트"),
                                         ("manual", "수기 전달 수"), ("data", "데이터 [확장자] · 전달 방법")]))

    def manual_handoffs(self, part: str = "") -> str:
        r = self.s.manual_handoffs(part or None)
        if part and r["part"] is None:
            return f"파트 '{part}' 를 찾지 못함 — overview 로 파트 약칭을 확인한다"
        return (self._head() + "사람 손으로 옮기는 구간의 **원자료** (전달 방법이 수기이거나 비고에 수기 신호). "
                "착수 등급·순위는 아직 계산 전 — 후보로만 본다.\n\n"
                + self._table(r["handoffs"], [("kind", "종류"), ("part", "파트"), ("tool_id", "Tool ID"), ("tool", "툴"), ("dir", "방향"),
                                         ("data", "데이터"), ("ext", "확장자"), ("transfer", "전달 방법"), ("partner", "연계 툴"),
                                         ("frequency", "빈도"), ("auto", "자동화 가능(잠정)"), ("note", "비고")]))

    def hub_candidates(self, limit: int = 20, by: str = "tool") -> str:
        lim = max(1, min(int(limit), MAX_ROWS))
        head = (self._head() + "툴 기준 에이전트 후보 (**잠정** — 조사표에 신고된 연결 기준, 3D 지도 '툴 기준 후보' 와 같은 순서). "
                "정렬: 연결 상대 수 → 수기 전달 수 → 자동화 가능 → 같은 툴을 쓰는 파트 수. 판정은 엔지니어가 한다.\n"
                "**'순위' 열이 정본이다 — 이 순서를 바꾸거나 다른 기준(쓰는 파트 수 등)으로 다시 매기지 말고 그대로 전한다.**\n\n")
        if by == "usage":                                            # 파트별 행 (툴사용 단위) — 같은 툴이 파트마다 한 줄
            rows = [{"rank": i + 1, **r} for i, r in enumerate(self.s.hub_candidates())]
            return head + self._table(rows, [("rank", "순위"), ("tool", "툴"), ("part", "파트"), ("tool_id", "Tool ID"), ("partners", "연결 상대"),
                                             ("declared", "자기 신고"), ("mentioned", "상대 언급"), ("manual", "수기 전달"),
                                             ("auto", "자동화 가능"), ("parts", "같은 툴 쓰는 파트")], limit=lim)
        rows = self.s.hub_candidates_by_tool()
        return head + "툴로 묶은 순위 — 툴 순서는 그 툴을 쓰는 파트 중 가장 앞선 것 기준 (지도 순위표와 같다).\n\n" + self._table(rows, [
            ("rank", "순위"), ("tool", "툴"), ("partners", "연결 상대 (최고)"), ("manual", "수기 전달"), ("auto", "자동화 가능"),
            ("parts", "쓰는 파트 수"), ("detail", "세부 순위 (파트)")], limit=lim)


def build_server(store: OntologyStore):
    """FastMCP 서버 — 도구 이름은 영문, 설명은 한국어 (LLM 이 고를 때 읽는다). 전부 읽기 전용."""
    from mcp.server.fastmcp import FastMCP

    t = Tools(store)
    mcp = FastMCP(SERVER_NAME, instructions=INSTRUCTIONS)

    @mcp.tool()
    def overview() -> str:
        """Tool Ontology 전체 규모와 파트 목록(약칭·이름·툴사용 수·입출력 수). 다른 도구를 쓰기 전에 먼저 부른다."""
        return t.overview()

    @mcp.tool()
    def find_tool(query: str) -> str:
        """툴 이름 일부로 툴을 찾는다 (대표 이름·다른 표기·조사표 표기, 대소문자·공백 무시). 빈 문자열이면 전체 툴 목록."""
        return t.find_tool(query)

    @mcp.tool()
    def tool_info(tool: str) -> str:
        """툴 하나의 정보 — 제조사와, 그 툴을 쓰는 파트별 용도·빈도·인원·조작 방식·자동화 인터페이스·애로 구간·자동화 희망."""
        return t.tool_info(tool)

    @mcp.tool()
    def part_tools(part: str) -> str:
        """파트(약칭 또는 이름)가 쓰는 툴 목록 — 용도·조작 방식·자동화 IF·입출력 수·수기 전달 수."""
        return t.part_tools(part)

    @mcp.tool()
    def tool_io(tool: str, part: str = "") -> str:
        """툴의 입력·출력 데이터 (데이터 이름·분류·확장자·전달 방법·신고된 연계 툴). part 를 주면 그 파트의 것만."""
        return t.tool_io(tool, part)

    @mcp.tool()
    def tool_partners(tool: str) -> str:
        """툴과 데이터를 주고받는다고 조사표에 신고된 상대 툴 — 방향(보냄/받음)·근거(자기 신고/상대 언급)·데이터·수기 전달 수."""
        return t.tool_partners(tool)

    @mcp.tool()
    def manual_handoffs(part: str = "") -> str:
        """사람 손으로 데이터를 옮기는 구간(메일·수기 전달, 비고의 수기 신호) 원자료. part 를 주면 그 파트만. Tool Agent 후보를 찾을 때 쓴다."""
        return t.manual_handoffs(part)

    @mcp.tool()
    def hub_candidates(limit: int = 20, by: str = "tool") -> str:
        """툴 기준 에이전트 후보 순위(잠정, 3D 지도 '툴 기준 후보' 와 같은 순서) — 연결 상대가 많은 순. by="tool"(기본)은 툴로 묶은 순위,
        by="usage" 는 파트별 행. 결과의 '순위' 열 순서를 그대로 전한다 (다시 정렬하지 않는다). limit 행까지."""
        return t.hub_candidates(limit, by)

    return mcp


def self_check(store: OntologyStore, out=None) -> int:
    """플랫폼 없이 도구를 한 번씩 불러 본다 — 결과 앞부분만 stderr 로 (실데이터 값이 화면에 나오니 사내에서만 본다)."""
    out = out or sys.stderr
    t = Tools(store)
    try:
        o = store.overview()
    except FileNotFoundError as e:
        print(f"[NG] {e}", file=out)
        return 1
    sample_tool = (store.hub_candidates() or [{"tool": ""}])[0]["tool"]
    sample_part = o["parts"][0]["code"] if o["parts"] else ""
    calls = [("overview", lambda: t.overview()), ("find_tool", lambda: t.find_tool(sample_tool[:3])),
             ("tool_info", lambda: t.tool_info(sample_tool)), ("part_tools", lambda: t.part_tools(sample_part)),
             ("tool_io", lambda: t.tool_io(sample_tool)), ("tool_partners", lambda: t.tool_partners(sample_tool)),
             ("manual_handoffs", lambda: t.manual_handoffs()), ("hub_candidates", lambda: t.hub_candidates(5))]
    bad = 0
    for name, fn in calls:
        try:
            text = fn()
            print(f"[OK] {name} — {len(text)}자", file=out)
        except Exception as e:  # noqa: BLE001 — 점검은 다음 도구로 계속
            bad += 1
            print(f"[NG] {name} — {type(e).__name__}: {e}", file=out)
    print(f"[{'OK' if not bad else 'NG'}] 도구 {len(calls) - bad}/{len(calls)} 동작 (적재 {o['run']}, 툴 {o['tools']} · 툴사용 {o['usages']})", file=out)
    return 1 if bad else 0


def warm_up(store: OntologyStore) -> None:
    """stdio 루프를 시작하기 전에 도구를 한 번씩 돌려 모든 모듈을 메인 스레드에서 미리 import 한다.

    Windows 에서는 stdio 전송이 다른 스레드에서 stdin 파이프를 동기 읽기하는 동안, 도구 스레드가 C 확장(DLL — numpy 등)을 처음
    import 하면 DLL 초기화가 표준 핸들을 조회하다 멈춘다 (2026-10-09 재현: tools/call 이 numpy import 에서 영구 대기).
    그래서 시작할 때 import 를 끝내 둔다. 적재 결과가 아직 없어도 서버는 뜬다 (도구가 '먼저 적재' 를 알린다)."""
    import engenius_onto.survey_load  # noqa: F401 — openpyxl·pandas·numpy 까지 끌고 온다

    t = Tools(store)
    try:
        for fn in (t.overview, lambda: t.find_tool(""), lambda: t.hub_candidates(1), lambda: t.manual_handoffs()):
            fn()
        top = (store.hub_candidates() or [{"tool": ""}])[0]["tool"]
        for fn in (t.tool_info, t.tool_io, t.tool_partners):
            fn(top)
        t.part_tools((store.overview()["parts"] or [{"code": ""}])[0]["code"])
    except Exception as e:  # noqa: BLE001 — 데이터가 없거나 깨져도 서버는 띄우고, 이유는 stderr 로
        print(f"[mcp] 미리 읽기 실패 (도구 호출 때 다시 시도): {type(e).__name__}: {e}", file=sys.stderr)


def run(run_dir: str | None = None, backend: str = "local", check: bool = False, data: str = "real") -> int:
    store = OntologyStore(run=Path(run_dir) if run_dir else None, backend=backend, prefer=data)
    if check:
        return self_check(store)
    warm_up(store)
    build_server(store).run("stdio")
    return 0
