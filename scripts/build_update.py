"""사내 반입용 업데이트 파일 만들기 — zip 대신 텍스트 파일 하나 (Leo 2026-09-30 "zip 말고 .py 나 .txt 로").

    python scripts/build_update.py --from f3a4f55 [--to HEAD] [--out offline/]
    → offline/EnGenius_update_<from>_to_<to>.py.txt

만든 파일은 표준 라이브러리만 쓰는 파이썬 스크립트다. 두 커밋 사이에 바뀐 저장소 파일을 base64 로 품고 있다.
사내: 확장자를 .py 로 바꿔 아무 폴더에 두고 실행 — 저장소(기본 C:\\EnGenius\\engenius-tool-ontology, 다르면 인자로)를 찾아
바뀐 파일을 쓰고, 덮어쓰기 전 원래 파일은 offline\\backup_<from>_<일시>\\ 에 남긴다 (덮어쓰지 않는다 — 판을 쌓는다).
.bat 은 CRLF 로 쓴다 (cmd 가 LF 만 있는 .bat 을 잘못 읽는 경우가 있다). 실데이터·산출물(data/real, output)은 git 밖이라 들어갈 수 없다.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

TEMPLATE = r'''# -*- coding: utf-8 -*-
"""En-Genius 툴 온톨로지 업데이트 __FROM__ → __TO__ (__DATE__)

사용 (사내 PC):
  1. 이 파일의 확장자를 .py 로 바꾼다 (예: EnGenius_update___FROM___to___TO__.py). 두는 폴더는 어디든 된다.
  2. cmd 에서:  C:\EnGenius\engenius-tool-ontology\.venv\Scripts\python EnGenius_update___FROM___to___TO__.py
     저장소가 다른 곳이면 경로를 붙인다:  ... EnGenius_update___FROM___to___TO__.py D:\어딘가\engenius-tool-ontology
  3. 끝나면 scripts\doctor.bat 로 확인.
바꾸는 파일 __N__개 (추가 __NA__ · 변경 __NM__ · 삭제 __ND__). 원래 파일은 offline\backup___FROM___<일시>\ 에 남는다.
.venv · output · fuseki-data · data\real 은 건드리지 않는다. 표준 라이브러리만 쓴다.
"""
import base64
import datetime
import hashlib
import shutil
import sys
from pathlib import Path

FROM, TO = "__FROM__", "__TO__"
FILES = __FILES__      # (경로, sha256, base64) — 추가·변경
DELETED = __DELETED__  # 경로 — 저장소에서 지워진 파일 (백업으로 옮긴다)


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\EnGenius\engenius-tool-ontology")
    if not ((root / "src" / "engenius_onto").is_dir() and (root / "scripts" / "env.bat").is_file()):
        print(f"[NG] 저장소를 찾지 못함: {root}\n     저장소 폴더(scripts·src·config 가 보이는 곳)를 인자로 준다.")
        return 1
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    backup = root / "offline" / f"backup_{FROM}_{stamp}"
    added = changed = removed = same = 0
    for rel, sha, b64 in FILES:
        data = base64.b64decode(b64)
        if hashlib.sha256(data).hexdigest() != sha:
            print(f"[NG] 파일 손상: {rel} — 업데이트 파일을 다시 받는다 (아무것도 바꾸지 않았다)" if added + changed == 0
                  else f"[NG] 파일 손상: {rel} — 중간에 멈춤. 백업: {backup}")
            return 1
    for rel, sha, b64 in FILES:
        data = base64.b64decode(b64)
        dst = root / rel
        if dst.is_file():
            if hashlib.sha256(dst.read_bytes()).hexdigest() == sha:
                same += 1
                continue
            (backup / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, backup / rel)
            changed += 1
        else:
            added += 1
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
    for rel in DELETED:
        dst = root / rel
        if dst.is_file():
            (backup / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(backup / rel))
            removed += 1
    log = root / "offline" / "applied_updates.txt"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(f"{stamp}  {FROM} -> {TO}  추가 {added} · 변경 {changed} · 삭제 {removed} · 이미 같음 {same}\n")
    print(f"[OK] 업데이트 {FROM} → {TO}: 추가 {added} · 변경 {changed} · 삭제 {removed} · 이미 같음 {same}")
    if changed or removed:
        print(f"     원래 파일 백업: {backup}")
    print("     다음: scripts\\doctor.bat")
    return 0


if __name__ == "__main__":
    rc = main()
    if sys.stdin and sys.stdin.isatty():
        input("엔터를 누르면 닫힙니다")
    sys.exit(rc)
'''


def git(*args: str, binary: bool = False):
    r = subprocess.run(["git", *args], cwd=REPO, check=True, capture_output=True)
    return r.stdout if binary else r.stdout.decode("utf-8").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm", required=True, help="사내에 이미 있는 판의 커밋 (예: f3a4f55)")
    ap.add_argument("--to", default="HEAD")
    ap.add_argument("--out", default=str(REPO / "offline"))
    args = ap.parse_args()
    frm, to = git("rev-parse", "--short", args.frm), git("rev-parse", "--short", args.to)
    files, deleted = [], []
    for line in git("-c", "core.quotepath=false", "diff", "--name-status", "--no-renames", frm, to).splitlines():
        status, path = line.split("\t", 1)
        if status == "D":
            deleted.append(path)
            continue
        data = git("show", f"{to}:{path}", binary=True)
        if path.lower().endswith(".bat"):
            data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        files.append((path, hashlib.sha256(data).hexdigest(), base64.b64encode(data).decode("ascii"), status))
    body = "[\n" + "".join(f"    ({p!r}, {s!r},\n     {b!r}),\n" for p, s, b, _ in files) + "]"
    date = git("show", "-s", "--format=%cs", to)
    text = (TEMPLATE.replace("__FILES__", body).replace("__DELETED__", repr(deleted))
            .replace("__FROM__", frm).replace("__TO__", to).replace("__DATE__", date)
            .replace("__N__", str(len(files) + len(deleted))).replace("__NA__", str(sum(1 for f in files if f[3] == "A")))
            .replace("__NM__", str(sum(1 for f in files if f[3] == "M"))).replace("__ND__", str(len(deleted))))
    out = Path(args.out) / f"EnGenius_update_{frm}_to_{to}.py.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"[OK] {out} — 파일 {len(files)} (추가 {sum(1 for f in files if f[3] == 'A')} · 변경 {sum(1 for f in files if f[3] == 'M')}) · "
          f"삭제 {len(deleted)} · {out.stat().st_size / 1e6:.2f} MB")
    for p, _, _, st in files:
        print(f"  {st} {p}")
    for p in deleted:
        print(f"  D {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
