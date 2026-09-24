"""설정 파일 읽기. 경로는 저장소 루트(config/) 기준."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"


def load_yaml(name: str, config_dir: Path | None = None) -> dict:
    path = (config_dir or CONFIG_DIR) / name
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass(frozen=True)
class FusekiConfig:
    endpoint: str
    dataset: str
    graphs: dict
    timeout_s: float = 10.0

    @property
    def dataset_url(self) -> str:
        return f"{self.endpoint.rstrip('/')}/{self.dataset}"

    @property
    def ping_url(self) -> str:
        return f"{self.endpoint.rstrip('/')}/$/ping"


def fuseki_config(config_dir: Path | None = None) -> FusekiConfig:
    d = load_yaml("fuseki.yaml", config_dir)
    return FusekiConfig(
        endpoint=d["endpoint"],
        dataset=d["dataset"],
        graphs=dict(d["graphs"]),
        timeout_s=float(d.get("timeout_s", 10)),
    )


SCHEMA_FILE = REPO_ROOT / "schema" / "engenius_tool.yaml"


def namespaces(schema_file: Path | None = None) -> dict:
    """온톨로지·인스턴스 네임스페이스 {eg, egid}. 정본은 스키마 prefixes 한 곳이다.

    바꿀 때는 schema/engenius_tool.yaml(과 검증용 컨테이너 스키마) 의 prefixes 를 고치고
    python -m engenius_onto schema 로 재생성한다 — 생성물(OWL·SHACL·Pydantic)이 IRI 를 담기 때문.
    """
    with (schema_file or SCHEMA_FILE).open(encoding="utf-8") as f:
        prefixes = yaml.safe_load(f)["prefixes"]
    return {"eg": prefixes["eg"], "egid": prefixes["egid"]}
