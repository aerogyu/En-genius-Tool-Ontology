"""expected.yaml 다시 만들기 — 손으로 쓴 머리말(expected_head.yaml) + 참조 계산 집계(aggregates).

    python tests/golden/make_expected.py

명세(data/synthetic/survey_spec.yaml)나 oracle.py 를 바꾼 뒤 실행한다. aggregates 는 손으로 고치지 않는다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import oracle  # noqa: E402


def build() -> str:
    spec = yaml.safe_load((REPO / "data" / "synthetic" / "survey_spec.yaml").read_text(encoding="utf-8"))
    agg = oracle.summarize(oracle.compute(spec, REPO))
    head = (HERE / "expected_head.yaml").read_text(encoding="utf-8")
    body = ("\n# ---- 아래는 tests/golden/oracle.py 가 명세에서 계산한 값 (손으로 고치지 말 것 — make_expected.py)\n"
            + yaml.safe_dump({"aggregates": agg}, allow_unicode=True, sort_keys=False, width=160))
    return head.rstrip("\n") + "\n" + body


if __name__ == "__main__":
    text = build()
    yaml.safe_load(text)   # 문법 확인
    (HERE / "expected.yaml").write_text(text, encoding="utf-8", newline="\n")
    print("expected.yaml 갱신")
