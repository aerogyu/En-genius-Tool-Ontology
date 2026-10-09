"""M2 독립 참조 계산 — docs/02 4~7장 규칙을 합성 명세(survey_spec.yaml)에 그대로 적용한다.

목적: 골든 기대값(expected.yaml)을 사람이 손으로 세지 않고 재현 가능하게 만들고, M3·M4 구현
(적재기·SPARQL 규칙)과 **서로 독립인** 두 번째 구현으로 대조하는 것. 그래서 src/ 코드를 import 하지 않는다.
docs/02 가 정하지 않은 세부는 expected.yaml 'interpretations' (I1~) 에 적은 해석을 따른다 — 코드 주석의 [I번호].
명세 입력이므로 엑셀 파일 층(예시 행 위치, 헤더 셀)은 명세의 파일 설정(header_overrides 등)으로 재현한다.
"""

from __future__ import annotations

import datetime as dt
import difflib
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

import openpyxl

# docs/02 9장 rules.yaml 예시값 그대로
MANUAL_TRANSFER = {"메일·수기 전달"}
NOTE_KEYWORDS = ("수기", "수작업", "손으로", "복사", "재입력")
AUTO_OPS = {"CLI 지원", "GUI+CLI"}
NON_AUTO_IF = {"없음", "모름"}
AIRGAP_EXCLUDED = {"불가"}
GENERIC_EXT = {"xlsx", "xls", "csv", "txt", "pdf", "docx", "pptx", "hwp"}
FREQ_RANK = {"매일": 4, "주 1회 이상": 3, "월 1회 이상": 2, "분기 이하": 1}
PRIO_RANK = {"상": 3, "중": 2, "하": 1}
GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "제외": 3}
FUZZY = 0.85
HUB_TOP_N = 10
CONTAIN_MIN = 3                                                                        # [I23] 포함 후보는 짧은 키 3자 이상 (docs/09 #16)
TOKEN_MAP = {"c++": "cpp", "c#": "csharp", "f#": "fsharp"}                              # [I2] rules.yaml tool_token_map
GENERIC_NAMES = ["자체개발", "자체 개발", "자체제작", "자체 제작", "사내툴", "사내 툴", "사내개발", "사내 개발", "인하우스",
                 "in-house", "inhouse", "custom", "매크로", "macro"]                     # [I34] rules.yaml generic_tool_names
GENERIC_PREFIX = "미상:"
IO_ID_FILL_DOWN = True                                                                  # [I22] rules.yaml loader.io_id_fill_down (2026-10-09)

EXT_ALIAS = {"step": "stp", "iges": "igs", "jpeg": "jpg", "tif": "tiff", "yml": "yaml",
             "엑셀": "xlsx", "워드": "docx", "파워포인트": "pptx", "한글": "hwp", "텍스트": "txt"}
EMPTY_TOKENS = {"", "없음", "모름", "-", "—", "–", "n/a", "na", "해당없음", "해당 없음"}   # [I16]
EXT_OK = re.compile(r"^[a-z0-9_+\-]+(\.[a-z0-9_+\-]+)*$")
VERSION_TOKEN = re.compile(r"^(v\d+(\.\d+)*|\d{4}r\d+|r\d+[a-z]?|sp\d+|\d+(\.\d+)+|(19|20)\d{2})$")   # [I2] 연도만 있는 토큰 포함 (docs/09 #16 A)
# 'ㆍ'(U+318D) 는 NFKC 에서 U+119E 로 바뀐다 — 정규화 뒤에 나누므로 둘 다 구분자로 둔다
EXT_SEP = re.compile("[/,;·ㆍᆞ・\\s]+")
PARTNER_SEP = re.compile("[,;/·ㆍᆞ・\\n]+")                                            # [I17]
PERSON_PATTERN = re.compile(r"(책임|선임|수석|연구원|과장|차장|부장|대리|사원|팀장)\s*\(\s*내선")   # [D6]

USAGE_KEYS = {  # 명세 키 → (양식 헤더, 선택지 목록, 필수)
    "sw_id": ("SW ID *", None, True), "name": ("SW명(정식) *", None, True), "version": ("버전 *", None, True),
    "vendor": ("제조사 / 개발주체 *", None, True), "kind": ("구분 *", "구분", True),
    "purpose": ("용도 대분류 *", "용도대분류", True), "detail": ("용도 상세 *", None, True),
    "phase": ("주 사용 단계 *", "사용단계", True), "task": ("주요 사용 업무 요약 *", None, True),
    "field_cell": ("담당 부서 *", "담당부서", True), "users": ("사용 인원수", None, False),
    "freq": ("사용 빈도", "사용빈도", False), "license": ("라이선스 형태", "라이선스형태", False),
    "qty": ("보유 수량", None, False), "expiry": ("만료 시기", None, False),
    "env": ("실행 환경 *", "실행환경", True), "airgap": ("폐쇄망 구동 *", "폐쇄망구동", True),
    "op": ("조작 방식 *", "조작방식", True), "batch": ("배치/스크립트 실행 *", "배치실행", True),
    "auto_if": ("자동화 인터페이스 *", "자동화IF", True), "auto_detail": ("자동화 상세", None, False),
    "headless": ("헤드리스 실행", "가능불가모름", False), "auth": ("인증/로그인 방식", "인증방식", False),
    "storage": ("산출물 주 저장 위치", "저장위치", False), "vv": ("사내 검증 상태 *", "검증상태", True),
    "vv_ref": ("검증 기준/문서번호", None, False), "cert": ("감항·인증 업무 사용 *", "예아니오모름", True),
    "wish": ("자동화 희망 작업 *", None, True), "pain": ("현재 수작업·애로 구간", None, False),
    "prio": ("우선순위 의견", "우선순위", False), "roadmap": ("대체/업그레이드 계획", None, False),
    "note": ("비고", None, False),
}
IO_KEYS = {
    "sw_id": ("SW ID *", None, True), "dir": ("방향 *", "방향", True), "name": ("데이터/산출물 명칭 *", None, True),
    "cat": ("분류 *", "온톨로지분류", True), "ext": ("파일 형식/확장자 *", None, True),
    "std": ("포맷 표준성", "포맷표준성", False), "nature": ("데이터 성격 *", "데이터성격", True),
    "transfer": ("전달 방법 *", "전달방법", True), "partner": ("연계 SW명", None, False),
    "path": ("저장 위치/경로", None, False), "grade": ("보안등급", "보안등급", False), "note": ("비고", None, False),
}
INT_SLOTS = {"users", "qty"}
FREE_TEXT = {"detail", "task", "auto_detail", "wish", "pain", "roadmap", "note"}   # [D6] 인명 패턴 검사 대상
DIRECTION = {"in": "입력(소비)", "out": "출력(생산)"}
IGNORED_HEADERS = {"SW명(자동)", "실무 문의처(선택)"}                               # 의도적 제외 열 (경고 아님)


# --------------------------------------------------------------------------- 정규화 (docs/02 6장)
def _nfkc(s) -> str:
    return unicodedata.normalize("NFKC", str(s or ""))


def _base(s: str) -> str:
    return re.sub(r"\([^)]*\)", " ", _nfkc(s).lower())


def _alnum(s: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", s)


def norm_header(h: str) -> str:
    return re.sub(r"[\s*]", "", _nfkc(h))


def vendor_key(v: str | None) -> str:
    return _alnum(_base(v or ""))


def _name_key(name: str) -> str:
    tokens = [TOKEN_MAP.get(t, t) for t in _base(name).split() if not VERSION_TOKEN.match(t)]
    return _alnum("".join(tokens))


GENERIC_KEYS = {_name_key(n) for n in GENERIC_NAMES} - {""}


def tool_key(name: str, vendor: str | None = None) -> str:
    """NFKC → 소문자 → 괄호 주석 제거 → 버전 토큰 제거 → 토큰 치환(C++→cpp, [I2]) → 영숫자·한글만 → 제조사 접두 제거 (6.1-2).
    [I14] 떼어낸 나머지가 비면 떼지 않는다 (툴명 = 제조사명, 예: Tecplot). [I34] 제조사가 범용 이름('자체개발')이면 떼지 않는다."""
    key = _name_key(name)
    v = vendor_key(vendor)
    if v and v not in GENERIC_KEYS and key.startswith(v) and len(key) > len(v):
        key = key[len(v):]
    return key


def is_generic_key(key: str) -> bool:
    """[I34] 빈 키거나 범용 이름('자체개발' 등)의 키 — 통합하지 않고 행별 '미상:<파트>/<SW ID>' 키로 둔다."""
    return key == "" or key in GENERIC_KEYS


def survey_vendors(usages) -> list[str]:
    """[I1] 접두 흡수·연계 SW명 해석에 쓰는 조사 제조사 키 — 범용 제조사('자체개발' 등, I34)는 뺀다. 긴 것부터."""
    return sorted({vendor_key(u.vendor) for u in usages if vendor_key(u.vendor) and not is_generic_key(vendor_key(u.vendor))},
                  key=len, reverse=True)


def _id_norm(s) -> str:
    """[#18] SW ID 비교 키 — 전각·대소문자·공백·보이지 않는 문자, 하이픈 뒤 숫자 앞 0 은 같은 ID (적재기와 따로 구현)."""
    k = unicodedata.normalize("NFKC", str(s or ""))
    k = "".join(ch for ch in k if ch not in "​‌‍⁠﻿" and not ch.isspace()).upper()
    return re.sub(r"-0+(\d)", r"-\1", k)


def split_partners(raw) -> list[str]:
    """[I17] NFKC 후 , ; / · ㆍ ・ 줄바꿈으로 나눈다. [I16] 빈 값 토큰·정규화 키가 빈 조각은 버린다. [I34] 범용 이름 조각도 버린다."""
    out = []
    for p in PARTNER_SEP.split(_nfkc(raw)):
        p = p.strip()
        if p.lower() in EMPTY_TOKENS or is_generic_key(tool_key(p)):
            continue
        out.append(p)
    return out


def normalize_extensions(raw) -> tuple[list[str], bool, list[str]]:
    """(정규화 확장자, 사내 표기, 매핑 못 한 토큰) — docs/02 6.2 + [I12] [I16].
    셀 전체가 빈 값 토큰이면 빈 목록. 괄호 주석은 떼고(안에 '사내' 가 있으면 사내 표기), 토큰 '사내' 도 사내 표기."""
    s = _nfkc(raw).lower().strip()
    if s in EMPTY_TOKENS:
        return [], False, []
    inhouse = False
    for m in re.findall(r"\(([^)]*)\)", s):
        inhouse |= "사내" in m
    s = re.sub(r"\([^)]*\)", " ", s)
    out, bad = [], []
    for tok in EXT_SEP.split(s):
        tok = tok.strip().lstrip(".*").strip()
        if tok == "사내":
            inhouse = True
            continue
        if tok in EMPTY_TOKENS:
            continue
        tok = EXT_ALIAS.get(tok, tok)
        (out if EXT_OK.match(tok) else bad).append(tok)
    return sorted(set(out)), inhouse, bad


def template_choices(template: Path) -> dict[str, list[str]]:
    wb = openpyxl.load_workbook(template, read_only=True, data_only=True)
    rows = list(wb["선택지"].iter_rows(min_row=2, values_only=True))
    wb.close()
    out = {}
    for col in zip(*rows):
        vals = [str(v) for v in col if v is not None]
        if vals:
            out[vals[0]] = vals[1:]
    return out


def template_example_rows(template: Path) -> dict[str, list[tuple]]:
    """예시 행 내용 (적재 열만 — B 수식·K 문의처 제외) [I15]."""
    wb = openpyxl.load_workbook(template, data_only=True)
    out = {}
    for sheet, rows, keys in (("SW기본정보", (4,), USAGE_KEYS), ("SW입출력", (4, 5, 6), IO_KEYS)):
        ws = wb[sheet]
        cols = {str(c.value): c.column for c in ws[2] if c.value}
        out[sheet] = [tuple(ws.cell(r, cols[h]).value for h, _, _ in keys.values() if h in cols) for r in rows]
    return out


# --------------------------------------------------------------------------- 모델
@dataclass
class Usage:
    file: str
    file_field: str
    field: str
    sw_id: str
    name: str
    vendor: str
    kind: str
    op: str
    auto_if: str
    airgap: str
    freq: str
    users: object
    prio: str
    tool: str = ""

    @property
    def key(self) -> str:
        return f"{self.field}/{self.sw_id}"

    @property
    def automatable(self) -> bool:
        op, aif = (self.op or "").strip(), (self.auto_if or "").strip()
        return op in AUTO_OPS or bool(aif and aif not in NON_AUTO_IF)

    def sort_key(self):
        users = self.users if isinstance(self.users, int) else -1   # [I6]
        return (FREQ_RANK.get(self.freq, 0), users, PRIO_RANK.get(self.prio, 0))


@dataclass
class IO:
    file: str
    file_field: str
    sw_id: str
    direction: str
    name: str
    cat: str
    ext_raw: str
    exts: list
    inhouse: bool
    transfer: str
    partner_raw: str
    note: str
    owner: Usage | None
    partner_tools: set = field(default_factory=set)
    partner_unresolved: list = field(default_factory=list)
    suffix: str = ""

    @property
    def base_key(self) -> str:
        owner = self.owner.key if self.owner else f"{self.file_field}/{self.sw_id}(고아)"
        return f"{owner}/{self.direction}/{self.name}"

    @property
    def key(self) -> str:
        return self.base_key + self.suffix


@dataclass
class Feed:
    o: IO
    i: IO
    matched: list
    confidence: str
    declared: bool
    manual: bool
    manual_basis: str | None
    grade: str | None


# --------------------------------------------------------------------------- 셀 값 규칙 (docs/02 5-2)
def cell_to_text(key: str, value, where: str, warnings: list) -> object:
    """문자열 슬롯의 숫자·날짜 셀 변환 [D5]. 정수 슬롯(users, qty)은 그대로 두되 빈 값 토큰('NA'·'-')은 빈칸 [I16, docs/09 #21]."""
    if value is None:
        return None
    if key in INT_SLOTS:
        return None if isinstance(value, str) and value.strip().lower() in EMPTY_TOKENS else value
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)                                   # 정수: 경고 없음 (선행 0 소실은 탐지 불가)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        warnings.append(f"엑셀 숫자 변환 가능성: {where} {USAGE_KEYS.get(key, IO_KEYS.get(key))[0]} = {value}")
        return repr(value)
    if isinstance(value, (dt.date, dt.datetime)):
        d = value if isinstance(value, dt.date) else value.date()
        if key == "expiry":
            return d.strftime("%Y-%m")
        warnings.append(f"날짜 셀: {where} {USAGE_KEYS.get(key, IO_KEYS.get(key))[0]} → {d.isoformat()}")
        return d.isoformat()
    return value


def check_row(keys: dict, v: dict, choices: dict, where: str, warnings: list, sheet: str) -> None:
    for k, (header, lst, required) in keys.items():
        val = v.get(k)
        if k == "dir" and val in DIRECTION:
            val = DIRECTION[val]
        if required and (val is None or str(val).strip() == ""):
            warnings.append(f"필수값 누락: {where} '{header}'")
            continue
        if lst and val is not None and str(val) not in choices.get(lst, []):
            warnings.append(f"선택지 밖 값: {where} '{header}' = '{val}'")
        if k in FREE_TEXT and val and PERSON_PATTERN.search(str(val)):
            warnings.append(f"인명 유사 패턴: {where} '{header}'")


# --------------------------------------------------------------------------- 계산
def manual_applies(row: "IO", counterpart_tool: str) -> bool:
    """[I32] (Leo 2026-09-24) 수기 전달이 적힌 행이 연계 SW명을 적었다면 그 수기는 적힌(해석된) 상대에게만 적용한다.
    연계 SW명이 비었으면 모든 상대에게 적용. 해석 못 한 이름만 적었으면 조사된 어떤 상대에게도 적용하지 않는다."""
    if row.transfer not in MANUAL_TRANSFER:
        return False
    if not split_partners(row.partner_raw):
        return True
    return counterpart_tool in row.partner_tools


def grade(supplier: Usage, consumer: Usage) -> str:
    if supplier.airgap in AIRGAP_EXCLUDED or consumer.airgap in AIRGAP_EXCLUDED:
        return "제외"
    return {2: "A", 1: "B", 0: "C"}[supplier.automatable + consumer.automatable]


def compute(spec: dict, repo: Path) -> dict:
    template = repo / spec["template"]
    base_choices = template_choices(template)
    examples = template_example_rows(template)
    du, di = spec["defaults"]["usage"], spec["defaults"]["io"]
    usages: list[Usage] = []
    warnings: list[str] = []
    per_file = {}
    by_file_id: dict[tuple[str, str], Usage] = {}
    by_file_key: dict[tuple[str, str], Usage] = {}
    raw_ios = []

    # 재발송 [I33]: 파일명의 분야가 같은 파일 중 (날짜, 파일명) 이 가장 늦은 것만 적재한다
    def fname_of(f):
        return spec["file_name"].format(field=f["field"], date=f.get("file_date", spec["file_date"]))

    latest = {}
    for f in spec["files"]:
        k = (f.get("file_date", spec["file_date"]), fname_of(f))
        if f["field"] not in latest or k > latest[f["field"]][0]:
            latest[f["field"]] = (k, f)
    superseded = []
    for f in spec["files"]:
        if latest[f["field"]][1] is not f:
            superseded.append(fname_of(f))
            warnings.append(f"재발송으로 대체: {fname_of(f)} → {fname_of(latest[f['field']][1])} (적재 안 함)")
            per_file[fname_of(f)] = {"usage_rows": 0, "io_rows": 0, "excluded": 0, "warnings": 1, "superseded": True}

    for f in spec["files"]:
        ff = f["field"]
        fname = fname_of(f)
        if fname in superseded:
            continue
        choices = {k: list(v) for k, v in base_choices.items()}
        if f.get("extra_categories", True):
            choices["온톨로지분류"] += spec.get("extra_categories", [])
        stats = {"usage_rows": 0, "io_rows": 0, "excluded": 0, "warnings": 0, "superseded": False}
        w0 = len(warnings)

        # 헤더 [docs/02 5장 1]: 바뀐 문구는 정규화 비교로 매핑, 매핑 안 되는 헤더는 경고
        known = {norm_header(h) for h, _, _ in USAGE_KEYS.values()} | {norm_header(h) for h, _, _ in IO_KEYS.values()} \
            | {norm_header(h) for h in IGNORED_HEADERS}
        for sheet, overrides in f.get("header_overrides", {}).items():
            for old, new in overrides.items():
                if norm_header(new) not in known:
                    warnings.append(f"매핑 안 된 헤더: {fname} {sheet} '{new}'")
        for sheet, extra in f.get("extra_headers", {}).items():
            for h in extra:
                if norm_header(h) not in known:
                    warnings.append(f"매핑 안 된 헤더: {fname} {sheet} '{h}'")

        # 예시 행: 템플릿 위치에 남은 것 + 복사본 [I15]
        stats["excluded"] += 1 + (1 if f.get("io_start_row") == 5 else 3)
        for u in f["usages"]:
            if u.get("example_copy"):
                stats["excluded"] += 1
                continue
            v = {**du, "field_cell": ff, **u}
            where = f"{fname} SW기본정보 {v.get('sw_id')}"
            for k in list(v):
                if k in USAGE_KEYS:
                    v[k] = cell_to_text(k, v[k], where, warnings)
            check_row(USAGE_KEYS, v, choices, where, warnings, "SW기본정보")
            # 파트 = 파일 분야 (v0.3, docs/10 — 행의 '담당 부서' 는 분류 속성일 뿐 키가 아니다. P17 개정 2026-09-30)
            us = Usage(fname, ff, ff, str(v["sw_id"]), v["name"], v["vendor"], v["kind"], v.get("op"),
                       v.get("auto_if"), v["airgap"], v.get("freq"), v.get("users"), v.get("prio"))
            if (fname, us.sw_id) in by_file_id:
                warnings.append(f"중복 SW ID: {fname} {us.sw_id} — 먼저 나온 행 사용, '{us.name}' 행 제외")
                stats["excluded"] += 1
                continue
            if v["field_cell"] != ff:
                warnings.append(f"파일 분야 ≠ 담당 부서: {fname} {us.sw_id} → '{v['field_cell']}'")
            if us.users is not None and not isinstance(us.users, int):
                warnings.append(f"사용 인원수 정수 변환 실패: {fname} {us.sw_id} '{us.users}' — 원문 보존")
            by_file_id[(fname, us.sw_id)] = us
            by_file_key[(fname, _id_norm(us.sw_id))] = us
            usages.append(us)
            stats["usage_rows"] += 1

        prev_id = None                                                 # [I22] 바로 위 행(빈 행 없이 붙은)의 SW ID
        for r in f["ios"]:
            if r.get("blank") or r.get("example_copy"):
                prev_id = None
                continue
            if r.get("sw_id") in (None, "") and IO_ID_FILL_DOWN and prev_id is not None:
                r = {**r, "sw_id": prev_id}
                warnings.append(f"Tool ID 이어받음: {fname} SW입출력 '{r.get('name')}' → '{prev_id}' (바로 위 행)")
            if r.get("sw_id") in (None, ""):                           # [I22]
                warnings.append(f"SW ID 없는 내용 행: {fname} SW입출력 '{r.get('name')}' — 건너뜀")
                stats["excluded"] += 1
                prev_id = None
                continue
            prev_id = r["sw_id"]
            v = {**di, **r}
            where = f"{fname} SW입출력 {v['sw_id']} '{v['name']}'"
            for k in list(v):
                if k in IO_KEYS:
                    v[k] = cell_to_text(k, v[k], where, warnings)
            check_row(IO_KEYS, v, choices, where, warnings, "SW입출력")
            raw_ios.append((fname, ff, v))
            stats["io_rows"] += 1
        stats["warnings"] = len(warnings) - w0
        per_file[fname] = stats

    # 툴 — 정규화 키로 통합. [I34] 빈·범용 이름은 행별 키. [I1] 다른 행의 제조사 접두(범용 제조사 제외)를 떼면 기존 키와 같은 것은
    # 그 툴로 흡수 (Q3(a)) — 키 집합 위에서 쌍을 정하고 합집합으로 묶어 **그룹 단위**로 모든 행에 적용 (셋 이상이 얽혀도 쌍을 버리지
    # 않는다). 참조 계산은 레지스트리를 모르므로 생존 키는 늘 접두를 뗀 쪽 = 사슬의 끝 (명세에는 별칭이 없어 가장 짧은 키와 같다;
    # amap(별칭·통합 판정)이 있으면 적재기는 접두를 뗀 키의 대표 키를 따른다). 적재기는 레지스트리 활성 행이 그룹에 정확히 하나면
    # 그 키를 살리고, 둘 이상이면 흡수를 보류해 검토표로 올린다 — 레지스트리가 없을 때 결과가 같다.
    # 별개 판정 쌍(명세 distinct: [[키 A, 키 B]], tool_aliases.yaml distinct 거울)이 그룹 안에 들면 — 직접 쌍은 묶지 않지만 제3의 키를
    # 거쳐 한 그룹이 될 수 있다 — 그 그룹은 통째로 흡수하지 않고 경고 (합성 명세에는 없어 골든 값은 바뀌지 않는다)
    vendors = survey_vendors(usages)
    distinct = {tuple(sorted(p)) for p in (spec.get("distinct") or [])}
    for u in usages:
        u.tool = tool_key(u.name, u.vendor)
        if is_generic_key(u.tool):
            u.tool = f"{GENERIC_PREFIX}{u.field}/{u.sw_id}"
    existing = {u.tool for u in usages}
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        while parent.get(x, x) != x:
            x = parent[x]
        return x

    for k in sorted(existing):
        if k.startswith(GENERIC_PREFIX):
            continue
        for vk in vendors:
            rest = k[len(vk):]
            if k.startswith(vk) and rest and rest in existing and tuple(sorted((k, rest))) not in distinct:
                if find(k) != find(rest):
                    parent[find(k)] = find(rest)
                break
    groups: dict[str, set[str]] = defaultdict(set)
    for k in parent:
        groups[find(k)].add(k)
    absorb = {}
    for end, members in groups.items():
        members = members | {end}
        clashes = sorted(p for p in combinations(sorted(members), 2) if p in distinct)
        if clashes:
            for a, b in clashes:
                warnings.append(f"제조사 접두 흡수와 별개 판정이 충돌: {a} / {b} — 흡수하지 않음")
            continue
        survivor = min(members, key=lambda k: (len(k), k))      # 사슬의 끝 = 접두를 뗀 쪽 (별칭이 없으니 가장 짧은 키)
        for k in members - {survivor}:
            absorb[k] = survivor
    for u in usages:
        u.tool = absorb.get(u.tool, u.tool)
    tools = defaultdict(list)
    for u in usages:
        tools[u.tool].append(u)

    def resolve(name: str) -> str | None:        # [I1] [I14]
        k = tool_key(name)
        if k in tools:
            return k
        for vk in vendors:
            rest = k[len(vk):]
            if k.startswith(vk) and rest and rest in tools:
                return rest
        return None

    ios: list[IO] = []
    for fname, ff, v in raw_ios:
        exts, inhouse, bad = normalize_extensions(v["ext"])
        owner = by_file_id.get((fname, str(v["sw_id"]))) or by_file_key.get((fname, _id_norm(v["sw_id"])))   # [D3] 같은 파일 안, [#18] 표기 차이 흡수
        io = IO(fname, ff, str(v["sw_id"]), v["dir"], v["name"], v["cat"], str(v["ext"]), exts, inhouse,
                str(v["transfer"] or "").strip(), v.get("partner") or "", v.get("note") or "", owner)
        if owner is not None and owner.sw_id != io.sw_id:
            warnings.append(f"Tool ID 표기 차이: {fname} '{io.sw_id}' → '{owner.sw_id}' 로 연결")
            per_file[fname]["warnings"] += 1
        if owner is None:
            warnings.append(f"고아 입출력: {fname} SW ID '{io.sw_id}' ({io.name}) — SW기본정보에 없음")
            per_file[fname]["warnings"] += 1
        if bad:
            warnings.append(f"확장자 매핑 실패: {fname} {io.sw_id} '{io.name}' 토큰 {bad} — 원문 보존")
            per_file[fname]["warnings"] += 1
        for p in split_partners(io.partner_raw):
            t = resolve(p)
            if t:
                io.partner_tools.add(t)
            else:
                io.partner_unresolved.append(tool_key(p))
        ios.append(io)

    # 골든 IO 키: 기본 키가 겹치면 달라지는 필드로 구분, 완전히 같으면 순번 + 경고 [D2]
    by_base = defaultdict(list)
    for io in ios:
        by_base[(io.file, io.base_key)].append(io)
    for group in by_base.values():
        if len(group) < 2:
            continue
        fields = [("cat", lambda x: x.cat), ("ext", lambda x: x.ext_raw),
                  ("transfer", lambda x: x.transfer), ("partner", lambda x: x.partner_raw)]
        varying = [g for n, g in fields if len({g(x) for x in group}) > 1]
        seen = Counter()
        for x in group:
            sig = tuple(g(x) for g in varying)
            if varying:
                x.suffix = "[" + "|".join(sig) + "]"
            if seen[sig]:
                x.suffix += f"#{seen[sig]}"
                warnings.append(f"완전 중복 입출력 행: {x.key} — 경고 후 순번")
                per_file[x.file]["warnings"] += 1
            seen[sig] += 1

    owned = [x for x in ios if x.owner]                                  # [I9]
    derive_warnings = sorted(f"확장자 미기재: {x.key}" for x in owned if not x.exts)   # [I13] 입출력마다 1건
    feeds: list[Feed] = []
    for o in owned:
        if o.direction != "out" or not o.exts:
            continue
        for i in owned:
            if i.direction != "in" or not i.exts or o.cat != i.cat or o.owner is i.owner:
                continue
            m = sorted(set(o.exts) & set(i.exts))
            if not m:
                continue
            manual = manual_applies(o, i.owner.tool) or manual_applies(i, o.owner.tool)   # [I21] [I32]
            note_hit = any(k in o.note or k in i.note for k in NOTE_KEYWORDS)              # 비고마다 따로
            basis = "전달방법" if manual else ("비고" if note_hit else None)
            feeds.append(Feed(
                o, i, m, "낮음" if all(e in GENERIC_EXT for e in m) else "보통",
                (i.owner.tool in o.partner_tools) or (o.owner.tool in i.partner_tools),
                manual, basis, grade(o.owner, i.owner) if basis else None))              # [I3] 비고 신호도 등급

    # CQ04 대조
    recon = []
    for x in owned:
        if not x.exts:                                                   # [I13]
            recon += [(x, t, "확장자 미기재") for t in sorted(x.partner_tools)]
            continue
        comp = {f.o.owner.tool for f in feeds if f.i is x} if x.direction == "in" else \
               {f.i.owner.tool for f in feeds if f.o is x}
        for t in sorted(comp | x.partner_tools):
            if t in comp and t in x.partner_tools:
                v = "확정"
            elif t in x.partner_tools:
                v = "숨은변환 의심"
            else:
                v = "잠재(연계 미기재)" if not split_partners(x.partner_raw) else "잠재(신고와 다름)"
            recon.append((x, t, v))

    # 착수 순위 [I4] [I5] [I18] [I25] [I26]
    handoffs = {}
    for f in feeds:
        if f.manual:
            ent = handoffs.setdefault((f.o.owner.key, f.i.owner.key, "수기"),
                                      [f.o.owner, f.i.owner, "수기", f.grade, []])
            ent[4] += [f.o.key, f.i.key]
    for x, t, v in recon:
        if v != "숨은변환 의심":
            continue
        for u in tools[t]:
            if u is x.owner:                                             # [I26] 자기 자신 쌍은 만들지 않음
                continue
            s, c = (u, x.owner) if x.direction == "in" else (x.owner, u)
            ent = handoffs.setdefault((s.key, c.key, "변환"), [s, c, "변환", grade(s, c), []])
            ent[4].append(x.key)
    # [I3] (Leo 2026-09-24) 비고 신호 구간도 '비고' 종류로 올린다 — 같은 쌍의 수기 행이 있으면 올리지 않는다
    for f in feeds:
        if f.manual_basis == "비고" and (f.o.owner.key, f.i.owner.key, "수기") not in handoffs:
            ent = handoffs.setdefault((f.o.owner.key, f.i.owner.key, "비고"),
                                      [f.o.owner, f.i.owner, "비고", f.grade, []])
            ent[4] += [f.o.key, f.i.key]
    # [I18] 같은 등급 안에서 비고 행은 수기·변환 행 뒤 (근거가 약하다)
    ranked = sorted(handoffs.values(), key=lambda h: (
        GRADE_ORDER[h[3]], h[2] == "비고", *[-v for v in h[1].sort_key()], *[-v for v in h[0].sort_key()],
        h[0].key, h[1].key))

    # CQ05 고립 [I11]
    has_io = {x.owner.key for x in owned}
    linked = {f.o.owner.key for f in feeds} | {f.i.owner.key for f in feeds}
    resolved = {x.owner.key for x in owned if x.partner_tools}
    no_io = sorted(u.key for u in usages if u.key not in has_io)
    unlinked = sorted(u.key for u in usages if u.key in has_io and u.key not in linked | resolved)

    # CQ08 허브 [I7] [I24]
    tool_partners, usage_partners = defaultdict(set), defaultdict(set)
    for f in feeds:
        a, b = f.o.owner, f.i.owner
        if a.tool != b.tool:
            tool_partners[a.tool].add(b.tool)
            tool_partners[b.tool].add(a.tool)
        usage_partners[a.key].add(b.key)
        usage_partners[b.key].add(a.key)

    # CQ09 [I10]
    missing = defaultdict(lambda: {"mentions": 0, "fields": set()})
    for x in ios:
        for k in x.partner_unresolved:
            missing[k]["mentions"] += 1
            missing[k]["fields"].add(x.owner.field if x.owner else x.file_field)

    # CQ10 [I23] — 행별 '미상:' 키는 후보에 올리지 않고, 포함은 짧은 키가 CONTAIN_MIN 자 이상일 때만 [I34]
    keys = sorted(k for k in tools if not k.startswith(GENERIC_PREFIX))
    candidates = sorted({(a, b) for a in keys for b in keys if a < b and (
        ((a in b or b in a) and min(len(a), len(b)) >= CONTAIN_MIN)
        or max(difflib.SequenceMatcher(None, a, b).ratio(), difflib.SequenceMatcher(None, b, a).ratio()) >= FUZZY)})
    conflicts = {}
    for k, us in tools.items():
        for attr in ("vendor", "kind"):
            c = Counter(getattr(u, attr) for u in us)
            if len(c) > 1:
                top = max(c.values())
                conflicts.setdefault(k, {})[attr] = {"majority": sorted(v for v, n in c.items() if n == top)[0],
                                                     "values": dict(sorted(c.items()))}

    matrix, matrix_manual = Counter(), Counter()                         # [I20] 대각 포함
    for f in feeds:
        matrix[(f.o.owner.field, f.i.owner.field)] += 1
        if f.manual:
            matrix_manual[(f.o.owner.field, f.i.owner.field)] += 1

    return dict(usages=usages, tools=tools, ios=ios, feeds=feeds, recon=recon, ranked=ranked, no_io=no_io,
                unlinked=unlinked, tool_partners=tool_partners, usage_partners=usage_partners, missing=missing,
                candidates=candidates, conflicts=conflicts, matrix=matrix, matrix_manual=matrix_manual,
                warnings=warnings, derive_warnings=derive_warnings, per_file=per_file)


def reach(result: dict, start: set[str], direction: str = "down", max_depth: int | None = None) -> list[str]:
    """eg:feeds 방향 탐색 [I19]: 시작점 자신은 (순환으로 돌아와도) 결과에 넣지 않는다."""
    nxt = defaultdict(set)
    for f in result["feeds"]:
        a, b = f.o.owner.key, f.i.owner.key
        (nxt[a] if direction == "down" else nxt[b]).add(b if direction == "down" else a)
    seen, frontier, depth = set(), set(start), 0
    while frontier and (max_depth is None or depth < max_depth):
        frontier = {n for s in frontier for n in nxt[s]} - seen - set(start)
        seen |= frontier
        depth += 1
    return sorted(seen)


def top_n(counts: dict[str, int], n: int = HUB_TOP_N) -> list[str]:
    """[I24] N 번째 값과 같은 동률은 모두 포함."""
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    if len(ordered) <= n:
        return [k for k, _ in ordered]
    cut = ordered[n - 1][1]
    return [k for k, v in ordered if v >= cut]


def summarize(result: dict) -> dict:
    feeds = result["feeds"]
    rv = Counter(v for _, _, v in result["recon"])
    impact_start = {x.owner.key for x in result["ios"]
                    if x.owner and x.direction == "in" and x.cat == "해석-결과" and "csv" in x.exts}
    tool_hub = {k: len(v) for k, v in result["tool_partners"].items()}
    usage_hub = {k: len(v) for k, v in result["usage_partners"].items()}
    return {
        "counts": {
            "usages": len(result["usages"]), "tools": len(result["tools"]), "io_specs": len(result["ios"]),
            "orphan_io_specs": sum(1 for x in result["ios"] if not x.owner),
            "fields": len({u.field for u in result["usages"]}),
            "categories": len({x.cat for x in result["ios"]}),
            "feeds": len(feeds), "feeds_manual": sum(f.manual for f in feeds),
            "feeds_note_signal": sum(f.manual_basis == "비고" for f in feeds),
            "feeds_low_confidence": sum(f.confidence == "낮음" for f in feeds),
            "feeds_declared": sum(f.declared for f in feeds),
        },
        "loader_per_file": result["per_file"],
        "reconciliation_counts": dict(sorted(rv.items())),
        "handoff_ranking": [{"supplier": h[0].key, "consumer": h[1].key, "kind": h[2], "grade": h[3],
                             "evidence": sorted(set(h[4]))} for h in result["ranked"]],
        "isolated": {"no_io": result["no_io"], "unlinked": result["unlinked"]},
        "hub_partner_counts": dict(sorted(tool_hub.items(), key=lambda kv: (-kv[1], kv[0]))),
        "hub_top10_tools": top_n(tool_hub),
        "hub_partner_counts_usage": dict(sorted(usage_hub.items(), key=lambda kv: (-kv[1], kv[0]))),
        "hub_top10_usages": top_n(usage_hub),
        "missing_tools": {k: {"mentions": v["mentions"], "fields": sorted(v["fields"])}
                          for k, v in sorted(result["missing"].items())},
        "tools": {k: sorted({u.name for u in us}) for k, us in sorted(result["tools"].items())},
        "merge_candidates": [list(p) for p in result["candidates"]],
        "attribute_conflicts": dict(sorted(result["conflicts"].items())),
        "field_matrix": {f"{a} → {b}": n for (a, b), n in sorted(result["matrix"].items())},
        "field_matrix_manual": {f"{a} → {b}": n for (a, b), n in sorted(result["matrix_manual"].items())},
        "impact_해석결과_csv": sorted(impact_start | set(reach(result, impact_start))),
        "cq01_2차유로(SAS)/SAS-01": {
            "upstream_1": reach(result, {"2차유로(SAS)/SAS-01"}, "up", 1),
            "downstream_1": reach(result, {"2차유로(SAS)/SAS-01"}, "down", 1),
            "upstream_all": reach(result, {"2차유로(SAS)/SAS-01"}, "up"),
            "downstream_all": reach(result, {"2차유로(SAS)/SAS-01"}, "down"),
        },
        "feeds": [{"from": f.o.key, "to": f.i.key, "matched": f.matched, "confidence": f.confidence,
                   "declared": f.declared, "manual": f.manual, "basis": f.manual_basis, "grade": f.grade}
                  for f in sorted(feeds, key=lambda f: (f.o.key, f.i.key))],
        "reconciliation": [{"io": x.key, "tool": t, "verdict": v}
                           for x, t, v in sorted(result["recon"], key=lambda r: (r[0].key, r[1]))],
        "warnings": sorted(result["warnings"]),
        "derive_warnings": result["derive_warnings"],
    }
