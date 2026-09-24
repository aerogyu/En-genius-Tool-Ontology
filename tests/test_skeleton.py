"""M0 골격 테스트 — 외부 네트워크 없이 통과해야 한다 (Fuseki 테스트는 서버 없으면 skip)."""

from __future__ import annotations

import subprocess
import sys
import urllib.parse
import urllib.request

import pytest
from rdflib import Literal, URIRef

from engenius_onto.backends import fuseki_alive, local_dataset
from engenius_onto.cli import COMMANDS, main
from engenius_onto.config import REPO_ROOT, fuseki_config, namespaces

G1 = URIRef("http://en-genius.local/graph/test-a")
G2 = URIRef("http://en-genius.local/graph/test-b")
S = URIRef("http://en-genius.local/id/TEST-000001")
P = URIRef("http://www.w3.org/2000/01/rdf-schema#label")

UNION_QUERY = """
SELECT ?o WHERE { <http://en-genius.local/id/TEST-000001> <http://www.w3.org/2000/01/rdf-schema#label> ?o }
ORDER BY ?o
"""


def test_help_subprocess():
    """python -m engenius_onto --help 가 동작한다 (M0 완료 기준)."""
    r = subprocess.run(
        [sys.executable, "-m", "engenius_onto", "--help"],
        capture_output=True, text=True, encoding="utf-8", cwd=REPO_ROOT,
    )
    assert r.returncode == 0
    for name in COMMANDS:
        assert name in r.stdout


@pytest.mark.parametrize("name", [n for n, (_, ms) in COMMANDS.items() if ms == "M4"])
def test_unimplemented_commands_fail_loudly(name):
    """미구현 명령은 조용히 성공하지 않는다."""
    assert main([name]) == 2


def test_config_loads():
    cfg = fuseki_config()
    assert cfg.dataset == "engenius"
    assert set(cfg.graphs) == {"schema", "survey", "derived"}
    ns = namespaces()
    assert ns["eg"].endswith("/onto/") and ns["egid"].endswith("/id/")


def test_local_union_default_graph():
    """로컬 백엔드: 기본 그래프 질의가 모든 named graph 의 합집합을 본다."""
    ds = local_dataset()
    ds.graph(G1).add((S, P, Literal("가", lang="ko")))
    ds.graph(G2).add((S, P, Literal("나", lang="ko")))
    got = [str(row.o) for row in ds.query(UNION_QUERY)]
    assert got == ["가", "나"]


def _gsp(cfg, method, graph, data=None):
    url = f"{cfg.dataset_url}/data?graph=" + urllib.parse.quote(str(graph), safe="")
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "text/turtle; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=cfg.timeout_s) as r:
        return r.status


@pytest.mark.fuseki
def test_fuseki_union_matches_local():
    """Fuseki 백엔드도 같은 질의에 같은 결과 (unionDefaultGraph)."""
    cfg = fuseki_config()
    if not fuseki_alive(cfg):
        pytest.skip("Fuseki 가 떠 있지 않음")
    ttl_a = f'<{S}> <{P}> "가"@ko .'.encode("utf-8")
    ttl_b = f'<{S}> <{P}> "나"@ko .'.encode("utf-8")
    try:
        _gsp(cfg, "PUT", G1, ttl_a)
        _gsp(cfg, "PUT", G2, ttl_b)
        url = f"{cfg.dataset_url}/sparql?query=" + urllib.parse.quote(UNION_QUERY)
        req = urllib.request.Request(url, headers={"Accept": "application/sparql-results+json"})
        import json
        with urllib.request.urlopen(req, timeout=cfg.timeout_s) as r:
            res = json.load(r)
        got = [b["o"]["value"] for b in res["results"]["bindings"]]
        assert got == ["가", "나"]
    finally:
        for g in (G1, G2):
            try:
                _gsp(cfg, "DELETE", g)
            except Exception:
                pass
