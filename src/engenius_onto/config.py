"""설정 파일 읽기. 경로는 저장소 루트(config/) 기준.

M3.1 2차 (docs/09 C15, docs/11 3장 1번): 사내 설정 오버레이 — data/real/config/<이름>.yaml 이 있으면 config/<이름>.yaml 위에
덮는다. 저장소의 config/ 는 공개 값(공개 툴 별칭·규칙)만 두고, 실 툴명·셀 값이 드는 판정(apply-review·value_aliases)은
오버레이에 쌓는다 (git 제외, 업데이트 파일이 덮어쓰지 않는다). 합치는 방식은 파일마다 다르다 — merge_config().
"""

from __future__ import annotations

import csv
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"
REAL_CONFIG_DIR = REPO_ROOT / "data" / "real" / "config"      # 사내 오버레이 (git 제외 — .gitignore data/real/)


def config_where(path: Path) -> str:
    """오류 문구·로그에 쓰는 설정 파일 경로 — 저장소 안이면 저장소 기준 상대 경로('/' 구분), 밖이면 절대 경로."""
    p = Path(path).resolve()
    try:
        return p.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(p)


def read_yaml(path: Path, where: str | None = None) -> dict:
    """YAML 설정 파일 하나 읽기 (없는 파일은 호출자가 거른다). 문법 오류는 traceback 대신 ConfigError —
    '<파일> <행>행 <열>열: YAML 문법 오류' 로 자리만 알리고 줄 내용·값은 넣지 않는다 (오버레이에는 실 툴명이 든다 — 반출 차단).
    파일 전체가 매핑이 아니면(목록·문자열) 그것도 ConfigError."""
    path = Path(path)
    where = where or config_where(path)
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        at = f" {mark.line + 1}행 {mark.column + 1}열" if mark is not None else ""
        raise ConfigError(f"{where}{at}: YAML 문법 오류 — 들여쓰기·괄호·콜론 뒤 공백을 확인") from None
    return _expect(where, "(파일 전체)", data, "dict")


def load_yaml(name: str, config_dir: Path | None = None) -> dict:
    return read_yaml((config_dir or CONFIG_DIR) / name)


# --------------------------------------------------------------------------- 오버레이 (C15)
def default_overlay_dir(config_dir: Path | None = None) -> Path | None:
    """기본 오버레이 폴더 — 저장소 config/ 를 쓸 때만 data/real/config (있을 때). 다른 config 폴더(테스트 사본)에는 붙이지 않는다."""
    base = Path(config_dir or CONFIG_DIR).resolve()
    if base == CONFIG_DIR.resolve() and REAL_CONFIG_DIR.is_dir():
        return REAL_CONFIG_DIR
    return None


class ConfigError(ValueError):
    """설정 파일(config/·오버레이)의 형식·값 오류 — CLI 는 '[NG] 설정 오류: …' 한 줄로 보여 주고 rc 1 (traceback 없이)."""


def _merge_dict_keys(base: dict, over: dict, where: str = "", path: str = "") -> dict:
    """키 단위 덮어쓰기 — 중첩 dict 는 키별로 내려가고, 목록·스칼라는 통째 바꾼다 (rules.yaml 방식).
    기본값이 매핑·목록인 키에 다른 형식을 덮으면 ConfigError (where = 오버레이 파일 이름).
    값 없는 키(`loader:` 처럼 YAML 에서 None)로 매핑·목록 기본값을 지우는 것도 오류 — 조용히 None 으로 덮지 않는다."""
    out = dict(base or {})
    for k, v in (over or {}).items():
        cur = out.get(k)
        name = f"{path}.{k}" if path else str(k)
        if v is None and isinstance(cur, (dict, list)):
            raise ConfigError(f"{where} {name}: 값이 비어 있다 — 키를 지우거나 값을 적는다")
        if isinstance(v, dict) and isinstance(cur, dict):
            out[k] = _merge_dict_keys(cur, v, where, name)
        elif v is not None and isinstance(cur, dict) and not isinstance(v, dict):
            raise ConfigError(f"{where} {name}: 형식은 매핑(키: 값) 이어야 한다 (지금: {type(v).__name__})")
        elif v is not None and isinstance(cur, list) and not isinstance(v, list):
            raise ConfigError(f"{where} {name}: 형식은 목록 이어야 한다 (지금: {type(v).__name__})")
        else:
            out[k] = v
    return out


def _expect(where: str, key: str, value, kind: str):
    """설정 값의 형식 검사 — 틀리면 파일·키 이름을 붙인 ValueError (조용히 무시하거나 AttributeError 로 죽지 않게).
    kind: 'dict' | 'list' | 'str' | 'dict_of_list' | 'dict_of_str' | 'dict_of_dict' | 'list_of_pairs'. None 은 빈 값으로 본다."""
    want = {"dict": "매핑(키: 값)", "list": "목록", "str": "문자열", "dict_of_list": "매핑(이름: [목록])",
            "dict_of_str": "매핑(키: 문자열)", "dict_of_dict": "매핑(열: {적힌 값: 값})", "list_of_pairs": "목록([[키 A, 키 B], ...])"}[kind]

    def bad():
        return ConfigError(f"{where} {key}: 형식은 {want} 이어야 한다 (지금: {type(value).__name__})")

    if value is None:
        return {} if kind.startswith("dict") else [] if kind.startswith("list") else ""
    if kind == "str":
        if not isinstance(value, (str, int, float)):
            raise bad()
        return str(value)
    if kind.startswith("dict"):
        if not isinstance(value, dict):
            raise bad()
        if kind == "dict_of_list" and not all(v is None or isinstance(v, list) for v in value.values()):
            raise bad()
        if kind == "dict_of_str" and not all(v is None or isinstance(v, (str, int, float)) for v in value.values()):
            raise bad()
        if kind == "dict_of_dict" and not all(v is None or isinstance(v, dict) for v in value.values()):
            raise bad()
        return value
    if not isinstance(value, list):
        raise bad()
    if kind == "list_of_pairs" and not all(isinstance(p, (list, tuple)) and len(p) == 2 for p in value):
        raise bad()
    return value


ALIASES_SHAPES = {"aliases": "dict_of_list", "distinct": "list_of_pairs", "merge_pairs": "list_of_pairs",
                  "merge_keys": "dict_of_str", "labels": "dict_of_str",
                  "partner_missing": "list"}      # tool_aliases.yaml 의 정해진 키와 형식 (partner_missing — 검토표 연계 행 '기존 툴 아님', docs/09 #17)


def check_aliases_shape(where: str, cfg: dict) -> dict:
    """tool_aliases.yaml 한 파일의 형식 검사 (merge_config 와 apply-review 가 같이 쓴다) — 정해진 키는 형식이 틀리면 ConfigError,
    빈 값(None)은 빈 매핑·목록으로. 돌려주는 dict 는 정해진 키를 모두 갖되, 원래 파일에 있던 키만 `in` 으로 알 수 있게
    '_present' 집합을 함께 둔다 (merge_pairs: [] 로 비운 파일과 키가 없는 옛 파일을 구별 — 6.1-5)."""
    cfg = _expect(where, "(파일 전체)", cfg, "dict")
    out = {k: _expect(where, k, cfg.get(k), kind) for k, kind in ALIASES_SHAPES.items()}
    out["_present"] = {k for k in ALIASES_SHAPES if k in cfg}
    return out


def check_header_map_shape(where: str, cfg) -> dict[str, dict[str, list[str]]]:
    """header_map.yaml 한 파일의 형식 — {시트: {슬롯: [문구, ...]}} (I30). 틀리면 ConfigError — 오류 문구에는 파일·시트·슬롯(위치)만 쓰고
    헤더 문구는 넣지 않는다 (사내 헤더에 인명이 섞일 수 있다). 문자열 하나('비고2')를 목록 대신 쓰면 글자 단위로 매핑되던 것을 막는다.
    빈 값(None)은 빈 매핑·목록으로. 의미 검사(모르는 시트·슬롯, 제외 열 문구, 문구 충돌)는 form_spec.load_form_spec 이 한다."""
    cfg = _expect(where, "(파일 전체)", cfg, "dict")
    out: dict[str, dict[str, list[str]]] = {}
    for sheet, slots in cfg.items():
        slots = _expect(where, str(sheet), slots, "dict")
        cur = out.setdefault(str(sheet), {})
        for slot, phrases in slots.items():
            phrases = [] if phrases is None else phrases
            if not isinstance(phrases, list) or not all(isinstance(p, (str, int, float)) and not isinstance(p, bool) for p in phrases):
                raise ConfigError(f"{where} {sheet}.{slot}: 형식은 문구 목록(['문구', ...]) 이어야 한다 (지금: {type(phrases).__name__})")
            cur[str(slot)] = [str(p) for p in phrases]
    return out


def merge_config(name: str, base: dict, over: dict, where_base: str | None = None, where_over: str | None = None) -> dict:
    """config/<name> 위에 오버레이 <name> 을 덮은 결과 (where_*: 오류 문구에 쓰는 파일 경로 — load_config 가 실제 경로를 넘긴다).

    - tool_aliases.yaml: aliases 는 대표 이름별 변형 목록 합집합, distinct·merge_pairs 는 쌍 합집합, partner_missing 은 키 합집합, labels 는 키별 덮어쓰기.
      merge_keys 는 어느 한쪽에라도 merge_pairs 키가 있으면 **합친 merge_pairs 에서 다시 계산**한다 (merge_keys_from_pairs — 두 파일의
      이력이 사슬로 이어질 때 키별 덮어쓰기는 깊이 1 이 깨져 '손으로 고친 merge_pairs' 경고가 영구히 났다). merge_pairs 키가 없는 쪽의
      merge_keys 는 쌍으로 승격해 섞는다 (옛 파일 호환). 양쪽 다 키가 없으면 옛 방식(merge_keys 키별 덮어쓰기, merge_pairs 키 없음).
    - value_aliases.yaml: 열별 깊은 병합 (같은 열의 '적힌 값' 은 오버레이가 이긴다)
    - template_examples.yaml: 시트별 예시 행 목록 합집합 (같은 행은 한 번 — 사내 양식판의 예시를 더한다, docs/09 #3)
    - header_map.yaml: 시트·슬롯별 문구 합집합 — 저장소 문구 먼저, 오버레이의 새 문구를 뒤에 (같은 문구는 한 번; 지우기는 없다 — 사내 문구를
      더하기만, I30). 시트 키는 원문 그대로 합친다 (v1.1 이름 'Tool 입출력' 과 정규 이름의 통합·의미 검사는 form_spec.load_form_spec)
    - 그 밖(rules.yaml 등): 키 단위 덮어쓰기 (중첩 dict 는 키별)
    형식이 틀린 값(목록 자리에 문자열 등)·값 없는 키는 파일·키 이름을 붙인 ConfigError(ValueError) 로 멈춘다 — 조용히 무시하지 않는다.
    """
    srcs = ((where_base or f"config/{name}", base), (where_over or f"data/real/config/{name}", over))
    base, over = (_expect(w, "(파일 전체)", d, "dict") for w, d in srcs)
    if name == "tool_aliases.yaml":
        from engenius_onto.normalize import merge_keys_from_pairs, read_merge_pairs   # normalize 가 config 를 import 한다 — 지연 import

        b, o = (check_aliases_shape(w, d) for w, d in zip((s[0] for s in srcs), (base, over)))
        aliases = {k: [str(x) for x in (v or [])] for k, v in b["aliases"].items()}
        for rep, variants in o["aliases"].items():
            aliases[rep] = sorted(set(aliases.get(rep) or []) | {str(x) for x in (variants or [])})
        distinct = [list(p) for p in b["distinct"]]
        for p in o["distinct"]:
            if list(p) not in distinct:
                distinct.append(list(p))
        out = _merge_dict_keys({k: v for k, v in base.items() if k not in ALIASES_SHAPES},      # 정해진 키는 아래서 합친다
                               {k: v for k, v in over.items() if k not in ALIASES_SHAPES}, srcs[1][0])
        missing = [str(x) for x in b["partner_missing"]]
        missing += [str(x) for x in o["partner_missing"] if str(x) not in missing]
        out.update({"aliases": aliases, "distinct": distinct, "labels": {**b["labels"], **o["labels"]}, "partner_missing": missing})
        if "merge_pairs" in b["_present"] or "merge_pairs" in o["_present"]:
            pairs = []
            for d in (b, o):                                   # 키가 없는 쪽만 merge_keys 를 쌍으로 승격 (read_merge_pairs 와 같은 규칙)
                for p in read_merge_pairs({k: d[k] for k in ("merge_pairs", "merge_keys") if k in d["_present"]}):
                    if p not in pairs:
                        pairs.append(p)
            out["merge_pairs"], out["merge_keys"] = pairs, merge_keys_from_pairs(pairs)
        else:
            out["merge_keys"] = {**b["merge_keys"], **o["merge_keys"]}
        return out
    if name == "value_aliases.yaml":
        b, o = (_expect(w, "(파일 전체)", d, "dict_of_dict") for w, d in zip((s[0] for s in srcs), (base, over)))
        out = {col: dict(m or {}) for col, m in b.items()}
        for col, m in o.items():
            out[col] = {**out.get(col, {}), **(m or {})}
        return out
    if name == "template_examples.yaml":
        out: dict = {}
        for w, d in srcs:
            for sheet, rows in _expect(w, "(파일 전체)", d, "dict_of_list").items():
                cur = out.setdefault(sheet, [])
                for row in rows or []:
                    if not isinstance(row, dict):
                        raise ConfigError(f"{w} {sheet}: 예시 행은 매핑(슬롯: 값) 이어야 한다 (지금: {type(row).__name__})")
                    if row not in cur:
                        cur.append(row)
        return out
    if name == "header_map.yaml":
        out = {}
        for w, d in srcs:
            for sheet, slots in check_header_map_shape(w, d).items():
                cur = out.setdefault(sheet, {})
                for slot, phrases in slots.items():
                    lst = cur.setdefault(slot, [])
                    lst += [p for p in phrases if p not in lst]
        return out
    return _merge_dict_keys(base, over, srcs[1][0])


def load_config(name: str, config_dir: Path | None = None, overlay_dir: Path | None = None,
                optional: bool = False) -> tuple[dict, bool]:
    """(합친 설정, 오버레이 파일을 썼는지). overlay_dir 가 None 이면 오버레이 없음 — 호출자가 default_overlay_dir() 로 정한다.
    YAML 문법 오류·형식 오류는 실제 파일 경로를 붙인 ConfigError (read_yaml·merge_config)."""
    base_path = Path(config_dir or CONFIG_DIR) / name
    if optional and not base_path.is_file():
        base = {}
    else:
        base = read_yaml(base_path)
    over_path = Path(overlay_dir) / name if overlay_dir else None
    if over_path is None or not over_path.is_file():
        if name == "tool_aliases.yaml":
            check_aliases_shape(config_where(base_path), base)      # 오버레이가 없어도 형식은 검사 (값은 원문 그대로 돌려준다)
        return base, False
    over = read_yaml(over_path)
    return merge_config(name, base, over, config_where(base_path), config_where(over_path)), True


# --------------------------------------------------------------------------- CSV (docs/09 #15)
def read_csv_rows(path: Path) -> tuple[list[dict], str]:
    """검토표·레지스트리 CSV 읽기 — utf-8-sig 로 먼저, 안 되면 cp949 (엑셀 '다른 이름으로 저장' 기본값). (행 목록, 쓴 인코딩)."""
    path = Path(path)
    last: Exception | None = None
    for enc in ("utf-8-sig", "cp949"):
        try:
            with path.open(encoding=enc, newline="") as f:
                return [dict(r) for r in csv.DictReader(f)], enc
        except UnicodeDecodeError as e:
            last = e
    raise ValueError(f"CSV 인코딩을 알 수 없다: {path.name} — 엑셀에서 'CSV UTF-8(쉼표로 분리)' 로 저장한다 ({last})")


# --------------------------------------------------------------------------- 설치 판 표식 (docs/11 3장 3번)
INSTALLED_COMMIT_FILE = REPO_ROOT / "offline" / "installed_commit.txt"   # 1행 커밋 해시, 2행 커밋 번호 — 업데이트 적용 스크립트가 쓴다


@dataclass(frozen=True)
class InstalledVersion:
    commit: str          # 짧은 해시(앞 7자) 또는 '미상' — diag·doctor·load_log 표기
    number: int | None   # git rev-list --count (없으면 None)
    source: str          # installed_commit.txt | git | 없음
    commit_full: str = ""   # 표식 파일·git 에 적힌 그대로의 해시 (load_log 에만)

    def __str__(self) -> str:
        return f"{self.commit} (#{self.number})" if self.number is not None else self.commit


def _short_commit(h: str) -> str:
    """표식의 해시를 앞 7자로 — 전체 해시(40자)든 짧은 해시든 같은 표기 (README_offline 7장: '앞 7자리면 충분')."""
    return h.strip()[:7]


def installed_version(repo_root: Path | None = None) -> InstalledVersion:
    """설치 판 — offline/installed_commit.txt 가 있으면 그것, 없으면 .git 의 HEAD, 둘 다 없으면 '미상'.
    표식은 BOM 이 붙어 있어도(메모장 저장) 읽고, commit 은 앞 7자로 정규화한다 (전체 해시는 commit_full).
    값 없음(해시·번호뿐) — load_log·diag 머리에 넣어 밖으로 가져갈 수 있다."""
    root = Path(repo_root or REPO_ROOT)
    marker = root / "offline" / "installed_commit.txt"
    if marker.is_file():
        lines = [ln.strip() for ln in marker.read_text(encoding="utf-8-sig", errors="replace").splitlines() if ln.strip()]
        if lines:
            num = int(lines[1]) if len(lines) > 1 and lines[1].isdigit() else None
            return InstalledVersion(_short_commit(lines[0]), num, "installed_commit.txt", lines[0])
    if (root / ".git").exists():
        try:
            run = lambda *a: subprocess.run(["git", *a], cwd=root, capture_output=True, text=True, timeout=10)  # noqa: E731
            h = run("rev-parse", "HEAD")
            n = run("rev-list", "--count", "HEAD")
            if h.returncode == 0 and h.stdout.strip():
                full = h.stdout.strip()
                return InstalledVersion(_short_commit(full), int(n.stdout.strip()) if n.returncode == 0 and n.stdout.strip().isdigit()
                                        else None, "git", full)
        except (OSError, subprocess.SubprocessError):
            pass
    return InstalledVersion("미상", None, "없음")


# --------------------------------------------------------------------------- Fuseki
@dataclass(frozen=True)
class FusekiConfig:
    endpoint: str
    dataset: str
    graphs: dict
    timeout_s: float = 10.0

    @property
    def dataset_url(self) -> str:
        return f"{self.endpoint.rstrip('/')}/{self.dataset}"

    @property
    def ping_url(self) -> str:
        return f"{self.endpoint.rstrip('/')}/$/ping"


def fuseki_config(config_dir: Path | None = None) -> FusekiConfig:
    d = load_yaml("fuseki.yaml", config_dir)
    return FusekiConfig(
        endpoint=d["endpoint"],
        dataset=d["dataset"],
        graphs=dict(d["graphs"]),
        timeout_s=float(d.get("timeout_s", 10)),
    )


SCHEMA_FILE = REPO_ROOT / "schema" / "engenius_tool.yaml"


def namespaces(schema_file: Path | None = None) -> dict:
    """온톨로지·인스턴스 네임스페이스 {eg, egid}. 정본은 스키마 prefixes 한 곳이다.

    바꿀 때는 schema/engenius_tool.yaml(과 검증용 컨테이너 스키마) 의 prefixes 를 고치고
    python -m engenius_onto schema 로 재생성한다 — 생성물(OWL·SHACL·Pydantic)이 IRI 를 담기 때문.
    """
    with (schema_file or SCHEMA_FILE).open(encoding="utf-8") as f:
        prefixes = yaml.safe_load(f)["prefixes"]
    return {"eg": prefixes["eg"], "egid": prefixes["egid"]}
