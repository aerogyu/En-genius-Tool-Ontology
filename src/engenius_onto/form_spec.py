"""조사 양식 열 명세 — 스키마(form_* 주석) 한 곳에서 읽는다.

적재기는 이 명세로 헤더를 슬롯에 매핑하고, 필수값·선택지·셀 종류를 판단한다. linkml 을 import 하지 않고
스키마 YAML 을 직접 읽는다 (적재 경로를 가볍게 — 생성·검증은 schema_gen 이 linkml 로 한다).
헤더 비교 규칙은 NFKC 후 공백·'*' 무시 (골든 I30). config/header_map.yaml 은 추가 문구만 담는다 — 사내 문구는 오버레이
data/real/config/header_map.yaml 에 더한다 (시트·슬롯별 합집합, 제외 열·인명 열 문구는 매핑 금지 — M3.1 2차 잔여 2026-10-12).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml

from engenius_onto.config import CONFIG_DIR, SCHEMA_FILE, ConfigError, check_header_map_shape, config_where, load_config, read_yaml

SHEET_CLASS = {"SW기본정보": "ToolUsage", "SW입출력": "IOSpec"}
SHEET_ROLE = {"SW기본정보": "usage", "SW입출력": "io"}        # rules.yaml loader.sheets 의 키
NODE_RANGES = {"ResearchField", "DataCategory"}
# 인명 열을 가리키는 헤더 낱말 — header_map 이 어떤 슬롯에도 매핑할 수 없다 (CLAUDE.md 절대 규칙 5; '실무 문의처' 를 '(선택)' 없이 적어도 막는다)
PERSON_HEADER_WORDS = ("문의처", "담당자", "연락처", "작성자")


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


def load_form_spec(schema_file: Path | None = None, config_dir: Path | None = None, overlay_dir: Path | None = None,
                   sheet_names: dict[str, list[str]] | None = None) -> FormSpec:
    """스키마의 양식 열 + header_map 추가 문구 (I30). overlay_dir 의 header_map.yaml(사내 오버레이, data/real/config)이 있으면
    저장소 config/header_map.yaml 과 시트·슬롯별 합집합. sheet_names: 시트 키로 받을 이름 후보 {정규 시트 이름: [실제 이름, ...]} —
    없으면 rules.yaml loader.sheets (+ 오버레이). 검사는 파일마다 따로 해 오류에 실제 경로를 붙인다 (_header_aliases)."""
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

    if sheet_names is None:
        sheets = load_config("rules.yaml", config_dir, overlay_dir)[0]["loader"]["sheets"]
        sheet_names = {s: list(sheets.get(role) or []) for s, role in SHEET_ROLE.items()}
    base = Path(config_dir or CONFIG_DIR) / "header_map.yaml"
    files = [(config_where(base), read_yaml(base))]
    over = Path(overlay_dir) / "header_map.yaml" if overlay_dir else None
    if over is not None and over.is_file():
        files.append((config_where(over), read_yaml(over)))
    return FormSpec(columns, ignored, _header_aliases(files, columns, ignored, sheet_names))


def _header_aliases(files: list[tuple[str, dict]], columns: dict[str, list[Column]], ignored: dict[str, set[str]],
                    sheet_names: dict[str, list[str]]) -> dict[str, dict[str, str]]:
    """header_map 파일들(저장소 → 오버레이 순)의 추가 문구 → {정규 시트: {정규화 문구: 슬롯}} — 순서대로 쌓아 합집합 (config.merge_config 와 같은 뜻).
    ConfigError (파일 경로·시트·슬롯만 — 헤더 문구는 넣지 않는다): 모르는 시트 키(정규 이름 또는 sheet_names 후보만, 공백·'*' 무시) ·
    모르는 슬롯 · 제외 열(실무 문의처·No.·자동 수식 열 — 어느 시트든) 이나 인명 열 낱말(PERSON_HEADER_WORDS)이 든 문구 (절대 규칙 5) ·
    다른 슬롯의 양식 기본 문구를 가로채는 문구 · 같은 문구를 다른 슬롯에 (한 파일 안이든 저장소↔오버레이든)."""
    canon = {norm_header(s): s for s in SHEET_CLASS}
    for s, cands in (sheet_names or {}).items():
        for c in cands or []:
            canon.setdefault(norm_header(c), s)
    excluded = set().union(*ignored.values())
    aliases: dict[str, dict[str, str]] = {}
    origin: dict[tuple[str, str], str] = {}
    for where, raw in files:
        for key, slots in check_header_map_shape(where, raw).items():
            sheet = canon.get(norm_header(key))
            if sheet is None:
                raise ConfigError(f"{where} '{key}': 알 수 없는 시트 — {sorted(SHEET_CLASS)} 또는 rules.yaml loader.sheets 의 이름을 쓴다")
            cols = {c.slot: c for c in columns[sheet]}
            defaults = {norm_header(c.header): c.slot for c in columns[sheet]}
            for slot, phrases in slots.items():
                if slot not in cols:
                    raise ConfigError(f"{where} {key}: 알 수 없는 슬롯 '{slot}' (스키마 양식 열: {sorted(cols)})")
                for p in phrases:
                    nh = norm_header(p)
                    if not nh:
                        continue
                    if nh in excluded or any(w in nh for w in PERSON_HEADER_WORDS):
                        raise ConfigError(f"{where} {key}.{slot}: 제외 열(문의처 등 인명 열·No.·자동 수식 열)의 헤더는 매핑할 수 없다 "
                                          "— 그 열은 읽지 않는다 (CLAUDE.md 절대 규칙 5)")
                    if defaults.get(nh, slot) != slot:
                        raise ConfigError(f"{where} {key}.{slot}: 다른 슬롯 '{defaults[nh]}' 의 양식 기본 문구를 가로챌 수 없다")
                    prev = aliases.get(sheet, {}).get(nh)
                    if prev is not None and prev != slot:
                        raise ConfigError(f"{where} {key}.{slot}: 같은 문구가 이미 슬롯 '{prev}' 에 매핑됨 ({origin[(sheet, nh)]})")
                    aliases.setdefault(sheet, {})[nh] = slot
                    origin.setdefault((sheet, nh), where)
    return aliases


def _col_index(letter, fallback: int) -> tuple:
    if not letter:
        return (1, fallback)
    n = 0
    for ch in str(letter):
        n = n * 26 + (ord(ch.upper()) - 64)
    return (0, n)
