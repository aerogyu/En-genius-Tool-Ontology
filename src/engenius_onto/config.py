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


def namespaces(config_dir: Path | None = None) -> dict:
    return load_yaml("namespaces.yaml", config_dir)
