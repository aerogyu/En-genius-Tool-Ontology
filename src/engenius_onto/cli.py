"""명령행 진입점: python -m engenius_onto <명령>.

M0 골격 — 각 명령은 해당 마일스톤에서 구현한다.
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys

from engenius_onto import __version__

# 명령 → (설명, 구현 마일스톤)
COMMANDS = {
    "load": ("조사 엑셀을 읽어 survey 그래프(TTL)로 적재", "M3"),
    "derive": ("규칙으로 연결(Feed)·대조·고립을 도출해 derived 그래프 생성", "M4"),
    "report": ("질의 결과로 report.xlsx 와 run_log.json 작성", "M4"),
    "push": ("survey/derived 그래프를 Fuseki 에 named graph 단위로 교체", "M3"),
    "query": ("역량 질의(CQ) 실행", "M4"),
    "all": ("load → derive → report (→ push) 한 번에", "M4"),
}


def _not_yet(name: str) -> int:
    print(f"'{name}' 명령은 아직 구현되지 않았다 ({COMMANDS[name][1]} 예정).", file=sys.stderr)
    return 2


def _java_version() -> str | None:
    java = shutil.which("java")
    if not java:
        return None
    try:
        out = subprocess.run([java, "-version"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    lines = (out.stderr or out.stdout).strip().splitlines()
    return lines[0] if lines else None


def cmd_doctor(_args: argparse.Namespace) -> int:
    """실행 환경 점검 — 사내 반입 후 첫 확인용."""
    from engenius_onto.backends import fuseki_alive, fuseki_dataset_exists
    from engenius_onto.config import fuseki_config

    ok = True
    py = sys.version_info
    py_ok = py >= (3, 10)
    ok &= py_ok
    print(f"[{'OK' if py_ok else 'NG'}] Python {platform.python_version()} (3.10 이상 필요)")

    jv = _java_version()
    print(f"[{'OK' if jv else '--'}] Java: {jv or '없음 (Fuseki 백엔드에만 필요)'}")

    from importlib.metadata import PackageNotFoundError, version

    for dist in ("rdflib", "pydantic", "openpyxl", "pandas", "PyYAML", "linkml", "rfc3986-validator"):
        try:
            print(f"[OK] {dist} {version(dist)}")
        except PackageNotFoundError:
            ok = False
            print(f"[NG] {dist} 없음")

    from engenius_onto.licenses import DENYLIST, audit, denylisted

    bad = denylisted(audit())
    for r in bad:
        ok = False
        print(f"[NG] {r.name} 설치돼 있음 — {DENYLIST[r.name.lower()]}")
    if not bad:
        print("[OK] 금지 패키지 없음 (rfc3987 등)")

    cfg = fuseki_config()
    if fuseki_alive(cfg):
        ds = fuseki_dataset_exists(cfg)
        print(f"[OK] Fuseki {cfg.endpoint} 응답")
        print(f"[{'OK' if ds else 'NG'}] 데이터셋 '{cfg.dataset}' {'있음' if ds else '없음'}")
    else:
        print(f"[--] Fuseki {cfg.endpoint} 응답 없음 (로컬 백엔드만 사용 가능)")
    return 0 if ok else 1


def cmd_licenses(args: argparse.Namespace) -> int:
    """설치 패키지 라이선스 표. 금지(GPL) 항목이 있으면 rc=1 — 반입 심사 자료."""
    from engenius_onto.licenses import FORBIDDEN, MULTI, UNKNOWN, WEAK, audit, to_markdown

    rows = audit()
    print(to_markdown(rows))
    counts = {c: sum(r.cls == c for r in rows) for c in (FORBIDDEN, MULTI, WEAK, UNKNOWN)}
    print(f"\n전체 {len(rows)}개 — " + ", ".join(f"{c} {n}" for c, n in counts.items()))
    return 1 if counts[FORBIDDEN] else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="engenius_onto",
        description="En-Genius 툴 온톨로지 — 툴 간 데이터 연결 도출",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", metavar="<명령>")
    for name, (desc, ms) in COMMANDS.items():
        sp = sub.add_parser(name, help=f"{desc} [{ms}]")
        sp.set_defaults(func=lambda a, n=name: _not_yet(n))
    sp = sub.add_parser("doctor", help="실행 환경 점검 (Python·Java·패키지·Fuseki)")
    sp.set_defaults(func=cmd_doctor)
    sp = sub.add_parser("licenses", help="설치 패키지 라이선스 표 (금지 항목 있으면 rc=1)")
    sp.set_defaults(func=cmd_licenses)
    sp = sub.add_parser("schema", help="LinkML 스키마 점검(lint·양식 매핑·선택지) 후 OWL·SHACL·문서·Pydantic 생성")
    sp.add_argument("--check", action="store_true", help="생성하지 않고 커밋된 생성물이 스키마와 일치하는지만 확인")
    sp.set_defaults(func=lambda a: __import__("engenius_onto.schema_gen", fromlist=["run"]).run(check=a.check))
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        # 한글 Windows 기본 콘솔(cp949)에서 출력 문자 때문에 죽지 않도록
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)
