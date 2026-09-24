"""ID 레지스트리 (docs/02 4장, D3·D7) — FLD·TOOL·USE·CAT ID 를 CSV 로 고정해 재적재해도 같은 ID 를 쓴다.

- 키: 분야 = 이름, 툴 = 정규화 키, 분류 = 이름, 툴사용 = (FLD ID, SW ID 원문) — 원천 파일명은 키에 넣지 않는다 (D3).
- 이번 적재에 없는 분야·툴·분류는 지우지 않고 status=폐기 로 남긴다 — survey 그래프에도 폐기 상태로 계속 낸다 (D7).
  폐기된 ID 는 재발급하지 않는다 (다시 나오면 같은 ID 로 활성 복귀).
- 레지스트리는 데이터 옆에 둔다: data/synthetic/registry/, 사내는 data/real/registry/. 합성용을 실데이터에 쓰지 않는다.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

ACTIVE, MERGED, RETIRED = "활성", "통합됨", "폐기"

KINDS = {  # 종류 → (파일, ID 접두, 자릿수, 키 열)
    "field": ("fields.csv", "FLD", 3, ["key"]),
    "tool": ("tools.csv", "TOOL", 6, ["key"]),
    "category": ("categories.csv", "CAT", 3, ["key"]),
    "usage": ("usages.csv", "USE", 6, ["field_id", "source_key"]),
}


@dataclass
class Table:
    kind: str
    rows: list[dict] = field(default_factory=list)
    seen: set = field(default_factory=set)

    @property
    def spec(self):
        return KINDS[self.kind]

    def columns(self) -> list[str]:
        return ["id", *self.spec[3], "label", "status", "merged_into"]

    def _key(self, row: dict) -> tuple:
        return tuple(row[k] for k in self.spec[3])

    def find(self, key: tuple) -> dict | None:
        for r in self.rows:
            if self._key(r) == key:
                return r
        return None

    def assign(self, key: tuple, label: str) -> str:
        """키에 해당하는 ID (없으면 새 번호). 이번 적재에서 본 것으로 표시하고 활성으로 되돌린다."""
        r = self.find(key)
        if r is None:
            _, prefix, width, keys = self.spec
            n = max((int(x["id"].split("-")[1]) for x in self.rows), default=0) + 1
            r = {"id": f"{prefix}-{n:0{width}d}", **dict(zip(keys, key)), "label": label,
                 "status": ACTIVE, "merged_into": ""}
            self.rows.append(r)
        else:
            r["label"] = label
            if r["status"] == RETIRED:
                r["status"] = ACTIVE
        self.seen.add(r["id"])
        return r["id"]

    def retire_unseen(self) -> list[dict]:
        out = []
        for r in self.rows:
            if r["id"] not in self.seen and r["status"] == ACTIVE:
                r["status"] = RETIRED
            if r["id"] not in self.seen:
                out.append(r)
        return out


class Registry:
    def __init__(self, directory: Path):
        self.dir = Path(directory)
        self.tables = {k: Table(k) for k in KINDS}
        for kind, t in self.tables.items():
            p = self.dir / KINDS[kind][0]
            if p.is_file():
                with p.open(encoding="utf-8-sig", newline="") as f:
                    t.rows = [dict(r) for r in csv.DictReader(f)]
                for r in t.rows:
                    r.setdefault("merged_into", "")

    def assign(self, kind: str, key, label: str) -> str:
        return self.tables[kind].assign(key if isinstance(key, tuple) else (key,), label)

    def id_of(self, kind: str, key) -> str | None:
        r = self.tables[kind].find(key if isinstance(key, tuple) else (key,))
        return r["id"] if r else None

    def mark_merged(self, kind: str, key, into_id: str) -> None:
        r = self.tables[kind].find(key if isinstance(key, tuple) else (key,))
        if r is not None:
            r["status"], r["merged_into"] = MERGED, into_id
            self.tables[kind].seen.add(r["id"])

    def finalize(self) -> dict[str, list[dict]]:
        """이번 적재에 없던 행을 폐기로 바꾸고, 이번에 쓰지 않은 행 목록(폐기·통합됨)을 돌려준다."""
        return {k: t.retire_unseen() for k, t in self.tables.items()}

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        for kind, t in self.tables.items():
            rows = sorted(t.rows, key=lambda r: r["id"])
            with (self.dir / KINDS[kind][0]).open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=t.columns(), lineterminator="\n")
                w.writeheader()
                for r in rows:
                    w.writerow({c: r.get(c, "") for c in t.columns()})

    def rows(self, kind: str) -> list[dict]:
        return self.tables[kind].rows
