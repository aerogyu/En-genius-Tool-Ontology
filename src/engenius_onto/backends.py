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
