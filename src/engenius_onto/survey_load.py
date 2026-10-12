"""적재 실행 (python -m engenius_onto load) — 엑셀 → survey 그래프 TTL + 적재 로그 + 툴 통합 검토표 (M3).

산출물 (output/<실행ID>/):
  survey.ttl         survey named graph 내용 (SurveyLoad 포함)
  load_log.json      파일별 건수·제외 행(사유)·경고·행 단위 스키마 검증·통합 후보·레지스트리 요약·SHACL 결과
  tool_review.csv    툴 통합 후보 검토표 — '판정' 열을 채워 apply-review 로 config/tool_aliases.yaml 에 반영 (6.1-5)
레지스트리 CSV(data/<synthetic|real>/registry/)는 제자리에서 갱신한다.
실행 안전 (docs/09 7장): 레지스트리 폴더 잠금 `.load.lock` 을 쥐고 적재한다 (있으면 RegistryBusyError — 자동 해제 없음), 실행 폴더가
이미 있으면(같은 초) 1초씩 밀어 새로 만든다. 약칭 개명(parts.yaml renamed_from)은 쓰기 전에 레지스트리 분야 키를 바꾼다 (docs/09 #25b).
"""

from __future__ import annotations

import csv
import datetime as dt
import json
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path

from engenius_onto.config import (CONFIG_DIR, REAL_CONFIG_DIR, REPO_ROOT, check_aliases_shape, config_where, default_overlay_dir,
                                  installed_version, read_csv_rows, read_yaml)
from engenius_onto.loader import LoadResult, Loader
from engenius_onto.normalize import link_root as _root, merge_keys_from_pairs, nfc_strip, read_merge_pairs
from engenius_onto.rdf_writer import SchemaTerms, SurveyWriter
from engenius_onto.registry import ACTIVE, Registry, registry_lock

DATA_SETS = {  # --data 이름 → (조사 파일 폴더, 레지스트리 폴더)
    "synthetic": (REPO_ROOT / "data" / "synthetic" / "survey", REPO_ROOT / "data" / "synthetic" / "registry"),
    "real": (REPO_ROOT / "data" / "real" / "survey", REPO_ROOT / "data" / "real" / "registry"),
}
REVIEW_COLUMNS = ["툴A_키", "툴A_표기", "툴B_키", "툴B_표기", "유사도", "사유", "판정(통합/별개)", "대표 이름(통합 시)"]
PARTNER_REASON = "연계SW 미해석"      # 검토표 연계 행의 사유 (docs/09 #17) — 툴A = 기존 툴 키(제안 또는 빈칸), 툴B = 해석 못 한 연계 Tool명 키
FORMULA_LEAD = "=+-@\t\r"           # CSV 칸이 이 글자로 시작하면 엑셀이 수식으로 읽는다 (docs/09 #25d, OWASP CSV injection)
ALIASES_HEAD = (  # 오버레이 tool_aliases.yaml 을 처음 만들 때의 머리말 (사내 전용 파일 — 실 툴명이 든다, 밖으로 가져가지 않는다)
    "# 사내 툴 통합 판정 (apply-review 누적, docs/09 C15 오버레이) — config/tool_aliases.yaml 위에 덮인다. git 제외·반출 금지.\n"
    "# aliases: 대표 이름: [변형 표기]  ·  distinct: [[키 A, 키 B]]  ·  merge_pairs: [[키 A, 키 B]] (판정 이력, A 생존)\n"
    "# merge_keys: {키 B: 대표 키} (merge_pairs 에서 저장 때마다 다시 계산 — 손으로 고치려면 merge_pairs 를; 적재기도 merge_pairs 를 우선 읽는다)\n"
    "# labels: {키: 대표 이름} (판정 당시의 대표 키에 둔다 — 그룹 이름은 적재기가 고른다)\n"
    "# partner_missing: [연계 키] (검토표 '연계SW 미해석' 행을 툴A_키 빈칸 + 별개로 판정 = 기존 툴 아님 — 검토표에 다시 올리지 않고 조사 누락 후보로 남긴다)\n")


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


def _csv_safe(v) -> str:
    """CSV 칸이 엑셀에서 수식으로 읽히지 않게 — = + - @ 탭·CR 로 시작하면 앞에 ' (docs/09 #25d; 엑셀 16 에서 그대로 저장돼 돌아오는 것 실측).
    apply-review 는 대표 이름 앞의 이 ' 를 뗀다 (_review_cell)."""
    v = "" if v is None else str(v)
    return "'" + v if v and v[0] in FORMULA_LEAD else v


def write_review(path: Path, res: LoadResult) -> None:
    """툴 통합 검토표 (6.1-5). 통합 후보 행(I23·제조사 접두 보류) 뒤에 연계 행(사유 '연계SW 미해석', docs/09 #17 — Loader._partner_review).
    연계 행: 툴A_키 = 기존 툴 키 제안(비슷한 툴이 뚜렷할 때만, 아니면 빈칸 + 툴A_표기에 비슷한 키 힌트), 툴B_키 = 해석 못 한 연계 키,
    툴B_표기 = 언급 수·파트 (원문 partner_raw 는 쓰지 않는다). 표기 칸은 _csv_safe (엑셀 수식 방지)."""
    with path.open("w", encoding="utf-8-sig", newline="") as f:          # 엑셀에서 바로 열리도록 BOM
        w = csv.writer(f, lineterminator="\n")
        w.writerow(REVIEW_COLUMNS)
        for c in res.merge_candidates:
            w.writerow([_csv_safe(c["a"]), _csv_safe(" / ".join(c["names_a"])), _csv_safe(c["b"]), _csv_safe(" / ".join(c["names_b"])),
                        f"{c['similarity']:.3f}", c["reason"], "", ""])
        for c in getattr(res, "partner_candidates", None) or []:
            if c["a"]:
                shown_a = " / ".join(c["names_a"])
            elif c["hints"]:
                shown_a = "(기존 툴이면 툴A_키에 그 툴 키를 적는다 — 비슷한 키: " + " · ".join(f"{t} {r:.2f}" for t, r in c["hints"]) + ")"
            else:
                shown_a = "(기존 툴이면 툴A_키에 그 툴 키를 적는다 — 아니면 비워 두고 별개)"
            shown_b = f"(연계 Tool명 · 언급 {c['mentions']}회 · 파트 {'·'.join(c['fields']) or '미상'})"
            w.writerow([_csv_safe(c["a"]), _csv_safe(shown_a), _csv_safe(c["b"]), _csv_safe(shown_b),
                        f"{c['similarity']:.3f}" if c["similarity"] is not None else "", PARTNER_REASON, "", ""])


def run_load(data: str = "synthetic", input_dir: Path | None = None, registry_dir: Path | None = None,
             out_root: Path | None = None, now: dt.datetime | None = None, config_dir: Path | None = None,
             shacl: bool = True, save_registry: bool = True, overlay_dir: Path | None = None,
             overlay: bool = True) -> LoadOutput:
    """overlay_dir: 사내 설정 오버레이 폴더 (docs/09 C15). None 이면 --data real 일 때만 data/real/config 를 자동으로 쓴다
    (합성·--input 실행은 섞이지 않게 자동 적용하지 않는다 — --input 에는 --overlay 로 지정). overlay=False 면 자동 적용도 끈다."""
    if input_dir is not None and registry_dir is None:          # docs/09 #9 — 합성 레지스트리를 실데이터로 더럽히지 않게
        raise ValueError("--input 을 쓰면 --registry 도 지정한다 (또는 --data real — data/real/survey + data/real/registry)")
    inp, regdir = DATA_SETS[data]
    inp, regdir = Path(input_dir or inp), Path(registry_dir or regdir)
    now = (now or dt.datetime.now()).astimezone().replace(microsecond=0)
    if overlay_dir is None and overlay and data == "real" and input_dir is None:
        overlay_dir = default_overlay_dir(config_dir)
    loader = Loader(config_dir=config_dir or CONFIG_DIR, overlay_dir=overlay_dir)
    if not inp.is_dir():
        raise FileNotFoundError(f"조사 파일 폴더가 없다: {inp}")
    paths = loader.discover(inp)
    if not paths:
        raise FileNotFoundError(f"조사 파일이 없다: {inp} (*.xlsx)")
    # 동시 적재 잠금 (docs/09 7장) — 레지스트리 읽기부터 저장·산출물 쓰기까지. dry-run(save_registry=False)은 레지스트리를 쓰지 않아 잠그지 않는다
    with registry_lock(regdir) if save_registry else nullcontext():
        out_dir, now = _reserve_run_dir(Path(out_root or REPO_ROOT / "output"), now)   # 같은 초 두 실행 — 1초씩 밀어 새 폴더 (덮어쓰지 않는다)
        try:
            return _run_load(loader, paths, regdir, out_dir, now, data, input_dir, overlay_dir, shacl, save_registry)
        except BaseException:
            _drop_if_empty(out_dir)                           # 실패한 실행의 빈 폴더를 남기지 않는다 (latest_run 은 survey.ttl 있는 폴더만 고르지만)
            raise


RUN_DIR_TRIES = 60    # 같은 초 실행 폴더가 있으면 1초씩 밀어 볼 횟수 (docs/09 7장)


def _reserve_run_dir(root: Path, now: dt.datetime) -> tuple[Path, dt.datetime]:
    """output/<실행ID> 를 새로 만든다 — 이미 있으면(같은 초의 다른 실행) 1초씩 밀어 실행 ID·적재 시각을 함께 바꾼다 (docs/09 7장).
    실행 ID 형식(YYYYMMDDTHHMMSS)은 그대로라 LOAD ID 패턴(#25c)이 깨지지 않는다. (실행 폴더, 민 시각)."""
    for _ in range(RUN_DIR_TRIES):
        out_dir = root / now.strftime("%Y%m%dT%H%M%S")
        try:
            out_dir.mkdir(parents=True)
            return out_dir, now
        except FileExistsError:
            now += dt.timedelta(seconds=1)
    raise RuntimeError(f"실행 폴더를 만들지 못함: {root} 에 같은 시각부터 {RUN_DIR_TRIES}초치 실행 폴더가 이미 있다")


def _drop_if_empty(path: Path) -> None:
    try:
        path.rmdir()                                          # 비어 있을 때만 지워진다
    except OSError:
        pass


def _apply_part_renames(reg: Registry, renames: dict[str, str], warnings: list) -> None:
    """약칭 개명 (docs/09 #25b, parts.yaml renamed_from): 레지스트리 분야 키를 옛 → 새로 — FLD ID 가 그대로라 툴사용 키 (FLD ID, Tool ID)와
    입출력 해시도 그대로다. 옛·새 키 행이 둘 다 있으면(개명 설정 없이 한 번 적재한 뒤) 손대지 않고 경고. 약칭은 설정 값이라 그대로 인용한다."""
    for old, new in sorted(renames.items()):
        status, old_id, new_id = reg.rekey("field", old, new)
        if status == "rekeyed":
            warnings.append(f"파트 약칭 개명 반영: {old} → {new} ({old_id} 유지 — 툴사용·입출력 ID 도 유지)")
        elif status == "conflict":
            warnings.append(f"파트 약칭 개명 보류: '{old}'({old_id})·'{new}'({new_id}) 가 레지스트리에 둘 다 있음 — 개명 전 레지스트리 사본으로 "
                            "되돌린 뒤 다시 적재 (사본이 없으면 README_offline 6장 '파트 약칭을 바꿀 때'; 새 ID 로 계속 가려면 renamed_from 을 지운다)")


def _part_turnover(reg: Registry, loader: Loader, warnings: list) -> None:
    """한 실행에서 FLD 가 새로 생기고 다른 FLD 가 활성 → 폐기면 경고 (docs/09 #25b 5번 휴리스틱) — 약칭을 renamed_from 없이 바꾼 흔적일 수 있다.
    읽지 못한 파일이 있는 실행은 폐기 판정을 하지 않으므로(retired_now 비어 있음) 나오지 않는다. 키가 인명 유사면 FLD ID 만."""
    t = reg.tables["field"]
    if not t.created or not t.retired_now:
        return

    def show(ids: set) -> str:
        rows = sorted((r for r in t.rows if r["id"] in ids), key=lambda r: r["id"])
        return ", ".join(r["id"] if loader._looks_person(r["key"]) else f"{r['key']}({r['id']})" for r in rows)

    warnings.append(f"파트 신규·폐기 동시: 신규 {show(t.created)} · 폐기 {show(t.retired_now)} — 약칭을 바꾼 것이면 개명 전 레지스트리 사본으로 "
                    "되돌리고 config/parts.yaml 새 약칭 항목에 renamed_from: [옛 약칭] 을 적어 다시 적재하면 FLD·툴사용·입출력 ID 가 유지된다 "
                    "(파트를 나누거나 합친 것이면 정상 — docs/10 3장 4)")


def _run_load(loader: Loader, paths: list[Path], regdir: Path, out_dir: Path, now: dt.datetime, data: str,
              input_dir: Path | None, overlay_dir: Path | None, shacl: bool, save_registry: bool) -> LoadOutput:
    """run_load 의 본체 — 잠금·실행 폴더 예약 안쪽."""
    run_id = out_dir.name
    reg = Registry(regdir)
    if save_registry:
        reg.check_writable()                                  # #23 — 적재 전에 확인
    known = {r["key"] for r in reg.rows("tool") if r["status"] == ACTIVE}   # 제조사 접두 흡수의 생존 키 선택 (TOOL ID 유지)
    res = loader.load(paths, known_tool_keys=known)
    res.warnings.extend(reg.notices)                          # #15 — cp949 로 읽은 레지스트리 등
    _apply_part_renames(reg, res.part_renames, res.warnings)  # #25b — 분야 키를 바꾼 뒤 assign (FLD ID 유지)

    terms = SchemaTerms.load()
    writer = SurveyWriter(terms)
    loads = writer.write(res, reg, run_id, now, retire=res.complete)
    _part_turnover(reg, loader, res.warnings)                 # #25b 휴리스틱 — finalize 뒤 (신규·폐기 집합)
    ttl = writer.turtle()
    issues = validate_rows(res, terms)

    ver = installed_version()
    log = {
        "run_id": run_id,
        "loaded_at": now.isoformat(),
        "installed_version": {"commit": ver.commit, "commit_full": ver.commit_full, "number": ver.number,
                              "source": ver.source},         # 설치 판 표식 (값 없음) — 표기는 앞 7자, 전체 해시는 여기에만
        "schema_version": terms.version,
        "rule_version": loader.rules.get("rule_version"),
        "input": data if input_dir is None else "custom",
        "config_overlay": _overlay_record(overlay_dir, loader.overlay_files),      # C15 — 폴더 경로·파일 이름만 (값 없음)
        "files": [{"name": f.name, "index": f.index, "sha256": f.sha256, "field": f.field, "date": f.date, "copy": f.copy,
                   "load_id": loads.get(f.name), "superseded_by": f.superseded_by, "duplicate_of": f.duplicate_of,
                   "unreadable": f.unreadable, **f.stats()} for f in res.files],   # index = 입력 폴더 정렬 순번 (해시 이름 파일 찾기, #8)
        "counts": {"usages": len(res.usages), "io_specs": len(res.ios),
                   "orphan_io_specs": sum(1 for x in res.ios if x.owner is None), "tools": len(res.tools),
                   "fields": len({u.field for u in res.usages if u.field}),
                   "categories": len({x.category for x in res.ios if x.category}),
                   "excluded_rows": len(res.excluded_rows), "warnings": len(res.warnings),
                   "triples": len(writer.g)},
        "excluded_rows": res.excluded_rows,
        "warnings": sorted(res.warnings),
        "issues": res.issues,
        "complete": res.complete,
        "quality": quality_summary(res),
        "schema_issues": issues,
        "tool_merge_candidates": res.merge_candidates,
        "tool_attribute_conflicts": res.attribute_conflicts,
        "unresolved_partners": res.unresolved_partners(),
        "tool_keys": sorted(res.tools),                          # 이번 실행의 툴 키 — apply-review 가 연계 행의 툴A_키를 검사한다 (#17, 사내 전용 파일)
        "registry": {"dir": _rel(regdir), **{k: {s: sum(1 for r in reg.rows(k) if r["status"] == s)
                                                  for s in ("활성", "통합됨", "폐기")} for k in reg.tables},
                     "transitions": reg.transitions()},         # 신규·되살림 건수 (C2)
    }
    if shacl:
        log["shacl"] = run_shacl(ttl)

    if save_registry:
        reg.save()                                            # #23 — 산출물보다 먼저, 원자적으로
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "survey.ttl").write_text(ttl, encoding="utf-8", newline="\n")
    (out_dir / "load_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8",
                                           newline="\n")
    write_review(out_dir / "tool_review.csv", res)
    write_fix_requests(out_dir / "fix_requests", res)
    (out_dir / "diag.txt").write_text(diag_text(out_dir), encoding="utf-8", newline="\n")
    return LoadOutput(run_id, out_dir, res, ttl, log, issues)


def run_dataset(run_dir: Path) -> str:
    """실행 폴더가 어떤 데이터로 만든 것인지 — load_log.json 의 input (real | synthetic | custom), 모르면 '?'."""
    try:
        return json.loads((Path(run_dir) / "load_log.json").read_text(encoding="utf-8")).get("input", "?")
    except (OSError, ValueError):
        return "?"


def latest_run(root: Path, prefer: str | None = "real") -> Path | None:
    """output/ 의 최근 실행 폴더 — 실데이터 실행이 있으면 그중 최근 것을 먼저 (Leo 2026-09-30: 합성 적재가 최근이면 실데이터 지도가 안 떴다)."""
    root = Path(root)
    runs = sorted(p for p in root.glob("*T*") if p.is_dir() and (p / "survey.ttl").is_file()) if root.is_dir() else []
    chosen = [r for r in runs if run_dataset(r) == prefer] if prefer else []
    return (chosen or runs)[-1] if runs else None


def run_shacl(ttl: str) -> dict:
    """Jena SHACL (Fuseki jar) 이 있으면 survey 그래프를 검증한다 — 위반은 경고 보고서 (D4). 없으면 건너뜀.
    SHACL 도구가 실패해도 적재는 계속한다 (docs/09 #22)."""
    from engenius_onto import schema_gen
    from engenius_onto.shacl_check import find_tools, validate

    tools = find_tools()
    if not tools:
        return {"ran": False, "reason": "FUSEKI_HOME/JAVA 없음 — SHACL 검증 건너뜀"}
    try:
        r = validate(schema_gen.GEN_DIR / "engenius_tool.shacl.ttl", ttl, *tools)
    except Exception as e:  # noqa: BLE001 — 도구 오류는 보고만
        return {"ran": False, "reason": f"SHACL 도구 실패 — {type(e).__name__}: {str(e)[:200]}"}
    return {"ran": True, "conforms": r.conforms, "violations": len(r.results),
            "results": [{"focus": f, "path": p, "message": msg} for f, p, msg in r.results]}


FIX_COLUMNS = ["시트", "행", "Tool ID", "열", "적힌 값", "문제", "고치는 법"]
SHEET_SHOWN = {"SW기본정보": "Tool 기본정보", "SW입출력": "Tool 입출력"}


def write_fix_requests(folder: Path, res: LoadResult) -> list[Path]:
    """파일별 수정 요청표 (M3.1, Leo 2026-09-30) — 담당자에게 보낼 사내 전용 파일. 행 순서대로, 인명 의심 칸은 값을 싣지 않는다."""
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill

    by_file: dict[str, list[dict]] = {}
    for i in res.issues:
        by_file.setdefault(i["file"], []).append(i)
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for fname, items in sorted(by_file.items()):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "수정 요청"
        ws.append([f"{fname} — 조사표 수정 요청 {len(items)}건 (En-Genius 툴 조사, 적재 자동 점검)"])
        ws["A1"].font = Font(bold=True, size=12)
        ws.append(FIX_COLUMNS)
        for c in ws[2]:
            c.font, c.fill = Font(bold=True), PatternFill("solid", fgColor="DDE6F0")
        for i in sorted(items, key=lambda x: (x["sheet"], x["row"] or 0)):
            ws.append([SHEET_SHOWN.get(i["sheet"], i["sheet"]), i["row"], _safe_cell(i["tool_id"]), i["column"],
                       _safe_cell(i["value"]), i["kind"], i["hint"]])
        for col, width in zip("ABCDEFG", (14, 6, 12, 22, 28, 22, 60)):
            ws.column_dimensions[col].width = width
        for row in ws.iter_rows(min_row=3):
            row[6].alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "A3"
        path = folder / (Path(fname).stem + "_수정요청.xlsx")
        wb.save(path)
        out.append(path)
    return out


def _safe_cell(v: str) -> str:
    """엑셀이 수식으로 읽지 않게 (= + - @ 로 시작하면 앞에 ' ) — docs/09 #25d."""
    return "'" + v if v and v[0] in "=+-@" else v


QUALITY_SLOTS = {  # M4 계산에 쓰이는 열 → 스키마 열거형 (분포는 이 목록 안의 값만 이름으로, 밖은 건수만 — 값 유출 방지)
    ("SW입출력", "direction", "방향"): "IODirection", ("SW입출력", "transfer_method", "전달 방법"): "TransferMethod",
    ("SW기본정보", "operation_mode", "조작 방식"): "OperationMode", ("SW기본정보", "automation_if", "자동화 인터페이스"): "AutomationInterface",
}


def quality_summary(res: LoadResult) -> dict:
    """1차 적재 검토용 요약 (Leo 2026-09-30) — 파트별 표·계산 열 분포·툴 지표. 셀 값·툴명은 넣지 않는다 (드롭다운 선택지 이름만)."""
    import yaml

    from engenius_onto.config import SCHEMA_FILE

    enums = yaml.safe_load(SCHEMA_FILE.read_text(encoding="utf-8"))["enums"]
    issues_by = {}
    for i in res.issues:
        issues_by.setdefault((i["file"], i["kind"]), 0)
        issues_by[(i["file"], i["kind"])] += 1
    parts = []
    for f in res.loaded_files:
        us = [u for u in res.usages if u.file == f.name]
        xs = [x for x in res.ios if x.file == f.name]
        owners = {id(x.owner) for x in xs if x.owner is not None}
        wrote = [x for x in xs if x.partner_names]
        parts.append({"part": f.field or "(규칙 밖)", "sub_parts": sorted({u.field for u in us} - {f.field or ""}),
                      "usages": len(us), "ios": len(xs), "usages_without_io": sum(1 for u in us if id(u) not in owners),
                      "orphan_ios": sum(1 for x in xs if x.owner is None),
                      "partner_written": len(wrote), "partner_resolved": sum(1 for x in wrote if x.partner_tools),
                      "direction_unknown": sum(1 for x in xs if x.direction_short == "?"),
                      "choice_out": issues_by.get((f.name, "선택지 밖 값"), 0),
                      "required_missing": issues_by.get((f.name, "필수값 누락"), 0),
                      "excluded_rows": f.excluded, "warnings": f.warnings,
                      # 예시와 거의 같은 행 (I15 개정) — 교체돼 빠진 행('예시 행 남음')까지. 277 vs 282 같은 툴사용 수 차이를 파트별로 본다
                      "near_example": issues_by.get((f.name, "예시와 거의 같은 행"), 0) + issues_by.get((f.name, "예시 행 남음"), 0)})
    dist = {}
    for (sheet, slot, label), enum in QUALITY_SLOTS.items():
        allowed = set((enums.get(enum) or {}).get("permissible_values") or {})
        recs = res.ios if sheet == "SW입출력" else res.usages
        c = {"(빈칸)": 0, "(목록 밖)": 0}
        for r in recs:
            v = nfc_strip(r.v.get(slot))
            key = "(빈칸)" if not v else v if v in allowed else "(목록 밖)"
            c[key] = c.get(key, 0) + 1
        dist[label] = c
    tool_parts = {k: {u.field for u in g.usages} for k, g in res.tools.items()}
    unresolved = {k for x in res.ios for k in x.partner_unresolved}
    return {"parts": parts, "distributions": dist,
            "tools": {"total": len(res.tools), "used_by_2plus_parts": sum(1 for s in tool_parts.values() if len(s) >= 2),
                      "used_by_5plus_parts": sum(1 for s in tool_parts.values() if len(s) >= 5),
                      "merge_candidates": len(res.merge_candidates), "unresolved_partner_names": len(unresolved)}}


def diag_text(run_dir: Path) -> str:
    """진단 요약 — 밖으로 가져가도 되는 것만: 경고 종류·열·파일(약칭)별 건수. 셀 값·툴명·데이터명·경로·인명은 넣지 않는다."""
    from collections import Counter

    log = json.loads((Path(run_dir) / "load_log.json").read_text(encoding="utf-8"))
    c = log["counts"]
    iv = log.get("installed_version") or {}
    ver = iv.get("commit", "미상") + (f" (#{iv['number']})" if iv.get("number") is not None else "")
    ov = log.get("config_overlay") or {}
    lines = [f"[diag] 실행 {log['run_id']} · 설치 판 {ver} · 스키마 v{log['schema_version']} · 규칙 {log['rule_version']} · "
             f"완전 적재 {'예' if log.get('complete', True) else '아니오 (읽지 못한 파일 있음)'}",
             "설정 오버레이 사용: " + (f"예 ({', '.join(ov.get('files') or [])})" if ov.get("used") else "아니오"),
             f"파일 {len(log['files'])} (적재 {sum(1 for f in log['files'] if _file_loaded(f))}"
             f" · 재발송 대체 {sum(1 for f in log['files'] if f['superseded'])}"
             f" · 같은 내용 {sum(1 for f in log['files'] if f.get('duplicate_of'))}"
             f" · 읽지 못함 {sum(1 for f in log['files'] if f.get('unreadable'))})",
             f"툴사용 {c['usages']} · 입출력 {c['io_specs']} (고아 {c['orphan_io_specs']}) · 툴 {c['tools']} · 파트 {c['fields']} · "
             f"제외 행 {c['excluded_rows']} · 경고 {c['warnings']}", "", "경고 종류별 건수:"]
    kinds = Counter(w.split(":", 1)[0] for w in log["warnings"])
    lines += [f"  {k}: {n}" for k, n in kinds.most_common()]
    issues = log.get("issues") or []
    if issues:
        lines += ["", "수정 요청 — 문제 · 열별 건수:"]
        by = Counter((i["kind"], SHEET_SHOWN.get(i["sheet"], i["sheet"]), i["column"]) for i in issues)
        lines += [f"  {k} · {s} · {col or '-'}: {n}" for (k, s, col), n in by.most_common()]
        lines += ["", "수정 요청 — 파일(약칭)별 건수:"]
        byf = Counter(i["part"] or "(규칙 밖 파일)" for i in issues)
        lines += [f"  {p}: {n}" for p, n in sorted(byf.items())]
    q = log.get("quality")
    if q:
        pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "-"  # noqa: E731
        lines += ["", "파트별 (적재 파일마다 — 묶음 파일은 나뉜 파트를 괄호로):",
                  "  파트 | 툴사용 | 입출력 | 입출력 없는 툴사용 | 고아 입출력 | 연계 Tool명 적음 | 그중 알아봄 | 방향 못 읽음 | 선택지 밖 | 필수 빈칸 | 제외 행 | 예시 유사"]
        for p in q["parts"]:
            name = p["part"] + (f" ({'·'.join(p['sub_parts'])})" if p["sub_parts"] else "")
            lines.append(f"  {name} | {p['usages']} | {p['ios']} | {p['usages_without_io']} | {p['orphan_ios']} | "
                         f"{p['partner_written']} ({pct(p['partner_written'], p['ios'])}) | {pct(p['partner_resolved'], p['partner_written'])} | "
                         f"{p['direction_unknown']} | {p['choice_out']} | {p['required_missing']} | {p['excluded_rows']} | "
                         f"{p.get('near_example', '-')}")
        lines += ["", "M4 계산에 쓰이는 열 — 선택지별 건수 (목록 밖 값은 건수만):"]
        for label, c in q["distributions"].items():
            lines.append(f"  {label}: " + " · ".join(f"{k} {n}" for k, n in sorted(c.items(), key=lambda kv: -kv[1]) if n))
        t = q["tools"]
        lines += ["", f"툴: 전체 {t['total']} · 2개 파트 이상이 쓰는 툴 {t['used_by_2plus_parts']} · 5개 파트 이상 {t['used_by_5plus_parts']} · "
                      f"이름이 비슷한 통합 후보 쌍 {t['merge_candidates']} · 알아보지 못한 연계 Tool명 {t['unresolved_partner_names']}종"]
    sh = log.get("shacl") or {}
    if sh:
        lines += ["", f"SHACL: {'건너뜀' if not sh.get('ran') else ('적합' if sh.get('conforms') else '위반 ' + str(sh.get('violations')) + '건')}"]
    lines += ["", "※ 이 요약에는 셀 값·툴명·데이터명·경로·인명이 없다 — 밖으로 가져올 수 있다 (docs/08 8장)."]
    return "\n".join(lines) + "\n"


def _file_loaded(f: dict) -> bool:
    """load_log files[] 한 항목이 실제로 적재됐는가 — 재발송 대체·같은 내용·읽지 못함이 아님 (옛 로그에는 duplicate_of 가 없다)."""
    return not f["superseded"] and not f.get("unreadable") and not f.get("duplicate_of")


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return Path(p).name


def _overlay_record(overlay_dir: Path | None, files: list[str]) -> dict:
    """load_log 의 config_overlay — dir 는 저장소 안이면 상대 경로, 밖(--overlay 로 다른 폴더)이면 절대 경로 그대로 + outside_repo: true
    (3D 뷰어 graph_view3d.overlay_dir_of 가 같은 폴더를 다시 찾는다). 경로에 셀 값은 없다."""
    if not overlay_dir:
        return {"used": bool(files), "dir": None, "files": list(files)}
    p = Path(overlay_dir).resolve()
    try:
        return {"used": bool(files), "dir": p.relative_to(REPO_ROOT).as_posix(), "files": list(files)}
    except ValueError:
        return {"used": bool(files), "dir": str(p), "files": list(files), "outside_repo": True}


def summary_lines(out: LoadOutput) -> list[str]:
    c, lg = out.log["counts"], out.log
    lines = [f"[적재] 실행 {out.run_id} → {_rel(out.out_dir)}",
             f"  파일 {len(lg['files'])} (적재 {sum(1 for f in lg['files'] if _file_loaded(f))}) · "
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


def review_target_dir(csv_path: Path) -> Path:
    """apply-review 가 쓸 설정 폴더 (docs/09 C15): 검토표가 나온 실행이 합성이면 config/, 아니면 data/real/config (오버레이).
    실행 폴더를 모르면(검토표를 옮겨 둔 경우) 안전한 쪽인 오버레이."""
    return CONFIG_DIR if run_dataset(Path(csv_path).parent) == "synthetic" else REAL_CONFIG_DIR


@dataclass
class ReviewResult:
    merged: int = 0        # 통합 판정 수 (연계 행 통합 포함)
    kept: int = 0          # 별개 판정 수 (툴A_키가 있는 연계 행 별개 포함)
    undone: int = 0        # 별개 판정으로 되돌린 기존 통합 수
    path: Path | None = None
    encoding: str = "utf-8-sig"
    partner_merged: int = 0     # 그중 연계 행 통합 — 연계 Tool명을 기존 툴에 대응 (#17)
    partner_missing: int = 0    # 연계 행 '툴A_키 빈칸 + 별개' — 기존 툴 아님(조사 누락 확인) → partner_missing
    notes: list[str] = field(default_factory=list)   # CLI 가 '[주의]' 로 보여 줄 것 (값 없음)

    def __iter__(self):    # (통합, 별개, 해제) — 옛 호출부 호환
        return iter((self.merged, self.kept, self.undone))


def _review_cell(row: dict, col: str, n: int, key: bool = False) -> str:
    """검토표 칸 하나 (docs/09 #25d). 키 칸은 앞 ' 하나를 떼고, 대표 이름은 ' 뒤가 수식 글자(= + - @ 탭)일 때만 뗀다 (write_review 의 _csv_safe 되돌림).
    엑셀 오류 값(#NAME?·#REF! 등 — 엑셀이 칸을 수식으로 바꿔 저장한 흔적)이면 ValueError — 설정 파일은 바꾸지 않는다."""
    from engenius_onto.loader import EXCEL_ERRORS

    v = nfc_strip(row.get(col))
    if v.startswith("'") and (key or v[1:2] in tuple(FORMULA_LEAD)):
        v = v[1:].strip()
    if v.upper() in EXCEL_ERRORS:
        raise ValueError(f"검토표 {n}행: '{col}' 이 엑셀 오류 값 {v} — 엑셀이 수식으로 바꾼 흔적. 원래 값을 다시 적는다 (설정 파일은 바꾸지 않음)")
    return v


def _run_tool_keys(csv_path: Path) -> set[str] | None:
    """검토표가 나온 실행의 툴 키 (load_log.json tool_keys) — 없으면(옮긴 검토표·옛 실행) None (#17 연계 행 툴A_키 검사)."""
    try:
        keys = json.loads((Path(csv_path).parent / "load_log.json").read_text(encoding="utf-8")).get("tool_keys")
    except (OSError, ValueError):
        return None
    return {nfc_strip(k) for k in keys} if isinstance(keys, list) else None


def _key_links(cfg: dict, norm) -> dict[str, str]:
    """설정 파일 하나의 통합 링크 (키 → 키): merge_keys + 이름 별칭을 키로 바꾼 것."""
    links = {}
    for rep, variants in (cfg.get("aliases") or {}).items():
        rk = norm.tool_key(rep)
        for v in variants or []:
            vk = norm.tool_key(v)
            if rk and vk and vk != rk:
                links[vk] = rk
    for b, a in (cfg.get("merge_keys") or {}).items():
        if nfc_strip(b) and nfc_strip(a) and nfc_strip(b) != nfc_strip(a):
            links[nfc_strip(b)] = nfc_strip(a)
    return links


def apply_review(csv_path: Path, config_dir: Path | None = None, target_dir: Path | None = None,
                 overlay: bool = False) -> ReviewResult:
    """검토표의 판정을 tool_aliases.yaml 에 누적한다 (6.1-5 HITL, docs/09 #2 A·#14 최소형·#15·C15).

    - 통합: 툴A_키·툴B_키를 판정 이력 merge_pairs 에 [A 키, B 키] 로 더하고 (생존 키 = A 키, TOOL ID 유지), merge_keys 는 저장 때마다
      이력에서 다시 계산한다 (merge_keys_from_pairs — 대표끼리 잇고 깊이 1). 둘이 이미 같은 그룹이면 라벨만 갱신.
      대표 이름(적었을 때만)은 판정 당시의 대표 키에 labels[대표 키] 로 둔다 — 키를 옮기지 않고, 라벨도 옮기거나 승계하지 않는다.
      그룹의 대표 이름은 적재기가 고른다 (loader._alias_map: labels[대표 키] → 이력에서 가장 최근에 A 키로 적힌 키의 라벨 → 키 정렬 순 →
      다수결 표기). 그래서 별개로 되돌리면 각 키는 자기 라벨로 돌아간다.
    - 별개: 직접 쌍([A,B] 또는 [B,A])이 이력에 있으면 지우고(aliases 의 변형 한 개도) 다시 계산 — 제3의 키가 잘못된 대표에 남지 않는다.
      직접 쌍이 없는데 대표가 같으면 오류(간접 사슬 — 사람이 파일을 고친다), 아니면 distinct 만 더한다.
    - overlay=True (CLI --with-public-aliases): 저장소 config/ 의 공개 별칭(aliases)도 사슬 검사에 넣는다 (data/real/config 오버레이에
      쓸 때 — 거기서 이어진 쌍은 오버레이로 못 되돌린다). 독립 설정 사본(--config-dir)에는 기본으로 섞지 않는다.
    - 연계 행 (사유 '연계SW 미해석', docs/09 #17): 통합 = 툴A_키(기존 툴 키 — 검토표 옆 load_log.json 의 tool_keys 에 있어야, 없으면 검사 생략 +
      notes '[주의]')·툴B_키(연계 키)를 위와 같은 merge_pairs [A, B] 로 (A 생존 — 연계 키는 레지스트리 행이 없다). 툴A_키가 비면 오류.
      별개 + 툴A_키 있음 = 위와 같은 distinct (그 제안만 다시 안 나온다), 별개 + 툴A_키 빈칸 = 기존 툴 아님 → partner_missing (검토표에 다시
      안 올리고 CQ09 조사 누락 후보에는 남는다).
    - 칸 검사 (docs/09 #25d·절대 규칙 5): 키 칸 앞 ' 는 떼고, 대표 이름 앞 ' 는 뒤가 수식 글자일 때만 뗀다. 엑셀 오류 값(#NAME? 등)·사람 이름처럼
      보이는 대표 이름은 ValueError (값은 오류 문구에 넣지 않는다 — 오류 값 표기만). 모든 오류는 파일을 쓰기 전에 나므로 설정은 그대로다.
    - CSV 는 utf-8-sig → cp949 순으로 읽는다. 쓰는 곳: target_dir (없으면 config_dir, 없으면 review_target_dir()).
    """
    import yaml

    from engenius_onto.normalize import Normalizer

    target = Path(target_dir or config_dir or review_target_dir(csv_path))
    cfg_path = target / "tool_aliases.yaml"
    if cfg_path.is_file():
        text = cfg_path.read_text(encoding="utf-8-sig")          # 메모장 BOM 이 있어도 머리말('#' 줄)을 잃지 않게
        cfg = check_aliases_shape(config_where(cfg_path), read_yaml(cfg_path))   # 문법·형식 오류는 ConfigError 한 줄 (traceback 없이)
    else:
        target.mkdir(parents=True, exist_ok=True)
        text = ALIASES_HEAD
        cfg = check_aliases_shape(config_where(cfg_path), {})
    aliases = {k: list(v or []) for k, v in cfg["aliases"].items()}
    distinct = [list(p) for p in cfg["distinct"]]
    pairs = read_merge_pairs({k: cfg[k] for k in ("merge_pairs", "merge_keys") if k in cfg["_present"]})   # 키가 없을 때만 승격
    labels = {nfc_strip(k): nfc_strip(v) for k, v in cfg["labels"].items()}
    missing = [k for k in dict.fromkeys(nfc_strip(x) for x in cfg["partner_missing"]) if k]
    # 정규화 규칙은 적재기와 같은 것으로 — 독립 설정 사본이면 그 rules.yaml, 오버레이(data/real/config 또는 --with-public-aliases)에
    # 쓸 때는 저장소 config/ 위에 그 폴더의 rules.yaml 을 덮는다 (오버레이의 tool_token_map 등이 사슬 검사 키에 반영되게)
    own_dir = Path(config_dir) if config_dir else (None if overlay else target)   # CLI --config-dir <독립 사본> 도 그 사본의 규칙으로
    own_rules = own_dir is not None and (own_dir / "rules.yaml").is_file()
    norm = Normalizer.from_config(own_dir if own_rules else None, overlay_dir=None if own_rules or not overlay else target)
    base_links = {}
    if overlay and (CONFIG_DIR / "tool_aliases.yaml").is_file():
        base_links = _key_links(read_yaml(CONFIG_DIR / "tool_aliases.yaml"), norm)

    def links_now() -> dict[str, str]:
        return {**base_links, **_key_links({"aliases": aliases, "merge_keys": merge_keys_from_pairs(pairs)}, norm)}

    rows, enc = read_csv_rows(csv_path)
    res = ReviewResult(path=cfg_path, encoding=enc)
    run_keys = _run_tool_keys(csv_path)
    for n, row in enumerate(rows, start=2):                  # n = 엑셀에서 보이는 행 번호 (1행 = 머리글)
        verdict = nfc_strip(row.get("판정(통합/별개)"))
        if not verdict:
            continue
        a, b = _review_cell(row, "툴A_키", n, key=True), _review_cell(row, "툴B_키", n, key=True)
        if verdict not in ("통합", "별개"):
            raise ValueError(f"판정 값은 '통합' 또는 '별개' 여야 한다: {verdict!r} ({a} / {b})")
        label = _review_cell(row, "대표 이름(통합 시)", n)
        if label and norm.looks_person(label):
            raise ValueError(f"검토표 {n}행: 대표 이름이 사람 이름처럼 보인다 — 툴 이름만 적는다 (설정 파일은 바꾸지 않음)")
        partner = nfc_strip(row.get("사유")) == PARTNER_REASON
        if partner and b and not a:
            if verdict == "별개":                               # 기존 툴 아님 = 조사 누락 확인 (#17)
                if b not in missing:
                    missing.append(b)
                res.partner_missing += 1
                continue
            if verdict == "통합":
                raise ValueError(f"검토표 {n}행: 연계SW 미해석 행의 통합은 툴A_키에 기존 툴 키를 적는다 — 툴B_키 {b}")
        if partner and a and verdict == "통합":
            if run_keys is None:
                note = "[주의] 연계SW 미해석 행의 툴A_키를 확인하지 못함 — 검토표 옆에 load_log.json(tool_keys)이 없다. 툴 키가 맞는지 다시 적재로 확인"
                if note not in res.notes:
                    res.notes.append(note)
            elif a not in run_keys:
                raise ValueError(f"검토표 {n}행: 툴A_키 {a} 는 이 실행의 툴 키가 아니다 — 같은 검토표의 통합 후보 행이나 레지스트리 tools.csv 의 "
                                 "'활성' key 를 적는다 (설정 파일은 바꾸지 않음)")
        if not a or not b:
            raise ValueError(f"검토표 {n}행: 툴A_키·툴B_키가 비어 있다 (판정 {verdict!r}) — 검토표 열을 지우지 않는다")
        if verdict == "통합":
            links = links_now()
            ra, rb = _root(links, a), _root(links, b)
            if partner:
                res.partner_merged += 1
                if b in missing:
                    missing.remove(b)                         # 최신 판정이 이긴다
            pair = sorted([a, b])
            if pair in distinct:
                distinct.remove(pair)                         # 최신 판정이 이긴다
            if ra != rb:
                if [a, b] not in pairs:
                    pairs.append([a, b])
                ra = _root(links_now(), a)
            if label:
                labels[ra] = label                            # 판정 당시의 대표 키에 — 다른 키의 라벨은 건드리지 않는다 (적재기가 그룹 이름을 고른다)
            res.merged += 1
        elif verdict == "별개":
            removed = 0
            for x, y in ((a, b), (b, a)):
                while [x, y] in pairs:                        # 직접 쌍은 어느 순서로든 지운다
                    pairs.remove([x, y])
                    removed += 1
                for rep, variants in aliases.items():
                    rk = norm.tool_key(rep)
                    if rk == y:
                        keep = [v for v in variants if norm.tool_key(v) != x]
                        removed += len(variants) - len(keep)
                        aliases[rep] = keep
            links = links_now()
            if _root(links, a) == _root(links, b):
                where = "config/tool_aliases.yaml(공개 별칭)" if _root(base_links, a) == _root(base_links, b) and base_links else str(cfg_path)
                raise ValueError(f"'{a}' 와 '{b}' 는 다른 키를 거쳐 이어져 있어 별개로 되돌릴 수 없다 — {where} 의 merge_pairs/aliases 를 손으로 고친다 "
                                 f"(대표 '{_root(links, a)}')")
            pair = sorted([a, b])
            if pair not in distinct:
                distinct.append(pair)
            res.kept += 1
            res.undone += removed
        else:
            raise ValueError(f"판정 값은 '통합' 또는 '별개' 여야 한다: {verdict!r} ({a} / {b})")
    merge_keys = merge_keys_from_pairs(pairs)                # 라벨은 적힌 키에 그대로 둔다 (별개로 되돌릴 때 각 키가 자기 이름을 되찾게)
    head = "".join(line + "\n" for line in text.splitlines() if line.startswith("#"))
    body = yaml.safe_dump({"aliases": aliases, "distinct": distinct, "merge_pairs": pairs, "merge_keys": merge_keys, "labels": labels,
                           "partner_missing": sorted(missing)}, allow_unicode=True, sort_keys=True, width=1000)
    cfg_path.write_text(head + body, encoding="utf-8", newline="\n")
    return res
