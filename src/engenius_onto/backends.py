"""그래프 백엔드 2종 — 로컬(rdflib)과 Fuseki.

두 백엔드는 같은 named graph 구성과 '기본 그래프 = 합집합' 의미를 가져야 한다
(docs/02 8장). SPARQL 은 표준 1.1 문법만 쓴다.
"""

from __future__ import annotations

import urllib.error
import urllib.request

from rdflib import Dataset

from engenius_onto.config import FusekiConfig


def local_dataset() -> Dataset:
    """Fuseki 의 unionDefaultGraph 와 같은 의미의 rdflib Dataset."""
    return Dataset(default_union=True)


def fuseki_alive(cfg: FusekiConfig) -> bool:
    """Fuseki 관리 엔드포인트 /$/ping 응답 여부."""
    try:
        with urllib.request.urlopen(cfg.ping_url, timeout=cfg.timeout_s) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


def fuseki_dataset_exists(cfg: FusekiConfig) -> bool:
    """데이터셋 SPARQL 엔드포인트가 ASK 질의에 응답하는지."""
    url = f"{cfg.dataset_url}/sparql?query=" + urllib.request.quote("ASK {}")
    req = urllib.request.Request(url, headers={"Accept": "application/sparql-results+json"})
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_s) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


def push_graph(cfg: FusekiConfig, graph_iri: str, turtle: bytes) -> int:
    """named graph 하나를 통째 교체 (SPARQL Graph Store Protocol PUT) 하고 올라간 트리플 수를 돌려준다."""
    import urllib.parse

    url = f"{cfg.dataset_url}/data?graph=" + urllib.parse.quote(graph_iri, safe="")
    req = urllib.request.Request(url, data=turtle, method="PUT",
                                 headers={"Content-Type": "text/turtle; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=max(cfg.timeout_s, 60)) as r:
        if r.status not in (200, 201, 204):
            raise RuntimeError(f"Fuseki PUT 실패 {r.status}: {graph_iri}")
    return int(select(cfg, f"SELECT (COUNT(*) AS ?n) WHERE {{ GRAPH <{graph_iri}> {{ ?s ?p ?o }} }}")[0]["n"])


def select(cfg: FusekiConfig, query: str) -> list[dict]:
    """Fuseki SPARQL SELECT → [{변수: 값 문자열}]."""
    import json
    import urllib.parse

    body = urllib.parse.urlencode({"query": query}).encode("utf-8")
    req = urllib.request.Request(f"{cfg.dataset_url}/sparql", data=body, method="POST", headers={
        "Accept": "application/sparql-results+json", "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=max(cfg.timeout_s, 60)) as r:
        res = json.load(r)
    return [{k: v["value"] for k, v in b.items()} for b in res["results"]["bindings"]]


def delete_graph(cfg: FusekiConfig, graph_iri: str) -> bool:
    """named graph 하나를 지운다 (SPARQL Graph Store Protocol DELETE). 그래프가 없어서 404 가 와도 정상 — False 를 돌려준다.
    push 는 실행 폴더에 derived.ttl 이 없을 때 이것으로 derived 그래프를 비운다 (docs/09 #25a — 옛 파생 결과가 새 survey 와 섞이지 않게)."""
    import urllib.parse

    url = f"{cfg.dataset_url}/data?graph=" + urllib.parse.quote(graph_iri, safe="")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="DELETE"), timeout=max(cfg.timeout_s, 60)) as r:
            if r.status not in (200, 202, 204):
                raise RuntimeError(f"Fuseki DELETE 실패 {r.status}: {graph_iri}")
        return True
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        return False


def load_local(ds: Dataset, graph_iri: str, turtle: str) -> None:
    """로컬 Dataset 의 named graph 하나를 통째 교체 (Fuseki push_graph 와 같은 의미)."""
    from rdflib import URIRef

    g = ds.graph(URIRef(graph_iri))
    g.remove((None, None, None))
    g.parse(data=turtle, format="turtle")
