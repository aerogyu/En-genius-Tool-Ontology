"""합성 조사 파일 생성 — python -m engenius_onto synth [--check].

data/synthetic/survey_spec.yaml (선언형 명세) → reference 양식을 채운 분야별 xlsx.
- 열은 위치가 아니라 양식 2행 헤더 이름으로 찾는다 (적재기와 같은 방식, docs/02 5장).
- 템플릿 예시 행(SW기본정보 4행, SW입출력 4~6행)은 그대로 둔다 (P10). io_start_row 로 덮어쓰기 재현.
- 난수 없음. xlsx(zip) 안의 시각·문서 속성을 고정해 같은 명세면 바이트까지 같은 파일이 나온다.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import zipfile
from pathlib import Path

import yaml

from engenius_onto.config import REPO_ROOT

SPEC = REPO_ROOT / "data" / "synthetic" / "survey_spec.yaml"
OUT_DIR = REPO_ROOT / "data" / "synthetic" / "survey"
FIXED_TIME = dt.datetime(2026, 9, 24, 0, 0, 0)
ZIP_TIME = (2026, 9, 24, 0, 0, 0)

USAGE_COLUMNS = {
    "sw_id": "SW ID *", "name": "SW명(정식) *", "version": "버전 *", "vendor": "제조사 / 개발주체 *",
    "kind": "구분 *", "purpose": "용도 대분류 *", "detail": "용도 상세 *", "phase": "주 사용 단계 *",
    "task": "주요 사용 업무 요약 *", "field_cell": "담당 부서 *", "contact": "실무 문의처(선택)",
    "users": "사용 인원수", "freq": "사용 빈도", "license": "라이선스 형태", "qty": "보유 수량",
    "expiry": "만료 시기", "env": "실행 환경 *", "airgap": "폐쇄망 구동 *", "op": "조작 방식 *",
    "batch": "배치/스크립트 실행 *", "auto_if": "자동화 인터페이스 *", "auto_detail": "자동화 상세",
    "headless": "헤드리스 실행", "auth": "인증/로그인 방식", "storage": "산출물 주 저장 위치",
    "vv": "사내 검증 상태 *", "vv_ref": "검증 기준/문서번호", "cert": "감항·인증 업무 사용 *",
    "wish": "자동화 희망 작업 *", "pain": "현재 수작업·애로 구간", "prio": "우선순위 의견",
    "roadmap": "대체/업그레이드 계획", "note": "비고",
}
IO_COLUMNS = {
    "sw_id": "SW ID *", "dir": "방향 *", "name": "데이터/산출물 명칭 *", "cat": "분류 *",
    "ext": "파일 형식/확장자 *", "std": "포맷 표준성", "nature": "데이터 성격 *", "transfer": "전달 방법 *",
    "partner": "연계 SW명", "path": "저장 위치/경로", "grade": "보안등급", "note": "비고",
}
DIRECTION = {"in": "입력(소비)", "out": "출력(생산)"}
USAGE_START_ROW = 5   # 작성안내 ④ '5행부터 작성'
IO_START_ROW = 7      # 예시 4~6행 다음
META_KEYS = {"cases", "blank"}


def load_spec(path: Path = SPEC) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def file_name(spec: dict, field: str) -> str:
    return spec["file_name"].format(field=field)


def _header_columns(ws) -> dict[str, int]:
    return {str(c.value): c.column for c in ws[2] if c.value}


def _fill_rows(ws, rows: list[dict], columns: dict[str, str], defaults: dict, start: int, extra=None) -> None:
    cols = _header_columns(ws)
    missing = [h for h in columns.values() if h not in cols]
    if missing:
        raise ValueError(f"{ws.title}: 양식에 없는 헤더 {missing}")
    r = start
    for row in rows:
        if row.get("blank"):
            r += 1
            continue
        unknown = set(row) - set(columns) - META_KEYS
        if unknown:
            raise ValueError(f"{ws.title}: 명세에 모르는 키 {sorted(unknown)} — {row}")
        values = {**defaults, **(extra(row) if extra else {}), **{k: v for k, v in row.items() if k not in META_KEYS}}
        for key, header in columns.items():
            v = values.get(key)
            if key == "dir" and v is not None:
                v = DIRECTION[v]
            ws.cell(r, cols[header]).value = v
        r += 1


def _add_choice_values(wb, list_name: str, values: list[str]) -> None:
    """선택지 시트의 목록에 값을 덧붙이고, 그 목록을 쓰는 데이터 유효성 범위를 늘린다."""
    from openpyxl.utils import get_column_letter

    ws = wb["선택지"]
    col = next((c.column for c in ws[2] if c.value == list_name), None)
    if col is None:
        raise ValueError(f"선택지 목록 '{list_name}' 이 없다")
    last = max(r for r in range(3, ws.max_row + 2) if ws.cell(r, col).value is not None or r == 3)
    old_end = last
    for v in values:
        last += 1
        ws.cell(last, col).value = v
    letter = get_column_letter(col)
    old_ref = f"선택지!${letter}$3:${letter}${old_end}"
    new_ref = f"선택지!${letter}$3:${letter}${last}"
    for sheet in ("SW기본정보", "SW입출력"):
        for dv in wb[sheet].data_validations.dataValidation:
            if dv.formula1 == old_ref:
                dv.formula1 = new_ref


def build_workbook_bytes(spec: dict, entry: dict) -> bytes:
    import openpyxl

    wb = openpyxl.load_workbook(REPO_ROOT / spec["template"])
    field = entry["field"]
    du, di = spec["defaults"]["usage"], spec["defaults"]["io"]
    _fill_rows(wb["SW기본정보"], entry["usages"], USAGE_COLUMNS, du, USAGE_START_ROW,
               extra=lambda row: {"field_cell": field})
    _fill_rows(wb["SW입출력"], entry["ios"], IO_COLUMNS, di, entry.get("io_start_row", IO_START_ROW))
    if spec.get("extra_categories"):
        _add_choice_values(wb, "온톨로지분류", spec["extra_categories"])

    p = wb.properties
    p.creator = p.lastModifiedBy = "engenius_onto synth (합성 데이터)"
    p.created = p.modified = FIXED_TIME
    p.title = f"합성 조사 — {field}"
    buf = io.BytesIO()
    wb.save(buf)
    return _normalize_zip(buf.getvalue())


def _normalize_zip(data: bytes) -> bytes:
    """zip 항목 시각·속성과 문서 수정 시각을 고정한다.

    openpyxl 은 저장할 때 zip 항목 시각과 docProps/core.xml 의 dcterms:modified 를 현재 시각으로
    덮어쓴다 (properties.modified 를 미리 넣어도 무시됨 — 실측).
    """
    import re

    src = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    fixed = FIXED_TIME.strftime("%Y-%m-%dT%H:%M:%SZ")
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            body = src.read(info.filename)
            if info.filename == "docProps/core.xml":
                body = re.sub(rb"(<dcterms:modified[^>]*>)[^<]*(</dcterms:modified>)",
                              rb"\g<1>" + fixed.encode() + rb"\g<2>", body)
            zi = zipfile.ZipInfo(info.filename, date_time=ZIP_TIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o600 << 16
            dst.writestr(zi, body)
    return out.getvalue()


def outputs(spec: dict | None = None, out_dir: Path = OUT_DIR) -> dict[Path, bytes]:
    spec = spec or load_spec()
    return {out_dir / file_name(spec, e["field"]): build_workbook_bytes(spec, e) for e in spec["files"]}


def run(check: bool = False, out_dir: Path = OUT_DIR) -> int:
    new = outputs(out_dir=out_dir)
    stale = [p for p in out_dir.glob("*.xlsx") if p not in new] if out_dir.exists() else []
    changed = [p for p, b in new.items() if not p.exists() or p.read_bytes() != b]
    rel = lambda p: p.relative_to(REPO_ROOT).as_posix() if p.is_relative_to(REPO_ROOT) else str(p)  # noqa: E731
    if check:
        for p in changed:
            print(f"[불일치] {rel(p)}")
        for p in stale:
            print(f"[잔존] {rel(p)}")
        if changed or stale:
            print("python -m engenius_onto synth 로 다시 생성할 것")
            return 1
        print(f"[OK] 합성 파일 {len(new)}개가 명세와 일치")
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    for p in changed:
        p.write_bytes(new[p])
    for p in stale:
        p.unlink()
    for p, b in sorted(new.items()):
        print(f"{hashlib.sha256(b).hexdigest()[:16]}  {rel(p)}")
    print(f"생성 {len(new)}개 (변경 {len(changed)}, 삭제 {len(stale)})")
    return 0
