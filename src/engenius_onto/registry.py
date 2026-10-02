"""ID 레지스트리 (docs/02 4장, D3·D7) — FLD·TOOL·USE·CAT ID 를 CSV 로 고정해 재적재해도 같은 ID 를 쓴다.

- 키: 분야 = 이름, 툴 = 정규화 키, 분류 = 이름, 툴사용 = (FLD ID, SW ID 원문) — 원천 파일명은 키에 넣지 않는다 (D3).
- 이번 적재에 없는 분야·툴·분류는 지우지 않고 status=폐기 로 남긴다 — survey 그래프에도 폐기 상태로 계속 낸다 (D7).
  폐기된 ID 는 재발급하지 않는다 (다시 나오면 같은 ID 로 활성 복귀). 통합됨 행도 그 키가 다시 활성 그룹으로 보이면
  같은 ID 로 되살린다 (docs/09 C2 — 별개 판정으로 통합을 되돌린 뒤).
- 통합됨 행은 '본 것' 으로 치지 않는다 — 이번 적재의 미사용 행으로 돌아가 survey 그래프에 통합됨 상태·merged_into 로 계속 쓰인다 (#12).
- 레지스트리는 데이터 옆에 둔다: data/synthetic/registry/, 사내는 data/real/registry/. 합성용을 실데이터에 쓰지 않는다.
- CSV 는 utf-8-sig 로 쓰고, 읽을 때는 utf-8-sig → cp949 순으로 시도한다 (#15 — 엑셀로 저장한 사본 대비). 저장은 늘 utf-8-sig.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from pathlib import Path

from engenius_onto.config import read_csv_rows

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
    created: set = field(default_factory=set)    # 이번 적재에서 새로 발급한 ID
    revived: set = field(default_factory=set)    # 폐기·통합됨에서 활성으로 되살린 ID (C2)

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
        """키에 해당하는 ID (없으면 새 번호). 이번 적재에서 본 것으로 표시하고 활성으로 되돌린다 (폐기·통합됨 모두, C2)."""
        r = self.find(key)
        if r is None:
            _, prefix, width, keys = self.spec
            n = max((int(x["id"].split("-")[1]) for x in self.rows), default=0) + 1
            r = {"id": f"{prefix}-{n:0{width}d}", **dict(zip(keys, key)), "label": label,
                 "status": ACTIVE, "merged_into": ""}
            self.rows.append(r)
            self.created.add(r["id"])
        else:
            r["label"] = label
            if r["status"] in (RETIRED, MERGED):
                r["status"], r["merged_into"] = ACTIVE, ""
                self.revived.add(r["id"])
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
        self.notices: list[str] = []          # 읽기 중 알림 (cp949 로 읽음 등) — run_load 가 경고로 옮긴다
        for kind, t in self.tables.items():
            p = self.dir / KINDS[kind][0]
            if p.is_file():
                t.rows, enc = read_csv_rows(p)
                if enc != "utf-8-sig":
                    self.notices.append(f"레지스트리 CSV 를 {enc} 로 읽음: {p.name} — 저장할 때 utf-8-sig 로 되돌린다 (#15)")
                for r in t.rows:
                    r.setdefault("merged_into", "")

    def assign(self, kind: str, key, label: str) -> str:
        return self.tables[kind].assign(key if isinstance(key, tuple) else (key,), label)

    def id_of(self, kind: str, key) -> str | None:
        r = self.tables[kind].find(key if isinstance(key, tuple) else (key,))
        return r["id"] if r else None

    def mark_merged(self, kind: str, key, into_id: str) -> None:
        """키의 행을 통합됨으로 — seen 에 넣지 않는다 (C2 b): finalize 가 미사용 행으로 돌려주어 그래프에 상태와 함께 쓰인다."""
        r = self.tables[kind].find(key if isinstance(key, tuple) else (key,))
        if r is not None:
            r["status"], r["merged_into"] = MERGED, into_id

    def finalize(self, retire: bool = True) -> dict[str, list[dict]]:
        """이번 적재에 없던 행을 폐기로 바꾸고, 이번에 쓰지 않은 행 목록(폐기·통합됨)을 돌려준다.
        retire=False 면 상태를 바꾸지 않는다 — 읽지 못한 파일이 있는 실행 (docs/09 #7)."""
        if not retire:
            return {k: [r for r in t.rows if r["id"] not in t.seen] for k, t in self.tables.items()}
        return {k: t.retire_unseen() for k, t in self.tables.items()}

    def transitions(self) -> dict[str, dict[str, int]]:
        """종류별 신규·되살림 건수 (load_log 용, 값 없음)."""
        return {k: {"created": len(t.created), "revived": len(t.revived)} for k, t in self.tables.items()}

    def check_writable(self) -> None:
        """적재 전에 레지스트리 폴더에 쓸 수 있는지 확인 (docs/09 #23) — 적재 뒤 저장 실패로 ID 가 어긋나지 않게."""
        self.dir.mkdir(parents=True, exist_ok=True)
        probe = self.dir / ".write_test"
        probe.write_text("", encoding="utf-8")
        probe.unlink()

    def save(self) -> None:
        """표마다 임시 파일에 다 쓴 뒤 바꿔 끼운다 — 도중에 멈춰도 반쪽 CSV 가 남지 않는다 (docs/09 #23)."""
        self.dir.mkdir(parents=True, exist_ok=True)
        done = []
        for kind, t in self.tables.items():
            rows = sorted(t.rows, key=lambda r: r["id"])
            path = self.dir / KINDS[kind][0]
            part = path.with_name(path.name + ".tmp")
            with part.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=t.columns(), lineterminator="\n")
                w.writeheader()
                for r in rows:
                    w.writerow({c: r.get(c, "") for c in t.columns()})
            done.append((part, path))
        for part, path in done:
            os.replace(part, path)

    def rows(self, kind: str) -> list[dict]:
        return self.tables[kind].rows
