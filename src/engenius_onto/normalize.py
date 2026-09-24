"""정규화 (docs/02 6장) — 툴 이름 키, 연계 SW명 분리, 확장자.

규칙 값은 config/rules.yaml·extensions.yaml 에서 읽는다. 세부 해석은 골든 interpretations (I번호).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from engenius_onto.config import load_yaml


def nfkc(s) -> str:
    return unicodedata.normalize("NFKC", "" if s is None else str(s))


def nfc_strip(s) -> str:
    return unicodedata.normalize("NFC", "" if s is None else str(s)).strip()


@dataclass
class Normalizer:
    rules: dict
    ext_cfg: dict

    @classmethod
    def from_config(cls, config_dir: Path | None = None) -> Normalizer:
        return cls(load_yaml("rules.yaml", config_dir), load_yaml("extensions.yaml", config_dir))

    # --- 공통 --------------------------------------------------------------------
    @cached_property
    def empty_tokens(self) -> set[str]:
        return {str(t).lower() for t in self.rules["empty_tokens"]}

    def is_empty(self, s) -> bool:
        """셀 전체가 빈 값 토큰인지 (I16)."""
        return nfkc(s).strip().lower() in self.empty_tokens

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

    def vendor_key(self, vendor) -> str:
        return self._alnum(self._base(vendor))

    def tool_key(self, name, vendor=None) -> str:
        """NFKC → 소문자 → 괄호 주석 제거 → 버전 토큰 제거(I2) → 영숫자·한글만 → 제조사 접두 제거.
        떼고 남는 것이 없으면 떼지 않는다 (I14 — 툴명 = 제조사명, 예: Tecplot)."""
        tokens = [t for t in self._base(name).split() if not self._version_re.match(t)]
        key = self._alnum("".join(tokens))
        v = self.vendor_key(vendor)
        if v and key.startswith(v) and len(key) > len(v):
            key = key[len(v):]
        return key

    # --- 연계 SW명 (6.3) -----------------------------------------------------------
    @cached_property
    def _partner_re(self):
        return re.compile("[" + re.escape(self.rules["partner_separators"]) + "]+")

    def split_partners(self, raw) -> list[str]:
        """NFKC 후 구분자로 나눈다 (I17). 빈 값 토큰·정규화 키가 빈 조각은 버린다 (I16)."""
        if raw is None or self.is_empty(raw):
            return []
        out = []
        for p in self._partner_re.split(nfkc(raw)):
            p = p.strip()
            if not p or p.lower() in self.empty_tokens or not self.tool_key(p):
                continue
            out.append(p)
        return out

    # --- 확장자 (6.2) --------------------------------------------------------------
    @cached_property
    def _ext_sep(self):
        return re.compile("[" + re.escape(self.ext_cfg["separators"]) + "]+")

    @cached_property
    def _ext_ok(self):
        return re.compile(self.ext_cfg["pattern"])

    def extensions(self, raw) -> tuple[list[str], bool, list[str]]:
        """(정규화 확장자 목록, 사내 표기 여부, 매핑 못 한 토큰) — I12·I16.
        셀 전체가 빈 값 토큰이면 빈 목록. 괄호 주석은 떼고(안에 사내 토큰이 있으면 사내 표기), 토큰 '사내' 도 사내 표기."""
        s = nfkc(raw).lower().strip()
        if s in self.empty_tokens:
            return [], False, []
        inhouse_tokens = [str(t).lower() for t in self.ext_cfg.get("inhouse_tokens", [])]
        inhouse = any(t in m for m in re.findall(r"\(([^)]*)\)", s) for t in inhouse_tokens)
        s = re.sub(r"\([^)]*\)", " ", s)
        aliases = {str(k).lower(): str(v) for k, v in self.ext_cfg.get("aliases", {}).items()}
        out, bad = [], []
        for tok in self._ext_sep.split(s):
            tok = tok.strip().lstrip(".*").strip()
            if tok in inhouse_tokens:
                inhouse = True
                continue
            if tok in self.empty_tokens:
                continue
            tok = aliases.get(tok, tok)
            (out if self._ext_ok.match(tok) else bad).append(tok)
        return sorted(set(out)), inhouse, bad
