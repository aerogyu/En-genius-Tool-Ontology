"""명령행 진입점: python -m engenius_onto <명령>.

M3: load·push·apply-review·template-examples 구현, M3.1: diag. derive·report·query·all 은 M4.
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


def _config_error(e: Exception) -> int:
    """설정 파일 오류(ConfigError)는 traceback 없이 한 줄로 — 사내에서 오버레이를 손으로 고치다 생기는 것 (docs/09 C15)."""
    print(f"[NG] 설정 오류: {e}", file=sys.stderr)
    return 2                                                      # load.bat 안내문의 '2 stopped' — 적재가 시작조차 안 됐다 (1 은 경고 있음)


def cmd_load(args: argparse.Namespace) -> int:
    """조사 엑셀 → survey 그래프 TTL·적재 로그·툴 통합 검토표 (output/<실행ID>/), 레지스트리 갱신."""
    from pathlib import Path

    from engenius_onto.config import ConfigError
    from engenius_onto.survey_load import run_load, summary_lines

    try:
        out = run_load(data=args.data, input_dir=Path(args.input) if args.input else None,
                       registry_dir=Path(args.registry) if args.registry else None,
                       out_root=Path(args.out) if args.out else None, shacl=not args.no_shacl,
                       overlay_dir=Path(args.overlay) if args.overlay else None, overlay=not args.no_overlay)
    except ConfigError as e:
        return _config_error(e)
    print("\n".join(summary_lines(out)))
    ov = out.log.get("config_overlay") or {}
    print(f"  설정 오버레이: {'예 (' + ', '.join(ov.get('files') or []) + ')' if ov.get('used') else '아니오'}")
    for w in out.log["warnings"]:
        print(f"  [경고] {w}")
    print(f"  수정 요청표(파일별): {out.out_dir / 'fix_requests'}")
    print(f"  진단 요약(반출용, 값 없음): {out.out_dir / 'diag.txt'}")
    return 0


def cmd_diag(args: argparse.Namespace) -> int:
    """적재 결과의 진단 요약 — 경고 종류·열·파트별 건수만 (셀 값·툴명·경로·인명 없음). 밖으로 가져갈 수 있는 것 (docs/08 8장)."""
    from pathlib import Path

    from engenius_onto.config import REPO_ROOT, ConfigError
    from engenius_onto.survey_load import diag_text

    run_dir = Path(args.run) if args.run else _latest_run(REPO_ROOT / "output")
    if run_dir is None or not (run_dir / "load_log.json").is_file():
        print("load_log.json 이 있는 실행 폴더가 없다 — 먼저 load 를 실행한다.", file=sys.stderr)
        return 1
    try:
        text = diag_text(run_dir)
    except ConfigError as e:
        return _config_error(e)
    (run_dir / "diag.txt").write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


def cmd_push(args: argparse.Namespace) -> int:
    """적재 결과(survey.ttl)와 스키마 OWL 을 Fuseki named graph 로 교체 (Graph Store Protocol PUT).
    실행 폴더에 derived.ttl 이 없으면 derived 그래프를 **비운다** (docs/09 #25a — 옛 파생 결과가 새 survey 와 섞이지 않게)."""
    from pathlib import Path

    from engenius_onto.backends import delete_graph, fuseki_alive, push_graph
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
    if not (run_dir / "derived.ttl").is_file():
        delete_graph(cfg, cfg.graphs["derived"])                 # survey 를 올리기 전에 — 새 survey 와 옛 derived 가 같이 있는 순간이 없게
        print(f"[OK] derived 비움 — {cfg.graphs['derived']} (이 실행에 derived.ttl 없음; 이전 도출 결과가 새 survey 와 섞이지 않게)")
    for name, path in (("schema", GEN_DIR / "engenius_tool.owl.ttl"), ("survey", run_dir / "survey.ttl")):
        n = push_graph(cfg, cfg.graphs[name], path.read_bytes())
        print(f"[OK] {cfg.graphs[name]} ← {path.name} ({n} triples)")
    if (run_dir / "derived.ttl").is_file():
        n = push_graph(cfg, cfg.graphs["derived"], (run_dir / "derived.ttl").read_bytes())
        print(f"[OK] {cfg.graphs['derived']} ← derived.ttl ({n} triples)")
    return 0


def _latest_run(root):
    """최근 실행 폴더 — 실데이터 실행이 있으면 그것을 먼저 (survey_load.latest_run)."""
    from engenius_onto.survey_load import latest_run

    return latest_run(root)


def cmd_apply_review(args: argparse.Namespace) -> int:
    """검토표 판정 → tool_aliases.yaml. 쓰는 곳: --config-dir, 없으면 검토표가 나온 실행이 합성이면 config/, 아니면 data/real/config (C15).
    공개 별칭(config/tool_aliases.yaml)은 쓰는 곳이 data/real/config 이거나 --with-public-aliases 일 때만 사슬 검사에 섞는다."""
    from pathlib import Path

    from engenius_onto.config import REAL_CONFIG_DIR, REPO_ROOT, ConfigError
    from engenius_onto.survey_load import apply_review, review_target_dir

    target = Path(args.config_dir) if args.config_dir else review_target_dir(Path(args.csv))
    overlay = bool(args.with_public_aliases) or target.resolve() == REAL_CONFIG_DIR.resolve()
    try:
        r = apply_review(Path(args.csv), target_dir=target, overlay=overlay)
    except ConfigError as e:
        return _config_error(e)
    except ValueError as e:
        print(f"[NG] {e}", file=sys.stderr)
        return 1
    try:
        shown = str(r.path.resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        shown = str(r.path)
    print(f"{shown} 갱신 — 통합 {r.merged}건, 별개 {r.kept}건, 통합 해제 {r.undone}건. 다시 load 하면 반영된다.")
    if r.encoding != "utf-8-sig":
        print(f"  [주의] 검토표를 {r.encoding} 로 읽음 — 엑셀 '다른 이름으로 저장' 은 'CSV UTF-8(쉼표로 분리)' 를 고른다")
    if target.resolve() != (REPO_ROOT / "config").resolve():
        print("  (사내 오버레이 — 실 툴명이 들어 있으니 밖으로 가져가지 않는다. --data real 적재가 자동으로 읽는다)")
    return 0


def cmd_template_examples(args: argparse.Namespace) -> int:
    from pathlib import Path

    from engenius_onto.config import REPO_ROOT
    from engenius_onto.loader import write_template_examples

    forms = [Path(f) for f in args.form] if args.form else [REPO_ROOT / "reference" / "SW조사양식_EnGenius_v1.0.xlsx",
                                                          REPO_ROOT / "reference" / "Tool조사양식_EnGenius_v1.1.xlsx"]
    path = write_template_examples(forms)
    print(f"{path} 갱신")
    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    """실행 환경 점검 — 사내 반입 후 첫 확인용."""
    from engenius_onto.backends import fuseki_alive, fuseki_dataset_exists
    from engenius_onto.config import fuseki_config

    from engenius_onto.config import installed_version

    ok = True
    print(f"[--] 설치 판 {installed_version()} ({installed_version().source})")
    py = sys.version_info
    py_ok = py >= (3, 10)
    ok &= py_ok
    print(f"[{'OK' if py_ok else 'NG'}] Python {platform.python_version()} (3.10 이상 필요)")
    utf8 = bool(sys.flags.utf8_mode)                              # 한국어 Windows(cp949)에서 스키마·설정 YAML 을 읽으려면 필수 — scripts\env.bat 가 PYTHONUTF8=1 을 둔다
    utf8_msg = "켜짐" if utf8 else "꺼짐 - scripts\\env.bat 를 거쳐 실행 (set PYTHONUTF8=1); 아니면 linkml·yaml 이 cp949 로 읽어 실패"   # (f-string 안에 역슬래시 금지, 3.10)
    print(f"[{'OK' if utf8 else 'NG'}] Python UTF-8 모드 {utf8_msg}")

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
            ov = sp.add_mutually_exclusive_group()               # 둘을 같이 주면 argparse 오류 (rc 2)
            ov.add_argument("--overlay", help="설정 오버레이 폴더 (기본: --data real 이면 data/real/config, 있을 때)")
            ov.add_argument("--no-overlay", action="store_true", help="설정 오버레이를 쓰지 않음 (--overlay 와 같이 못 쓴다)")
        if name == "push":
            sp.add_argument("--run", help="올릴 실행 폴더 (기본 output/ 의 최신)")
    sp = sub.add_parser("apply-review", help="툴 통합 검토표(tool_review.csv)의 판정을 tool_aliases.yaml 에 반영 "
                                             "(실데이터 실행이면 data/real/config, 합성이면 config/)")
    sp.add_argument("csv")
    sp.add_argument("--config-dir", help="쓸 설정 폴더 (기본: 검토표가 나온 실행으로 판단). 독립 사본이면 공개 별칭을 섞지 않는다 "
                                         "(섞으려면 --with-public-aliases)")
    sp.add_argument("--with-public-aliases", action="store_true", dest="with_public_aliases",
                    help="저장소 config/tool_aliases.yaml 의 공개 별칭도 사슬 검사에 섞음 (data/real/config 에 쓸 때는 자동). "
                         "load 의 --overlay(오버레이 폴더 경로)와는 다른 옵션")
    sp.set_defaults(func=cmd_apply_review)
    sp = sub.add_parser("template-examples", help="양식 xlsx 의 예시 행을 config/template_examples.yaml 로 추출")
    sp.add_argument("--form", action="append", help="양식 xlsx, 여러 번 가능 (기본: reference 의 v1.0 + v1.1 양식)")
    sp.set_defaults(func=cmd_template_examples)
    sp = sub.add_parser("diag", help="적재 진단 요약 — 경고 종류·열·파트별 건수만 (값 없음, 반출용)")
    sp.add_argument("--run", help="실행 폴더 (기본 output/ 의 최신)")
    sp.set_defaults(func=cmd_diag)
    sp = sub.add_parser("mcp", help="Tool Ontology MCP 서버 (stdio, 읽기 전용 도구 8개 — 사내 AI 플랫폼 에이전트용, M6 v0)")
    sp.add_argument("--run", help="실행 폴더 고정 (기본: 최신 실데이터 실행 — 재적재하면 자동으로 새 것을 읽는다)")
    sp.add_argument("--data", choices=["real", "synthetic"], default="real", help="최신 실행을 고를 때 먼저 볼 데이터 (기본 real)")
    sp.add_argument("--backend", choices=["local", "fuseki"], default="local",
                    help="local = survey.ttl 을 rdflib 로 (Fuseki 불필요, 기본) · fuseki = config/fuseki.yaml 의 Fuseki 에 SPARQL")
    sp.add_argument("--check", action="store_true", help="서버를 띄우지 않고 도구를 한 번씩 불러 본다 (자기 점검)")
    sp.set_defaults(func=lambda a: __import__("engenius_onto.mcp_server", fromlist=["run"]).run(
        run_dir=a.run, backend=a.backend, check=a.check, data=a.data))
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
