"""survey 그래프 작성기 (docs/02 3·4·8장, D4).

Pydantic/linkml 덤퍼 대신 전용 작성기로 쓴다 — 이름 속성(rdfs:label·skos:prefLabel·skos:altLabel)에만 @ko 를 달고,
선택지 밖 값·형식 오류 값도 원문 리터럴 그대로 쓴다 (SHACL 위반 = 경고 보고서, D4). 속성 IRI 는 스키마에서 읽는다
(slot_uri 가 있으면 그것, 없으면 eg:<슬롯 이름>) — 스키마와 작성기가 어긋나지 않게.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, SKOS, XSD

from engenius_onto.config import SCHEMA_FILE
from engenius_onto.loader import IORec, LoadResult, UsageRec
from engenius_onto.normalize import nfc_strip
from engenius_onto.registry import ACTIVE, Registry

LABEL_PROPS = {str(RDFS.label), str(SKOS.prefLabel), str(SKOS.altLabel)}


def _expand(curie: str, prefixes: dict) -> str:
    if ":" in curie and not curie.startswith("http"):
        p, local = curie.split(":", 1)
        if p in prefixes:
            return prefixes[p] + local
    return curie


@dataclass
class SchemaTerms:
    eg: Namespace
    egid: Namespace
    props: dict[str, URIRef]
    classes: dict[str, URIRef]
    version: str

    @classmethod
    def load(cls, schema_file: Path | None = None) -> SchemaTerms:
        s = yaml.safe_load((schema_file or SCHEMA_FILE).read_text(encoding="utf-8"))
        pre = s["prefixes"]
        eg = Namespace(pre["eg"])
        props = {}
        for name, d in (s.get("slots") or {}).items():
            props[name] = URIRef(_expand((d or {}).get("slot_uri", f"eg:{name}"), pre))
        classes = {}
        for cname, c in s["classes"].items():
            classes[cname] = URIRef(_expand(c.get("class_uri", f"eg:{cname}"), pre))
            for name, d in (c.get("attributes") or {}).items():
                props.setdefault(name, URIRef(_expand((d or {}).get("slot_uri", f"eg:{name}"), pre)))
        return cls(eg, Namespace(pre["egid"]), props, classes, str(s.get("version", "")))


def io_hash(parts: list[str], seq: int = 0) -> str:
    """IO ID 해시 (docs/02 4장, D2): 필드마다 NFC+strip, 구분자 \\x1f, sha1 앞 10자리. 완전 중복은 순번 추가."""
    payload = "\x1f".join(unicodedata.normalize("NFC", p or "").strip() for p in parts)
    if seq:
        payload += f"\x1f#{seq}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]


class SurveyWriter:
    def __init__(self, terms: SchemaTerms | None = None):
        self.t = terms or SchemaTerms.load()
        self.g = Graph()
        self.g.bind("eg", self.t.eg)
        self.g.bind("egid", self.t.egid)
        self.g.bind("skos", SKOS)

    # ---- 기본 ------------------------------------------------------------------
    def node(self, local_id: str) -> URIRef:
        return self.t.egid[local_id]

    def add(self, s, slot: str, value, lang_label: bool = False) -> None:
        if value is None or (isinstance(value, str) and value == ""):
            return
        p = self.t.props[slot]
        if isinstance(value, URIRef):
            o = value
        elif isinstance(value, bool):
            o = Literal(value)
        elif isinstance(value, int):
            o = Literal(value, datatype=XSD.integer)
        elif isinstance(value, dt.datetime):
            o = Literal(value.isoformat(timespec="seconds"), datatype=XSD.dateTime)
        elif str(p) in LABEL_PROPS or lang_label:
            o = Literal(str(value), lang="ko")
        else:
            o = Literal(str(value))
        self.g.add((s, p, o))

    def typed(self, local_id: str, cls: str, label: str) -> URIRef:
        s = self.node(local_id)
        self.g.add((s, RDF.type, self.t.classes[cls]))
        self.add(s, "label", label)
        return s

    # ---- 적재 결과 --------------------------------------------------------------
    def write(self, res: LoadResult, reg: Registry, run_id: str, loaded_at: dt.datetime) -> dict:
        """적재 결과를 그래프에 쓰고 {파일명: LOAD ID} 를 돌려준다. 레지스트리 ID 를 배정한다(저장은 호출자)."""
        loads = {}
        for n, f in enumerate(res.loaded_files, start=1):
            lid = f"LOAD-{run_id}-{n:02d}"
            loads[f.name] = lid
            s = self.typed(lid, "SurveyLoad", f.name)
            self.add(s, "run_id", run_id)
            self.add(s, "source_file_name", f.name)
            self.add(s, "source_sha256", f.sha256)
            self.add(s, "loaded_at", loaded_at)
            self.add(s, "row_count", f.usage_rows + f.io_rows)
            self.add(s, "excluded_row_count", f.excluded)
            self.add(s, "warning_count", f.warnings)

        fld = {}
        for u in res.usages:
            if u.field and u.field not in fld:
                fld[u.field] = reg.assign("field", u.field, u.field)
        tool = {k: reg.assign("tool", k, g.pref_label) for k, g in res.tools.items()}
        # 별칭으로 흡수된 옛 툴 키는 통합됨 (docs/01 원칙 9 — 삭제 대신 상태 전이)
        for r in reg.rows("tool"):
            target = res.alias_map.get(r["key"])
            if target and target != r["key"] and target in tool and r["id"] not in reg.tables["tool"].seen:
                reg.mark_merged("tool", r["key"], tool[target])
        cat = {}
        for x in res.ios:
            if x.category and x.category not in cat:
                cat[x.category] = reg.assign("category", x.category, x.category)
        use = {}
        for u in res.usages:
            use[id(u)] = reg.assign("usage", (fld.get(u.field, ""), u.sw_id), f"{u.field} {u.sw_id}")
        unused = reg.finalize()

        for label, fid in fld.items():
            s = self.typed(fid, "ResearchField", label)
            self.add(s, "status", ACTIVE)
        for k, g in res.tools.items():
            s = self.typed(tool[k], "Tool", g.pref_label)
            self.add(s, "pref_label", g.pref_label)
            for a in g.alt_labels:
                self.add(s, "alt_labels", a)
            self.add(s, "vendor", g.majority("reported_vendor"))
            self.add(s, "kind", g.majority("reported_kind"))
            self.add(s, "status", ACTIVE)
        for label, cid in cat.items():
            s = self.typed(cid, "DataCategory", label)
            self.add(s, "status", ACTIVE)
        # 이번 적재에 없는 분야·툴·분류도 상태와 함께 계속 낸다 (D7)
        for kind, cls in (("field", "ResearchField"), ("tool", "Tool"), ("category", "DataCategory")):
            for r in unused[kind]:
                s = self.typed(r["id"], cls, r["label"])
                self.add(s, "status", r["status"])
                if cls == "Tool":
                    self.add(s, "pref_label", r["label"])
                    if r.get("merged_into"):
                        self.add(s, "merged_into", self.node(r["merged_into"]))

        for u in res.usages:
            self._usage(u, use[id(u)], fld, tool, loads)
        for x in res.ios:
            owner_id = use[id(x.owner)] if x.owner else None
            self._io(x, owner_id, cat, tool, loads)
        return loads

    def _usage(self, u: UsageRec, uid: str, fld: dict, tool: dict, loads: dict) -> None:
        v = u.v
        s = self.typed(uid, "ToolUsage", f"{nfc_strip(v.get('reported_tool_name'))} ({u.field} {u.sw_id})")
        u.node_id = uid
        self.add(s, "usage_tool", self.node(tool[u.tool_key]))
        if u.field in fld:
            self.add(s, "usage_field", self.node(fld[u.field]))
        for slot, val in v.items():
            if slot in ("usage_field",):
                continue
            self.add(s, slot, val)
        for slot, raw in u.raw.items():
            self.add(s, f"{slot}_raw", raw)
        self.add(s, "source_row", u.row)
        self.add(s, "loaded_in", self.node(loads[u.file]))

    def _io(self, x: IORec, owner_id: str | None, cat: dict, tool: dict, loads: dict) -> None:
        v = x.v
        owner_part = owner_id or f"orphan:{x.file_field or ''}:{x.sw_id}"
        h = io_hash([owner_part, nfc_strip(v.get("direction")), x.name, cat.get(x.category, x.category),
                     nfc_strip(v.get("extensions_raw")), nfc_strip(v.get("transfer_method")),
                     nfc_strip(v.get("partner_raw"))], x.seq)
        s = self.typed(f"IO-{h}", "IOSpec", x.name)
        x.node_id = f"IO-{h}"
        if owner_id:
            self.add(s, "io_owner", self.node(owner_id))
        if x.category in cat:
            self.add(s, "io_category", self.node(cat[x.category]))
        for slot, val in v.items():
            if slot == "io_category":
                continue
            self.add(s, slot, val)
        for e in x.exts:
            self.add(s, "extensions", e)
        self.add(s, "inhouse_format", x.inhouse)
        for t in sorted(x.partner_tools):
            self.add(s, "partner_tools", self.node(tool[t]))
        for k in x.partner_unresolved:
            self.add(s, "partner_unresolved", k)
        self.add(s, "source_row", x.row)
        self.add(s, "loaded_in", self.node(loads[x.file]))

    def turtle(self) -> str:
        return self.g.serialize(format="turtle")
