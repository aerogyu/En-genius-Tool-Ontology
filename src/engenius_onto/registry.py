"""ID 레지스트리 (docs/02 4장, D3·D7) — FLD·TOOL·USE·CAT ID 를 CSV 로 고정해 재적재해도 같은 ID 를 쓴다.

- 키: 분야 = 파트 약칭 (v0.3 — 파일명의 약칭, docs/10), 툴 = 정규화 키, 분류 = 이름, 툴사용 = (FLD ID, SW ID 원문) — 원천 파일명은 키에 넣지 않는다 (D3).
  약칭 개명(parts.yaml renamed_from)은 분야 행의 키만 바꾼다(rekey) — FLD ID 가 그대로라 툴사용·입출력 ID 도 그대로 (docs/09 #25b).
  파일 간 같은 (파트, Tool ID) 충돌 때만 전용 파일이 아닌 쪽 SW ID 에 '@<파일 약칭 | file-sha256 앞 10자>' 꼬리 (I36 — 이것도 파일명이 아니다).
- 이번 적재에 없는 분야·툴·분류는 지우지 않고 status=폐기 로 남긴다 — survey 그래프에도 폐기 상태로 계속 낸다 (D7).
  폐기된 ID 는 재발급하지 않는다 (다시 나오면 같은 ID 로 활성 복귀). 통합됨 행도 그 키가 다시 활성 그룹으로 보이면
  같은 ID 로 되살린다 (docs/09 C2 — 별개 판정으로 통합을 되돌린 뒤).
- 통합됨 행은 '본 것' 으로 치지 않는다 — 이번 적재의 미사용 행으로 돌아가 survey 그래프에 통합됨 상태·merged_into 로 계속 쓰인다 (#12).
- 레지스트리는 데이터 옆에 둔다: data/synthetic/registry/, 사내는 data/real/registry/. 합성용을 실데이터에 쓰지 않는다.
- CSV 는 utf-8-sig 로 쓰고, 읽을 때는 utf-8-sig → cp949 순으로 시도한다 (#15 — 엑셀로 저장한 사본 대비). 저장은 늘 utf-8-sig.
- 엑셀 손상 검사 (#15 (4), Leo 결정 2026-10-12): 레지스트리 CSV 를 엑셀로 열어 저장하면 Tool ID 칸이 바뀐다 ('3-1'→'03월 01일', '01'→'1').
  툴사용 행의 라벨은 '<파트 이름> <Tool ID>[ (<구분>)]' 이라(rdf_writer) 라벨 끝이 키와 같아야 한다 — 다르고 그 차이가 엑셀 변환으로 정확히
  설명되면(excel_explains) 키를 라벨 끝 값으로 되살리고 알림 '레지스트리 엑셀 손상 복원', 설명되지 않으면 알림 '레지스트리 엑셀 손상 의심' 만
  (ID 만 인용 — 값 없음). 분야·툴·분류 키는 라벨로 대조할 수 없어 엑셀 날짜 모양(DATE_SHAPE)만 '의심' 으로 알린다.
- 동시 적재 잠금 (docs/09 7장): 적재는 레지스트리 폴더에 잠금 파일 `.load.lock` 을 O_CREAT|O_EXCL 로 만들고 끝나면 지운다 (registry_lock).
  이미 있으면 RegistryBusyError — 자동으로 풀지 않는다 (강제 종료로 남은 파일은 사람이 지운다. Windows 의 os.kill(pid, 0) 은 살아 있는지
  보는 것이 아니라 그 프로세스를 끝내므로 pid 로 확인하지 않는다).
"""

from __future__ import annotations

import calendar
import csv
import datetime as dt
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from engenius_onto.config import read_csv_rows

ACTIVE, MERGED, RETIRED = "활성", "통합됨", "폐기"
LOCK_NAME = ".load.lock"         # 레지스트리 폴더의 동시 적재 잠금 파일 (.gitignore — 합성 레지스트리는 git 추적이라)


class RegistryBusyError(RuntimeError):
    """레지스트리를 다른 적재가 쓰는 중 (잠금 파일이 있다) — CLI 는 '[NG] 레지스트리 사용 중: …' 한 줄, rc 2."""


@contextmanager
def registry_lock(directory: Path):
    """레지스트리 폴더 잠금 (docs/09 7장) — 읽기부터 저장·산출물 쓰기까지 한 적재만. 잠금 파일에는 pid·시작 시각만 (인명·PC 이름 없음).
    이미 잠겨 있으면 RegistryBusyError (그 파일 내용 앞 80자를 붙인다). 끝나면(예외·Ctrl+C 포함) 지운다 — 창을 강제로 닫으면 남을 수 있다."""
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    path = d / LOCK_NAME
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            info = path.read_text(encoding="utf-8", errors="replace").strip()[:80]
        except OSError:
            info = ""
        raise RegistryBusyError(
            f"다른 적재가 이 레지스트리를 쓰는 중이다 — 잠금 파일 {path}" + (f" ({info})" if info else "") +
            ". 다른 적재 창이 열려 있으면 그 적재가 끝난 뒤 다시 실행한다. 열린 적재가 없으면 (적재 창을 강제로 닫았거나 PC 가 꺼져 남은 파일) "
            "그 잠금 파일을 지우고 다시 실행한다") from None
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(f"pid={os.getpid()} started={dt.datetime.now().astimezone().replace(microsecond=0).isoformat()}\n")
        yield path
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
# 엑셀이 날짜로 바꿔 저장한 모양 (#15 (4)) — '03월 01일'(ko-KR, 실측) · '2026-03-01[ 00:00[:00]]' · '3/1[/2026]' · '1-Mar'
DATE_SHAPE = re.compile(r"\d{1,2}월\s?\d{1,2}일|\d{4}-\d{2}-\d{2}(?:\s\d{1,2}:\d{2}(?::\d{2})?)?|\d{1,2}/\d{1,2}(?:/\d{2,4})?|\d{1,2}-[A-Za-z]{3}")


def _month_day(t: str) -> tuple[int, int] | None:
    """Tool ID 원문이 엑셀이 날짜로 읽는 모양이면 (월, 일) — 'M-D'·'M/D'(숫자), 'MON-D'(영문 월 약어 — 약칭이 JAN~DEC 와 같을 때, 추정)."""
    m = re.fullmatch(r"(\d{1,2})[-/](\d{1,2})", t) or re.fullmatch(r"([A-Za-z]{3})[-/ ](\d{1,2})", t)
    if not m:
        return None
    mon = m.group(1)
    mo = int(mon) if mon.isdigit() else (MONTHS.index(mon.upper()) + 1 if mon.upper() in MONTHS else 0)
    d = int(m.group(2))
    return (mo, d) if 1 <= mo <= 12 and 1 <= d <= calendar.monthrange(2024, mo)[1] else None


def excel_explains(original: str, current: str) -> bool:
    """current 가 Tool ID 원문 original 을 엑셀이 열어 CSV 로 다시 저장한 모양인가 (#15 (4)) — 정확히 설명될 때만 True.
    ① 숫자만: 앞 0 소실 ('01'→'1', '0012'→'12') ② 소수: 끝 0 소실 ('1.50'→'1.5') ③ 월-일: '03월 01일'(ko-KR 실측) ·
    'M월 D일' · 'D-Mon'·'DD-Mon'(en-US) · 'YYYY-MM-DD[ 00:00[:00]]' · 'M/D/YYYY'·'YYYY/M/D' (연도는 아무 값 — 엑셀이 저장한 해)."""
    if not original or original == current:
        return False
    if re.fullmatch(r"\d+", original):
        return current == str(int(original))
    if re.fullmatch(r"\d+\.\d+", original):
        f = repr(float(original))
        return current == (f[:-2] if f.endswith(".0") else f)
    md = _month_day(original)
    if md is None:
        return False
    mo, d = md
    mon = MONTHS[mo - 1].title()
    if current in {f"{mo:02d}월 {d:02d}일", f"{mo}월 {d}일", f"{d}-{mon}", f"{d:02d}-{mon}"}:
        return True
    return bool(re.fullmatch(rf"\d{{4}}-{mo:02d}-{d:02d}(?:\s0?0:00(?::00)?)?|0?{mo}/0?{d}/\d{{2,4}}|\d{{4}}/0?{mo}/0?{d}", current))


def _label_ok(label: str, key: str) -> bool:
    """툴사용 행 라벨이 키와 맞는가 — '<파트 이름> <Tool ID>' 또는 구분 꼬리가 있으면 키 '<Tool ID>@<구분>' ↔ 라벨 '… <Tool ID> (<구분>)' (I36)."""
    if label.endswith(" " + key) or label == key:
        return True
    sw, sep, tag = key.rpartition("@")
    return bool(sep) and label.endswith(f" {sw} ({tag})")

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
    retired_now: set = field(default_factory=set)   # 이번 적재에서 활성 → 폐기로 바꾼 ID (#25b '파트 신규·폐기 동시', C2 (c))

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

    def rekey(self, old: tuple, new: tuple) -> tuple[str, str | None, str | None]:
        """키만 바꾼다 (#25b 약칭 개명 — ID·상태 유지, 라벨은 뒤의 assign 이 갱신). (결과, 옛 키 행 ID, 새 키 행 ID):
        'rekeyed' — 옛 키 행만 있어 키를 새 키로 바꿈 · 'conflict' — 둘 다 있어 손대지 않음 · 'absent' — 옛 키 행이 없음 (이미 바꿨거나 처음)."""
        r_old, r_new = self.find(old), self.find(new)
        if r_old is None:
            return "absent", None, r_new["id"] if r_new else None
        if r_new is not None:
            return "conflict", r_old["id"], r_new["id"]
        r_old.update(dict(zip(self.spec[3], new)))
        return "rekeyed", r_old["id"], r_old["id"]

    def retire_unseen(self) -> list[dict]:
        out = []
        for r in self.rows:
            if r["id"] not in self.seen and r["status"] == ACTIVE:
                r["status"] = RETIRED
                self.retired_now.add(r["id"])
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
        self._check_excel_damage()

    def _check_excel_damage(self) -> None:
        """레지스트리 CSV 의 엑셀 손상 (#15 (4), Leo 결정 2026-10-12 — 설명되는 행만 자동 복원 + 알림, 나머지는 알림만, ID 만 인용).

        툴사용: 라벨 끝이 키와 맞지 않으면(_label_ok) 라벨의 공백 뒤 꼬리 가운데 엑셀 변환으로 지금 키가 정확히 설명되는 것(excel_explains)이
        하나뿐이고 같은 (분야 ID, 그 값) 행이 따로 없을 때만 키를 그 값으로 되살린다 — 손상된 채 적재하면 그 툴사용·입출력이 새 ID 를 받고 옛 ID 가
        폐기되기 때문 (저장은 적재 끝의 save). 분야·툴·분류: 키가 엑셀 날짜 모양(DATE_SHAPE)이면 의심 알림만."""
        def ids(rows: list[str]) -> str:
            return ", ".join(rows[:5]) + (f" 외 {len(rows) - 5}" if len(rows) > 5 else "")

        t = self.tables["usage"]
        keys = {(r.get("field_id", ""), r.get("source_key", "")) for r in t.rows}
        restored, suspect = [], []
        for r in t.rows:
            key, label = r.get("source_key", ""), r.get("label", "")
            if _label_ok(label, key):
                continue
            tails = {label[i + 1:] for i, ch in enumerate(label) if ch == " "}
            orig = sorted(x for x in tails if excel_explains(x, key))
            fk = r.get("field_id", "")
            if len(orig) == 1 and (fk, orig[0]) not in keys:
                keys.discard((fk, key))
                keys.add((fk, orig[0]))
                r["source_key"] = orig[0]
                restored.append(r["id"])
            else:
                suspect.append(r["id"])
        name = KINDS["usage"][0]
        if restored:
            self.notices.append(f"레지스트리 엑셀 손상 복원: {name} {len(restored)}행 ({ids(restored)}) — 엑셀이 바꾼 Tool ID 칸('3-1'→'03월 01일', "
                                "'01'→'1')을 라벨 끝 값으로 되살림, 이번 적재가 고쳐 저장한다 (레지스트리 CSV 는 엑셀로 저장하지 않는다 — docs/09 #15)")
        if suspect:
            self.notices.append(f"레지스트리 엑셀 손상 의심: {name} {len(suspect)}행 ({ids(suspect)}) — Tool ID 칸이 라벨 끝과 다르다 (엑셀 저장·손 편집 흔적). "
                                "이대로면 그 툴사용과 입출력이 새 ID 를 받고 옛 ID 는 폐기된다 — 레지스트리를 백업에서 되돌리거나 Tool ID 칸을 라벨 끝 값으로 "
                                "고친 뒤 다시 적재 (레지스트리 CSV 는 엑셀로 저장하지 않는다)")
        for kind in ("field", "tool", "category"):
            fname, _p, _w, cols = KINDS[kind]
            bad = [r["id"] for r in self.tables[kind].rows if any(DATE_SHAPE.fullmatch(r.get(c, "") or "") for c in cols)]
            if bad:
                self.notices.append(f"레지스트리 엑셀 손상 의심: {fname} {len(bad)}행 ({ids(bad)}) — 키 칸이 엑셀 날짜 모양이다 "
                                    "(레지스트리 CSV 는 엑셀로 저장하지 않는다 — 백업에서 되돌린 뒤 다시 적재)")

    def assign(self, kind: str, key, label: str) -> str:
        return self.tables[kind].assign(key if isinstance(key, tuple) else (key,), label)

    def rekey(self, kind: str, old, new) -> tuple[str, str | None, str | None]:
        """Table.rekey — 키가 열 하나인 종류는 문자열로 넘겨도 된다 (분야 약칭 개명, #25b)."""
        return self.tables[kind].rekey(old if isinstance(old, tuple) else (old,), new if isinstance(new, tuple) else (new,))

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
