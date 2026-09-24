"""적재 실행 (python -m engenius_onto load) — 엑셀 → survey 그래프 TTL + 적재 로그 + 툴 통합 검토표 (M3).

산출물 (output/<실행ID>/):
  survey.ttl         survey named graph 내용 (SurveyLoad 포함)
  load_log.json      파일별 건수·제외 행(사유)·경고·행 단위 스키마 검증·통합 후보·레지스트리 요약·SHACL 결과
  tool_review.csv    툴 통합 후보 검토표 — '판정' 열을 채워 apply-review 로 config/tool_aliases.yaml 에 반영 (6.1-5)
레지스트리 CSV(data/<synthetic|real>/registry/)는 제자리에서 갱신한다.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
from dataclasses import dataclass, field
from pathlib import Path

from engenius_onto.config import CONFIG_DIR, REPO_ROOT
from engenius_onto.loader import LoadResult, Loader
from engenius_onto.normalize import nfc_strip
from engenius_onto.rdf_writer import SchemaTerms, SurveyWriter
from engenius_onto.registry import Registry

DATA_SETS = {  # --data 이름 → (조사 파일 폴더, 레지스트리 폴더)
    "synthetic": (REPO_ROOT / "data" / "synthetic" / "survey", REPO_ROOT / "data" / "synthetic" / "registry"),
    "real": (REPO_ROOT / "data" / "real" / "survey", REPO_ROOT / "data" / "real" / "registry"),
}
REVIEW_COLUMNS = ["툴A_키", "툴A_표기", "툴B_키", "툴B_표기", "유사도", "사유", "판정(통합/별개)", "대표 이름(통합 시)"]


@dataclass
class LoadOutput:
    run_id: str
    out_dir: Path
    result: LoadResult
    turtle: str
    log: dict
    schema_issues: list = field(default_factory=list)


def validate_rows(res: LoadResult, terms: SchemaTerms) -> list[dict]:
    """생성 Pydantic 모델로 행 단위 검증 (D4 — 오류 수집에만 쓰고 적재는 막지 않는다)."""
    from pydantic import ValidationError

    from engenius_onto import schema_model as m

    issues = []

    def check(model, data: dict, rec, sheet: str):
        try:
            model(**{k: v for k, v in data.items() if v not in (None, "", [])})
        except ValidationError as e:
            for err in e.errors():
                issues.append({"file": rec.file, "sheet": sheet, "row": rec.row, "key": rec.key,
                               "slot": ".".join(str(x) for x in err["loc"]), "message": err["msg"]})

    for u in res.usages:
        d = dict(u.v)
        d.pop("usage_field", None)
        d.update({f"{s}_raw": r for s, r in u.raw.items()})
        d.update(id=f"egid:{u.node_id}", label=u.key, usage_tool="egid:TOOL", source_row=u.row,
                 usage_field="egid:FLD" if u.field else None)
        check(m.ToolUsage, d, u, "SW기본정보")
    for x in res.ios:
        d = dict(x.v)
        d.pop("io_category", None)
        d.update(id=f"egid:{x.node_id}", label=x.name or None, extensions=x.exts, inhouse_format=x.inhouse,
                 io_owner=f"egid:{x.owner.node_id}" if x.owner else None, io_category="egid:CAT" if x.category else None,
                 partner_tools=[f"egid:{t}" for t in sorted(x.partner_tools)], partner_unresolved=x.partner_unresolved,
                 source_row=x.row)
        check(m.IOSpec, d, x, "SW입출력")
    return issues


def write_review(path: Path, res: LoadResult) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:          # 엑셀에서 바로 열리도록 BOM
        w = csv.writer(f, lineterminator="\n")
        w.writerow(REVIEW_COLUMNS)
        for c in res.merge_candidates:
            w.writerow([c["a"], " / ".join(c["names_a"]), c["b"], " / ".join(c["names_b"]),
                        f"{c['similarity']:.3f}", c["reason"], "", ""])


def run_load(data: str = "synthetic", input_dir: Path | None = None, registry_dir: Path | None = None,
             out_root: Path | None = None, now: dt.datetime | None = None, config_dir: Path | None = None,
             shacl: bool = True, save_registry: bool = True) -> LoadOutput:
    inp, regdir = DATA_SETS[data]
    inp, regdir = Path(input_dir or inp), Path(registry_dir or regdir)
    now = (now or dt.datetime.now()).astimezone().replace(microsecond=0)
    run_id = now.strftime("%Y%m%dT%H%M%S")
    out_dir = Path(out_root or REPO_ROOT / "output") / run_id
    loader = Loader(config_dir=config_dir or CONFIG_DIR)
    paths = loader.discover(inp)
    if not paths:
        raise FileNotFoundError(f"조사 파일이 없다: {inp} ({loader.lcfg['file_pattern']})")
    res = loader.load(paths)

    reg = Registry(regdir)
    terms = SchemaTerms.load()
    writer = SurveyWriter(terms)
    loads = writer.write(res, reg, run_id, now)
    ttl = writer.turtle()
    issues = validate_rows(res, terms)

    unresolved: dict[str, dict] = {}
    for x in res.ios:
        for k in x.partner_unresolved:
            e = unresolved.setdefault(k, {"mentions": 0, "fields": set()})
            e["mentions"] += 1
            e["fields"].add(x.owner.field if x.owner else x.file_field)
    log = {
        "run_id": run_id,
        "loaded_at": now.isoformat(),
        "schema_version": terms.version,
        "rule_version": loader.rules.get("rule_version"),
        "input": data if input_dir is None else "custom",
        "files": [{"name": f.name, "sha256": f.sha256, "field": f.field, "date": f.date,
                   "load_id": loads.get(f.name), "superseded_by": f.superseded_by, **f.stats()} for f in res.files],
        "counts": {"usages": len(res.usages), "io_specs": len(res.ios),
                   "orphan_io_specs": sum(1 for x in res.ios if x.owner is None), "tools": len(res.tools),
                   "fields": len({u.field for u in res.usages if u.field}),
                   "categories": len({x.category for x in res.ios if x.category}),
                   "excluded_rows": len(res.excluded_rows), "warnings": len(res.warnings),
                   "triples": len(writer.g)},
        "excluded_rows": res.excluded_rows,
        "warnings": sorted(res.warnings),
        "schema_issues": issues,
        "tool_merge_candidates": res.merge_candidates,
        "tool_attribute_conflicts": res.attribute_conflicts,
        "unresolved_partners": {k: {"mentions": v["mentions"], "fields": sorted(f for f in v["fields"] if f)}
                                for k, v in sorted(unresolved.items())},
        "registry": {"dir": _rel(regdir), **{k: {s: sum(1 for r in reg.rows(k) if r["status"] == s)
                                                  for s in ("활성", "통합됨", "폐기")} for k in reg.tables}},
    }
    if shacl:
        log["shacl"] = run_shacl(ttl)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "survey.ttl").write_text(ttl, encoding="utf-8", newline="\n")
    (out_dir / "load_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8",
                                           newline="\n")
    write_review(out_dir / "tool_review.csv", res)
    if save_registry:
        reg.save()
    return LoadOutput(run_id, out_dir, res, ttl, log, issues)


def run_shacl(ttl: str) -> dict:
    """Jena SHACL (Fuseki jar) 이 있으면 survey 그래프를 검증한다 — 위반은 경고 보고서 (D4). 없으면 건너뜀."""
    from engenius_onto import schema_gen
    from engenius_onto.shacl_check import find_tools, validate

    tools = find_tools()
    if not tools:
        return {"ran": False, "reason": "FUSEKI_HOME/JAVA 없음 — SHACL 검증 건너뜀"}
    r = validate(schema_gen.GEN_DIR / "engenius_tool.shacl.ttl", ttl, *tools)
    return {"ran": True, "conforms": r.conforms, "violations": len(r.results),
            "results": [{"focus": f, "path": p, "message": msg} for f, p, msg in r.results]}


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return Path(p).name


def summary_lines(out: LoadOutput) -> list[str]:
    c, lg = out.log["counts"], out.log
    lines = [f"[적재] 실행 {out.run_id} → {_rel(out.out_dir)}",
             f"  파일 {len(lg['files'])} (적재 {sum(1 for f in lg['files'] if not f['superseded'])}) · "
             f"툴사용 {c['usages']} · 입출력 {c['io_specs']} (고아 {c['orphan_io_specs']}) · 툴 {c['tools']} · "
             f"분야 {c['fields']} · 분류 {c['categories']}",
             f"  제외 행 {c['excluded_rows']} · 경고 {c['warnings']} · 행 단위 스키마 검증 {len(out.schema_issues)}건 · "
             f"통합 후보 {len(lg['tool_merge_candidates'])} · 조사 누락 후보 {len(lg['unresolved_partners'])}"]
    sh = lg.get("shacl")
    if sh and not sh["ran"]:
        lines.append(f"  SHACL: 건너뜀 — {sh['reason']}")
    elif sh:
        state = "적합" if sh["conforms"] else f"위반 {sh['violations']}건 (경고 보고서 — load_log.json shacl)"
        lines.append(f"  SHACL: {state}")
    return lines


def apply_review(csv_path: Path, config_dir: Path | None = None) -> tuple[int, int]:
    """검토표의 판정을 config/tool_aliases.yaml 에 누적한다 (6.1-5 HITL). (통합 수, 별개 수)."""
    import yaml

    cfg_path = (config_dir or CONFIG_DIR) / "tool_aliases.yaml"
    text = cfg_path.read_text(encoding="utf-8")
    cfg = yaml.safe_load(text) or {}
    aliases = cfg.get("aliases") or {}
    distinct = [list(p) for p in (cfg.get("distinct") or [])]
    merged = kept = 0
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            verdict = nfc_strip(row.get("판정(통합/별개)"))
            if verdict == "통합":
                names_a = [n for n in row["툴A_표기"].split(" / ") if n]
                names_b = [n for n in row["툴B_표기"].split(" / ") if n]
                rep = nfc_strip(row.get("대표 이름(통합 시)")) or names_a[0]
                variants = set(aliases.get(rep) or []) | set(names_a) | set(names_b)
                variants.discard(rep)
                aliases[rep] = sorted(variants)
                merged += 1
            elif verdict == "별개":
                pair = sorted([row["툴A_키"], row["툴B_키"]])
                if pair not in distinct:
                    distinct.append(pair)
                kept += 1
            elif verdict:
                raise ValueError(f"판정 값은 '통합' 또는 '별개' 여야 한다: {verdict!r} ({row['툴A_키']} / {row['툴B_키']})")
    head = "".join(line + "\n" for line in text.splitlines() if line.startswith("#"))
    body = yaml.safe_dump({"aliases": aliases, "distinct": distinct}, allow_unicode=True, sort_keys=True, width=1000)
    cfg_path.write_text(head + body, encoding="utf-8", newline="\n")
    return merged, kept
