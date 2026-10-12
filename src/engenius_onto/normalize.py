"""정규화 (docs/02 6장) — 툴 이름 키, 연계 SW명 분리, 확장자.

규칙 값은 config/rules.yaml·extensions.yaml 에서 읽는다. 세부 해석은 골든 interpretations (I번호).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from engenius_onto.config import load_config

GENERIC_KEY_PREFIX = "미상:"     # 범용·빈 이름의 행별 툴 키 접두 (I34) — '미상:<파트>/<Tool ID>'


def nfkc(s) -> str:
    return unicodedata.normalize("NFKC", "" if s is None else str(s))


def nfc_strip(s) -> str:
    return unicodedata.normalize("NFC", "" if s is None else str(s)).strip()


# --------------------------------------------------------------------------- 툴 통합 판정 이력 (6.1-5)
# 적재기(loader._alias_map)와 apply-review(survey_load) 가 같이 쓴다 — 순환 import 가 없는 여기에 둔다.
def link_root(links: dict[str, str], k: str) -> str:
    """통합 링크(키 → 키)를 끝까지 따라간 대표 키. 순환이면 돌아오는 자리에서 멈춘다."""
    seen = [k]
    while seen[-1] in links and links[seen[-1]] not in seen:
        seen.append(links[seen[-1]])
    return seen[-1]


def merge_keys_from_pairs(pairs: list[list[str]]) -> dict[str, str]:
    """판정 이력 merge_pairs([[A 키, B 키], ...], A 생존) → merge_keys {B 키: 대표 키} (깊이 1).
    순서대로 root(B) → root(A) 로 잇고, 대표가 바뀐 키들은 새 대표로 다시 가리킨다.
    apply-review 가 저장 때 계산해 파일에 적고, 적재기도 merge_pairs 가 있으면 같은 계산으로 다시 구한다 (손으로 고친 이력 반영)."""
    merge_keys: dict[str, str] = {}
    for a, b in pairs:
        ra, rb = link_root(merge_keys, a), link_root(merge_keys, b)
        if ra == rb:
            continue
        merge_keys[rb] = ra
        for k, v in list(merge_keys.items()):           # 깊이 1 유지 — rb 를 가리키던 것은 ra 로
            if v == rb:
                merge_keys[k] = ra
    return merge_keys


def read_merge_pairs(cfg: dict, promote: bool = True) -> list[list[str]]:
    """merge_pairs (판정 이력). promote=True 면 옛 파일(merge_pairs **키가 없고** merge_keys 만 있음)의 merge_keys 를 쌍으로 승격해
    읽는다 (하위 호환). `merge_pairs: []` 로 비운 파일은 키가 있으므로 승격하지 않는다 — 비운 뜻(통합 0)을 지킨다."""
    pairs = [[nfc_strip(a), nfc_strip(b)] for a, b in (cfg.get("merge_pairs") or [])]
    if "merge_pairs" not in cfg and promote:
        pairs = [[nfc_strip(a), nfc_strip(b)] for b, a in (cfg.get("merge_keys") or {}).items()]
    return [p for p in pairs if p[0] and p[1] and p[0] != p[1]]


@dataclass
class Normalizer:
    rules: dict
    ext_cfg: dict

    @classmethod
    def from_config(cls, config_dir: Path | None = None, overlay_dir: Path | None = None) -> Normalizer:
        """overlay_dir(사내 오버레이, C15)의 rules.yaml·extensions.yaml 이 있으면 키 단위로 덮는다."""
        return cls(load_config("rules.yaml", config_dir, overlay_dir)[0],
                   load_config("extensions.yaml", config_dir, overlay_dir)[0])

    # --- 공통 --------------------------------------------------------------------
    @cached_property
    def empty_tokens(self) -> set[str]:
        return {str(t).lower() for t in self.rules["empty_tokens"]}

    def is_empty(self, s) -> bool:
        """셀 전체가 빈 값 토큰인지 (I16)."""
        return nfkc(s).strip().lower() in self.empty_tokens

    # --- 자동화 판정 (docs/02 7.4, I16) -----------------------------------------------
    def automatable(self, op, aif) -> bool:
        """툴사용이 자동화 가능한가 — 조작 방식이 rules.yaml automatable.operation_modes 이거나, 자동화 IF 가 비어 있지 않고 빈 값 토큰
        (empty_tokens — NA·-·해당없음 포함)도 아니며 non_automation_if({없음, 모름})도 아님. 목록 밖 값('API 있음')은 가능으로 둔다
        (value_aliases 로 바로잡는다). 3D 지도(graph_view3d)·MCP(onto_store)·M4 착수 등급이 이 한 정의를 쓴다 (참조 계산 oracle 은 독립 구현)."""
        a = self.rules["automatable"]
        op, aif = nfc_strip(op), nfc_strip(aif)
        if op in {nfc_strip(x) for x in a["operation_modes"]}:
            return True
        return bool(aif) and not self.is_empty(aif) and aif not in {nfc_strip(x) for x in a["non_automation_if"]}

    # --- 인명 유사 (D6·I29, docs/09 #20) --------------------------------------------
    @cached_property
    def _person_res(self) -> list:
        return [re.compile(self.rules["person_pattern"])] + [re.compile(p) for p in self.rules.get("person_patterns_all") or []]

    def looks_person(self, s) -> bool:
        """인명·연락처처럼 보이는지 — rules.yaml person_pattern·person_patterns_all 중 하나라도 맞으면 True.
        경고·로그에 값을 인용해도 되는지 정할 때 쓴다 (적재기 Loader._q — 맞으면 값 대신 가림 문구)."""
        s = "" if s is None else str(s)
        return any(p.search(s) for p in self._person_res)

    # --- 툴 이름 (6.1) -------------------------------------------------------------
    @cached_property
    def _version_re(self):
        return re.compile(self.rules["version_token_regex"])

    @staticmethod
    def _base(s) -> str:
        return re.sub(r"\([^)]*\)", " ", nfkc(s).lower())

    @staticmethod
    def _alnum(s: str) -> str:
        return re.sub(r"[^0-9a-z가-힣]", "", s)

    @cached_property
    def token_map(self) -> dict[str, str]:
        """공백 토큰 치환 (I2, docs/09 #16) — 'c++' → 'cpp' 처럼 영숫자만 남기기 전에 바꾼다."""
        return {str(k).lower(): str(v).lower() for k, v in (self.rules.get("tool_token_map") or {}).items()}

    @cached_property
    def generic_keys(self) -> set[str]:
        """범용 툴 이름의 정규화 키 (I34 — '자체개발'·'사내툴' 등). 이 키로는 툴을 통합하지 않는다."""
        return {self.tool_key(n) for n in (self.rules.get("generic_tool_names") or [])} - {""}

    def is_generic_key(self, key: str) -> bool:
        """빈 키거나 범용 이름 키 — 행별 '미상:' 키로 두어야 하는 것 (I34)."""
        return key == "" or key in self.generic_keys

    def vendor_key(self, vendor) -> str:
        return self._alnum(self._base(vendor))

    def is_generic_vendor(self, vendor) -> bool:
        """제조사 칸의 범용 이름('자체개발'·'사내' 등, I34) — 접두로 떼지도, 다른 행의 접두 흡수에 쓰지도 않는다 (Leo Q3(b):
        자체개발 툴은 자동 통합하지 않는다). 빈 제조사도 True (쓸 접두가 없다)."""
        v = self.vendor_key(vendor)
        return v == "" or v in self.generic_keys

    def survey_vendors(self, vendors) -> list[str]:
        """조사에 나온 제조사 키 목록 — 범용·빈 제조사는 빼고 긴 것부터 (접두 흡수·연계 SW명 해석용, I1)."""
        return sorted({self.vendor_key(v) for v in vendors if not self.is_generic_vendor(v)}, key=len, reverse=True)

    def tool_key(self, name, vendor=None) -> str:
        """NFKC → 소문자 → 괄호 주석 제거 → 버전 토큰 제거(I2) → 토큰 치환(C++→cpp) → 영숫자·한글만 → 제조사 접두 제거.
        떼고 남는 것이 없으면 떼지 않는다 (I14 — 툴명 = 제조사명, 예: Tecplot). 제조사가 범용 이름('자체개발')이면 떼지 않는다 (I34)."""
        tokens = [self.token_map.get(t, t) for t in self._base(name).split() if not self._version_re.match(t)]
        key = self._alnum("".join(tokens))
        v = self.vendor_key(vendor)
        if v and v not in self.generic_keys and key.startswith(v) and len(key) > len(v):
            key = key[len(v):]
        return key

    # --- 연계 SW명 (6.3) -----------------------------------------------------------
    @cached_property
    def _partner_re(self):
        return re.compile("[" + re.escape(self.rules["partner_separators"]) + "]+")

    def split_partners(self, raw) -> list[str]:
        """NFKC 후 구분자로 나눈다 (I17). 빈 값 토큰·정규화 키가 빈 조각·범용 이름 조각('자체개발')은 버린다 (I16·I34)."""
        if raw is None or self.is_empty(raw):
            return []
        out = []
        for p in self._partner_re.split(nfkc(raw)):
            p = p.strip()
            if not p or p.lower() in self.empty_tokens or self.is_generic_key(self.tool_key(p)):
                continue
            out.append(p)
        return out

    # --- 확장자 (6.2) --------------------------------------------------------------
    @cached_property
    def _ext_seps(self) -> str:
        """구분자 문자 클래스의 내용 — 설정 separators + 모든 공백 문자 (\\r·\\v 포함, 설정과 관계없이 — docs/02 6.2, docs/09 6장 parity)."""
        return re.escape(self.ext_cfg["separators"]) + r"\s"

    @cached_property
    def _ext_sep(self):
        return re.compile("[" + self._ext_seps + "]+")

    @cached_property
    def _ext_ok(self):
        return re.compile(self.ext_cfg["pattern"])

    @cached_property
    def _paren_ext(self):
        """'형식명(.확장자)' (I12, docs/09 #10) — 괄호 안이 '.확장자'(점으로 시작, '*.' 허용; 여럿이면 구분자로 이음)뿐인 괄호와
        그 바로 앞 한 단어(괄호와 사이 공백 허용). 점 없는 괄호('STEP(AP214)')는 맞지 않는다 — 주석으로 뗀다.
        앞 단어가 '.'·'*.' 으로 시작하면 형식 이름이 아니라 확장자라 버리지 않는다 (extensions() 의 take)."""
        sep, dot = self._ext_seps, r"\*?\.[a-z0-9_+\-]+(?:\.[a-z0-9_+\-]+)*"
        return re.compile(rf"(?P<name>[^{sep}()]*)\s*\(\s*(?P<exts>{dot}(?:[{sep}]+{dot})*)\s*\)")

    @cached_property
    def _ext_aliases(self) -> dict[str, str]:
        return {nfkc(k).lower().strip(): str(v) for k, v in (self.ext_cfg.get("aliases") or {}).items()}

    @cached_property
    def non_ext_tokens(self) -> set[str]:
        """확장자 패턴에 맞아도 확장자가 아닌 말 (extensions.yaml non_extension_tokens — or·file·ascii·ap214·parasolid 등)."""
        return {nfkc(t).lower().strip() for t in self.ext_cfg.get("non_extension_tokens") or []}

    @cached_property
    def compound_exts(self) -> set[str]:
        """점으로 이은 묶음 확장자로 인정하는 것 (extensions.yaml compound_extensions — tar.gz·cas.h5 등, 앞 점 무시)."""
        return {nfkc(t).lower().strip().lstrip(".") for t in self.ext_cfg.get("compound_extensions") or []}

    def extensions(self, raw) -> tuple[list[str], bool, list[str]]:
        """(정규화 확장자 목록, 사내 표기 여부, 매핑 못 한 토큰) — I12·I16.
        셀 전체가 빈 값 토큰이면 빈 목록. '형식명(.확장자)' 는 괄호 안 확장자를 쓰고 형식명은 버린다(버린 형식명에 사내 토큰이 있으면 사내 표기).
        그 밖의 괄호 주석은 떼고(안에 사내 토큰이 있으면 사내 표기), 토큰 '사내' 도 사내 표기. 별칭을 먼저 적용하고, 확장자 패턴
        (숫자만 있는 토큰은 아님 — extensions.yaml pattern)에 안 맞거나 non_extension_tokens 면 매핑 못 한 토큰."""
        s = nfkc(raw).lower().strip()
        if s in self.empty_tokens:
            return [], False, []
        inhouse_tokens = [str(t).lower() for t in self.ext_cfg.get("inhouse_tokens", [])]
        inhouse = False

        def take(m) -> str:
            nonlocal inhouse
            name = m.group("name")
            if name.startswith((".", "*.")):                  # 괄호 앞 단어가 '.확장자' 자체 — '.cas(.dat)' 는 둘 다 확장자 (2026-10-12 검토 수리)
                return " " + name + " " + m.group("exts") + " "
            inhouse = inhouse or any(t in name for t in inhouse_tokens)
            return " " + m.group("exts") + " "

        s = self._paren_ext.sub(take, s)
        inhouse = inhouse or any(t in m for m in re.findall(r"\(([^)]*)\)", s) for t in inhouse_tokens)
        s = re.sub(r"\([^)]*\)", " ", s)
        out, bad = [], []
        for tok in self._ext_sep.split(s):
            tok = tok.strip().lstrip(".*").strip()
            if tok in inhouse_tokens:
                inhouse = True
                continue
            if tok in self.empty_tokens:
                continue
            tok = self._ext_aliases.get(tok, tok)          # 별칭이 비확장자 목록보다 먼저 (오버레이 parasolid: x_t 가 이긴다)
            (out if self._ext_ok.match(tok) and tok not in self.non_ext_tokens else bad).append(tok)
        return sorted(set(out)), inhouse, bad

    def unknown_compound(self, exts) -> list[str]:
        """점으로 이은 확장자 가운데 compound_extensions 밖의 것 ('model.stp') — 값은 그대로 쓰고 경고만 (docs/09 #10 Q2)."""
        return [e for e in exts if "." in e and e not in self.compound_exts]
