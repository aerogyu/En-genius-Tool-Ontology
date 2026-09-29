"""명령행 진입점: python -m engenius_onto <명령>.

M3: load·push·apply-review·template-examples 구현. derive·report·query·all 은 M4.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

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
    """JAVA_HOME(scripts\\env.bat 이 잡는다)을 먼저 보고, 없으면 PATH 의 java — 사내 PC 는 JDK zip 만 풀어 PATH 에 java 가 없다."""
    java = None
    home = os.environ.get("JAVA_HOME")
    if home:
        cand = Path(home) / "bin" / ("java.exe" if os.name == "nt" else "java")
        java = str(cand) if cand.is_file() else None
    java = java or shutil.which("java")
    if not java:
        return None
    try:
        out = subprocess.run([java, "-version"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    lines = (out.stderr or out.stdout).strip().splitlines()
    return lines[0] if lines else None


def cmd_load(args: argparse.Namespace) -> int:
    """조사 엑셀 → survey 그래프 TTL·적재 로그·툴 통합 검토표 (output/<실행ID>/), 레지스트리 갱신."""
    from pathlib import Path

    from engenius_onto.survey_load import run_load, summary_lines

    out = run_load(data=args.data, input_dir=Path(args.input) if args.input else None,
                   registry_dir=Path(args.registry) if args.registry else None,
                   out_root=Path(args.out) if args.out else None, shacl=not args.no_shacl)
    print("\n".join(summary_lines(out)))
    for w in out.log["warnings"]:
        print(f"  [경고] {w}")
    return 0


def cmd_push(args: argparse.Namespace) -> int:
    """적재 결과(survey.ttl)와 스키마 OWL 을 Fuseki named graph 로 교체 (Graph Store Protocol PUT)."""
    from pathlib import Path

    from engenius_onto.backends import fuseki_alive, push_graph
    from engenius_onto.config import REPO_ROOT, fuseki_config
    from engenius_onto.schema_gen import GEN_DIR

    cfg = fuseki_config()
    if not fuseki_alive(cfg):
        print(f"Fuseki {cfg.endpoint} 응답 없음 — scripts\\fuseki_start.bat 로 먼저 기동한다.", file=sys.stderr)
        return 1
    run_dir = Path(args.run) if args.run else _latest_run(REPO_ROOT / "output")
    if run_dir is None or not (run_dir / "survey.ttl").is_file():
        print("survey.ttl 이 있는 실행 폴더가 없다 — 먼저 load 를 실행한다.", file=sys.stderr)
        return 1
    for name, path in (("schema", GEN_DIR / "engenius_tool.owl.ttl"), ("survey", run_dir / "survey.ttl")):
        n = push_graph(cfg, cfg.graphs[name], path.read_bytes())
        print(f"[OK] {cfg.graphs[name]} ← {path.name} ({n} triples)")
    if (run_dir / "derived.ttl").is_file():
        n = push_graph(cfg, cfg.graphs["derived"], (run_dir / "derived.ttl").read_bytes())
        print(f"[OK] {cfg.graphs['derived']} ← derived.ttl ({n} triples)")
    return 0


def _latest_run(root):
    runs = sorted(p for p in root.glob("*T*") if p.is_dir()) if root.is_dir() else []
    return runs[-1] if runs else None


def cmd_apply_review(args: argparse.Namespace) -> int:
    from pathlib import Path

    from engenius_onto.survey_load import apply_review

    merged, kept = apply_review(Path(args.csv))
    print(f"config/tool_aliases.yaml 갱신 — 통합 {merged}건, 별개 {kept}건. 다시 load 하면 반영된다.")
    return 0


def cmd_template_examples(args: argparse.Namespace) -> int:
    from pathlib import Path

    from engenius_onto.config import REPO_ROOT
    from engenius_onto.loader import write_template_examples

    path = write_template_examples(Path(args.form) if args.form else REPO_ROOT / "reference" / "SW조사양식_EnGenius_v1.0.xlsx")
    print(f"{path} 갱신")
    return 0


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
    impl = {"load": cmd_load, "push": cmd_push}
    for name, (desc, ms) in COMMANDS.items():
        sp = sub.add_parser(name, help=f"{desc} [{ms}]")
        sp.set_defaults(func=impl.get(name, lambda a, n=name: _not_yet(n)))
        if name == "load":
            sp.add_argument("--data", choices=["synthetic", "real"], default="synthetic",
                            help="data/<synthetic|real>/survey 의 파일과 같은 곳의 registry 사용 (기본 synthetic)")
            sp.add_argument("--input", help="조사 파일 폴더 (--data 대신)")
            sp.add_argument("--registry", help="레지스트리 폴더 (--data 대신)")
            sp.add_argument("--out", help="산출물 상위 폴더 (기본 output/)")
            sp.add_argument("--no-shacl", action="store_true", help="SHACL 검증 생략")
        if name == "push":
            sp.add_argument("--run", help="올릴 실행 폴더 (기본 output/ 의 최신)")
    sp = sub.add_parser("apply-review", help="툴 통합 검토표(tool_review.csv)의 판정을 config/tool_aliases.yaml 에 반영")
    sp.add_argument("csv")
    sp.set_defaults(func=cmd_apply_review)
    sp = sub.add_parser("template-examples", help="양식 xlsx 의 예시 행을 config/template_examples.yaml 로 추출")
    sp.add_argument("--form", help="양식 xlsx (기본 reference/SW조사양식_EnGenius_v1.0.xlsx)")
    sp.set_defaults(func=cmd_template_examples)
    sp = sub.add_parser("doctor", help="실행 환경 점검 (Python·Java·패키지·Fuseki)")
    sp.set_defaults(func=cmd_doctor)
    sp = sub.add_parser("licenses", help="설치 패키지 라이선스 표 (금지 항목 있으면 rc=1)")
    sp.set_defaults(func=cmd_licenses)
    sp = sub.add_parser("schema", help="LinkML 스키마 점검(lint·양식 매핑·선택지) 후 OWL·SHACL·문서·Pydantic 생성")
    sp.add_argument("--check", action="store_true", help="생성하지 않고 커밋된 생성물이 스키마와 일치하는지만 확인")
    sp.set_defaults(func=lambda a: __import__("engenius_onto.schema_gen", fromlist=["run"]).run(check=a.check))
    sp = sub.add_parser("synth", help="합성 조사 파일 생성 (data/synthetic/survey_spec.yaml → 분야별 xlsx)")
    sp.add_argument("--check", action="store_true", help="생성하지 않고 커밋된 파일이 명세와 같은지만 확인")
    sp.set_defaults(func=lambda a: __import__("engenius_onto.synth", fromlist=["run"]).run(check=a.check))
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
