"""조사 양식 열 명세 — 스키마(form_* 주석) 한 곳에서 읽는다.

적재기는 이 명세로 헤더를 슬롯에 매핑하고, 필수값·선택지·셀 종류를 판단한다. linkml 을 import 하지 않고
스키마 YAML 을 직접 읽는다 (적재 경로를 가볍게 — 생성·검증은 schema_gen 이 linkml 로 한다).
헤더 비교 규칙은 NFKC 후 공백·'*' 무시 (골든 I30). config/header_map.yaml 은 추가 문구만 담는다.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml

from engenius_onto.config import SCHEMA_FILE, load_yaml

SHEET_CLASS = {"SW기본정보": "ToolUsage", "SW입출력": "IOSpec"}
NODE_RANGES = {"ResearchField", "DataCategory"}


def norm_header(h) -> str:
    return re.sub(r"[\s*]", "", unicodedata.normalize("NFKC", str(h or "")))


@dataclass(frozen=True)
class Column:
    sheet: str
    slot: str
    header: str            # 양식 기본 문구 (경고 메시지에 쓴다)
    required: bool
    kind: str              # text | int | node | enum
    choice_list: str | None


@dataclass
class FormSpec:
    columns: dict[str, list[Column]]         # 시트 → 열
    ignored: dict[str, set[str]]             # 시트 → 의도적 제외 헤더(정규화)
    aliases: dict[str, dict[str, str]]       # 시트 → {정규화 헤더: 슬롯}

    def by_header(self, sheet: str) -> dict[str, Column]:
        cols = {c.slot: c for c in self.columns[sheet]}
        out = {norm_header(c.header): c for c in self.columns[sheet]}
        for h, slot in self.aliases.get(sheet, {}).items():
            out[h] = cols[slot]
        return out


def _ann(d: dict, key: str):
    a = (d or {}).get("annotations") or {}
    v = a.get(key)
    return v.get("value") if isinstance(v, dict) else v


def load_form_spec(schema_file: Path | None = None, config_dir: Path | None = None) -> FormSpec:
    schema = yaml.safe_load((schema_file or SCHEMA_FILE).read_text(encoding="utf-8"))
    slots, classes, enums = schema.get("slots", {}), schema["classes"], schema.get("enums", {})
    columns: dict[str, list[Column]] = {s: [] for s in SHEET_CLASS}
    for sheet, cname in SHEET_CLASS.items():
        c = classes[cname]
        defs = {name: {**(slots.get(name) or {}), **((c.get("slot_usage") or {}).get(name) or {})}
                for name in c.get("slots", [])}
        defs.update(c.get("attributes") or {})
        for name, d in defs.items():
            if _ann(d, "form_sheet") != sheet:
                continue
            rng = d.get("range") or schema.get("default_range", "string")
            if rng in enums:
                kind, lst = "enum", _ann(enums[rng], "form_list")
            elif rng == "integer":
                kind, lst = "int", None
            elif rng in NODE_RANGES:
                kind, lst = "node", _ann(d, "form_list")
            else:
                kind, lst = "text", _ann(d, "form_list")   # 문자열 슬롯도 선택지 검사 (예: reported_domain → 담당부서, v0.3)
            columns[sheet].append(Column(sheet, name, _ann(d, "form_header"), bool(d.get("required")), kind, lst))
        order = {name: i for i, name in enumerate(defs)}
        columns[sheet].sort(key=lambda col: _col_index(_ann(defs[col.slot], "form_column"), order[col.slot]))

    ignored: dict[str, set[str]] = {s: set() for s in SHEET_CLASS}
    for item in str((schema.get("annotations") or {}).get("form_excluded_columns", "")).split(";"):
        parts = [x.strip() for x in item.split("|", 2)]
        if len(parts) == 3 and parts[0] in ignored:
            ignored[parts[0]].add(norm_header(parts[1]))

    hm = load_yaml("header_map.yaml", config_dir)
    aliases: dict[str, dict[str, str]] = {}
    for sheet in SHEET_CLASS:
        known = {c.slot for c in columns[sheet]}
        for slot, phrases in (hm.get(sheet) or {}).items():
            if slot not in known:
                raise ValueError(f"config/header_map.yaml {sheet}: 알 수 없는 슬롯 '{slot}' (스키마 양식 열: {sorted(known)})")
            for p in phrases or []:
                aliases.setdefault(sheet, {})[norm_header(p)] = slot
    return FormSpec(columns, ignored, aliases)


def _col_index(letter, fallback: int) -> tuple:
    if not letter:
        return (1, fallback)
    n = 0
    for ch in str(letter):
        n = n * 26 + (ord(ch.upper()) - 64)
    return (0, n)
