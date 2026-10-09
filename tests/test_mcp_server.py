"""M6 v0 — Tool Ontology MCP 서버 (docs/12, Leo 2026-10-09).

- 질의 층(onto_store)이 3D 뷰어와 같은 숫자를 낸다 (툴 기준 후보 순위·입출력 수).
- 실제 MCP 프로토콜(stdio)로 서버를 띄워 도구 8개를 나열·호출한다 — 사내 브리지가 하는 것과 같은 길.
- 자유 텍스트의 인명 유사 표기는 도구 결과에 나오지 않는다 (절대 규칙 5).
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from engenius_onto.config import REPO_ROOT
from engenius_onto.survey_load import DATA_SETS, run_load


TOOLS = ["overview", "find_tool", "tool_info", "part_tools", "tool_io", "tool_partners", "manual_handoffs", "hub_candidates"]


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("mcp")
    shutil.copytree(DATA_SETS["synthetic"][1], tmp / "registry")
    return run_load(registry_dir=tmp / "registry", out_root=tmp / "out", shacl=False).out_dir


@pytest.fixture(scope="module")
def store(run_dir):
    from engenius_onto.onto_store import OntologyStore

    return OntologyStore(run=run_dir)


def test_store_matches_viewer(store, run_dir):
    """툴 기준 후보 순위와 건수가 3D 뷰어(graph_view3d.build)와 같다 — 지도와 에이전트가 같은 숫자를 본다."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import graph_view3d

    data, _ = graph_view3d.build(run_dir)
    nodes = data["nodes"]
    viewer = [(nodes[r["t"]]["name"], nodes[r["i"]]["sw_id"], r["partners"], r["declared"], r["mentioned"], r["manual"], r["parts"])
              for r in data["rank"]]
    mine = [(r["tool"], r["tool_id"], r["partners"], r["declared"], r["mentioned"], r["manual"], r["parts"]) for r in store.hub_candidates()]
    assert mine == viewer
    o = store.overview()
    assert (o["tools"], o["usages"], o["ios"], len(o["parts"])) == (data["counts"]["tools"], data["counts"]["usages"],
                                                                   data["counts"]["ios"], data["counts"]["fields"])


def test_store_queries(store):
    assert [r["tool"] for r in store.find_tool("엑셀")] == ["Excel"]                      # 공개 별칭(엑셀 → Excel)도 찾는다
    assert {r["tool"] for r in store.find_tool("ansys")} >= {"ANSYS FLUENT", "ANSYS Mechanical"}
    info = store.tool_info("excel")
    assert info["tool"] == "Excel" and len(info["usages"]) == 6
    assert "matches" in store.tool_info("ansys")                                          # 여럿이면 고르라고 한다
    p = store.part_tools("구조")
    assert [u["tool_id"] for u in p["usages"]] == ["STR-01", "STR-02", "STR-03", "STR-04", "STR-05"]
    partners = store.tool_partners("Excel")["partners"]
    assert any(e["partner"] == "가상-1D네트워크" and e["flow"] == "보냄" and e["manual"] >= 1 for e in partners)
    h = store.manual_handoffs()["handoffs"]
    assert h and all(r["kind"] in ("수기", "비고") for r in h)
    assert store.manual_handoffs("SAS")["handoffs"] and all(r["part"] == "SAS" for r in store.manual_handoffs("SAS")["handoffs"])
    assert "error" in store.part_tools("없는파트")


def test_person_like_text_is_masked(store):
    """합성 SAS 의 애로 구간에는 'OOO 선임(내선 0000)' 같은 인명 유사 표기가 있다 — 도구 결과에는 나오지 않는다."""
    from engenius_onto.mcp_server import Tools

    t = Tools(store)
    text = "\n".join([t.tool_info(r["tool"]) for r in store.find_tool("")] + [t.manual_handoffs(), t.tool_io("Excel")])
    leaks = [ln for ln in text.splitlines() if "내선" in ln or "선임" in ln]
    assert not leaks, leaks
    assert "[인명 추정 가림]" in text


def test_self_check(store, capsys):
    from engenius_onto.mcp_server import self_check

    assert self_check(store) == 0
    assert "도구 8/8 동작" in capsys.readouterr().err


def _rpc(srv, method, params=None, mid=1):
    msg = {"jsonrpc": "2.0", "method": method, **({"id": mid} if mid is not None else {}), **({"params": params} if params is not None else {})}
    return srv.handle(msg)


def test_jsonrpc_handling(store):
    """표준 라이브러리 서버의 프로토콜 처리 — 판 협상·알림 무응답·모르는 메서드·인자 오류·도구 실패는 isError·배치."""
    import io

    from engenius_onto.mcp_server import PROTOCOL_VERSIONS, Server

    srv = Server(store)
    r = _rpc(srv, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}})
    assert r["result"]["protocolVersion"] == "2024-11-05" and r["result"]["capabilities"] == {"tools": {"listChanged": False}}
    r = _rpc(srv, "initialize", {"protocolVersion": "2099-01-01", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}})
    assert r["result"]["protocolVersion"] == PROTOCOL_VERSIONS[0]                  # 모르는 판이면 우리가 아는 최신으로
    assert _rpc(srv, "notifications/initialized", mid=None) is None
    assert _rpc(srv, "ping")["result"] == {}
    tools = _rpc(srv, "tools/list")["result"]["tools"]
    assert sorted(t["name"] for t in tools) == sorted(TOOLS) and all(t["inputSchema"]["type"] == "object" for t in tools)
    assert _rpc(srv, "resources/list")["result"] == {"resources": []} and _rpc(srv, "prompts/list")["result"] == {"prompts": []}
    assert _rpc(srv, "nope")["error"]["code"] == -32601
    assert _rpc(srv, "tools/call", {"name": "nope", "arguments": {}})["error"]["code"] == -32602
    assert _rpc(srv, "tools/call", {"name": "tool_info", "arguments": {}})["error"]["code"] == -32602        # 필수 인자 빠짐
    ok = _rpc(srv, "tools/call", {"name": "find_tool", "arguments": {"query": "엑셀"}})["result"]
    assert ok["isError"] is False and "Excel" in ok["content"][0]["text"]
    srv.tools.overview = lambda: 1 / 0                                             # 도구 실패 → 결과의 isError (프로토콜 오류 아님)
    bad = _rpc(srv, "tools/call", {"name": "overview", "arguments": {}})["result"]
    assert bad["isError"] is True and "ZeroDivisionError" in bad["content"][0]["text"]
    # serve(): 한 줄 = 메시지, 배치 배열, 깨진 JSON, 빈 줄
    lines = [json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}), "",
             json.dumps([{"jsonrpc": "2.0", "id": 2, "method": "ping"}, {"jsonrpc": "2.0", "method": "notifications/initialized"}]),
             "{broken"]
    out = io.BytesIO()
    Server(store).serve(io.BytesIO(("\n".join(lines) + "\n").encode("utf-8")), out)
    got = [json.loads(ln) for ln in out.getvalue().decode("utf-8").splitlines()]
    assert got[0]["id"] == 1 and got[1] == [{"jsonrpc": "2.0", "id": 2, "result": {}}] and got[2]["error"]["code"] == -32700


def _bridge_cmd(run_dir: Path) -> tuple[list[str], dict]:
    """브리지가 띄우는 그대로: python -X utf8 scripts/mcp_server.py — PYTHONPATH·PYTHONUTF8 없이."""
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING", "PYTHONPATH")}
    return [sys.executable, "-X", "utf8", str(REPO_ROOT / "scripts" / "mcp_server.py"), "--run", str(run_dir)], env


def test_stdio_raw_roundtrip(run_dir):
    """SDK 없이 줄 단위 JSON-RPC 로 실제 프로세스와 주고받는다 — 사내 selftest 에서도 도는 프로토콜 점검. stdout 에는 MCP 메시지만."""
    import subprocess

    cmd, env = _bridge_cmd(run_dir)
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "raw", "version": "0"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "tool_partners", "arguments": {"tool": "Excel"}}}]
    p = subprocess.run(cmd, input="".join(json.dumps(m, ensure_ascii=False) + "\n" for m in msgs).encode("utf-8"),
                       capture_output=True, env=env, cwd=str(run_dir), timeout=120)
    out = [json.loads(ln) for ln in p.stdout.decode("utf-8").splitlines()]        # 전부 JSON 이어야 한다 (잡음 출력 없음)
    assert [m["id"] for m in out] == [1, 2, 3] and p.returncode == 0
    assert out[0]["result"]["serverInfo"]["name"] == "engenius-tool-ontology"
    assert sorted(t["name"] for t in out[1]["result"]["tools"]) == sorted(TOOLS)
    assert "가상-1D네트워크" in out[2]["result"]["content"][0]["text"]


def test_stdio_protocol_roundtrip_with_official_sdk(run_dir):
    """공식 MCP SDK 클라이언트로 우리 서버(표준 라이브러리 구현)를 검사한다 — 규격 준수 확인. SDK 는 개발 PC 전용 (반입 안 함)."""
    pytest.importorskip("mcp")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    cmd, env = _bridge_cmd(run_dir)
    params = StdioServerParameters(command=cmd[0], args=cmd[1:], env=env, cwd=str(run_dir))

    async def go():
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                init = await s.initialize()
                listed = await s.list_tools()
                res = {}
                for name, args in [("overview", {}), ("find_tool", {"query": "엑셀"}), ("tool_partners", {"tool": "Excel"}),
                                   ("hub_candidates", {"limit": 3}), ("part_tools", {"part": "SAS"})]:
                    out = await s.call_tool(name, args)
                    res[name] = (out.isError, out.content[0].text)
                return init, listed, res

    init, listed, res = asyncio.run(go())
    assert init.serverInfo.name == "engenius-tool-ontology" and init.instructions
    assert sorted(t.name for t in listed.tools) == sorted(TOOLS)
    assert all(t.description for t in listed.tools)
    assert not any(err for err, _ in res.values())
    assert "Excel" in res["find_tool"][1] and "가상-1D네트워크" in res["tool_partners"][1]
    assert "합성 데이터" in res["overview"][1] or "custom" in res["overview"][1]
