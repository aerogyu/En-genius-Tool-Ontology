"""사내 반입용 업데이트 파일 만들기 — zip 대신 텍스트 파일 하나 (Leo 2026-09-30 "zip 말고 .py 나 .txt 로").

    python scripts/build_update.py --from f3a4f55 [--to HEAD] [--out offline/] [--skip-tests]
    → offline/EnGenius_update_<from>_to_<to>.py.txt

만든 파일은 표준 라이브러리만 쓰는 파이썬 스크립트다. 두 커밋 사이에 바뀐 저장소 파일을 base64 로 품고 있다.
사내: 확장자를 .py 로 바꿔 아무 폴더에 두고 실행 — 저장소(기본 C:\\EnGenius\\engenius-tool-ontology, 다르면 인자로)를 찾아
바뀐 파일을 쓰고, 덮어쓰기 전 원래 파일은 offline\\backup_<from>_<일시>\\ 에 남긴다 (덮어쓰지 않는다 — 판을 쌓는다).
.bat 은 CRLF 로 쓴다 (cmd 가 LF 만 있는 .bat 을 잘못 읽는 경우가 있다). 실데이터·산출물(data/real, output)은 git 밖이라 들어갈 수 없다.

2026-10-02 (docs/11 3장 1·3·10번):
- 파일마다 **FROM..TO 사이 모든 판의 sha 집합(KNOWN)** 을 싣는다 (FROM 자체 + `git rev-list FROM..TO` 의 각 커밋에서의 내용).
  사내 파일이 TO 와 같으면 '이미 같음', KNOWN 에 있으면 덮어쓰고(백업), 그 밖(= 진짜 로컬 수정)이면 덮지 않고 <파일>.new 를 옆에 쓴다.
  FROM 판 sha 하나만 실으면 누적 파일을 중간 판 위에 적용할 때 두 판 모두에서 바뀐 파일이 전부 K 로 빠지므로(2차 검토 지적) 집합으로 바꿨다.
- <파일>.new 가 이미 있고 내용이 다르면 덮지 않고 <파일>.new.<일시> 로 쓴다 (앞선 업데이트의 .new 보존).
- 백업 폴더에 MANIFEST.txt (A/M/D/K 와 경로, FROM/TO, 일시), 저장소에 offline/installed_commit.txt (TO 전체 해시 + 커밋 번호).
  K 가 1건 이상이면 표식은 전진하되(코드 판은 올라갔으므로) K 목록을 MANIFEST·applied_updates.txt 에 적고 끝에 [주의] 로 다시 알린다.
- 시작 때 installed_commit.txt 의 번호가 FROM 보다 작으면 '중간 업데이트 누락', TO 보다 크면 '역행' 으로 y/N 을 묻는다.
  해시가 FROM·TO 어느 쪽도 아니지만 번호가 사이면 '[..] 기준 판이 다르지만 사이 판 — 그대로 진행' 한 줄. 해시 비교는 앞 7자(짧은 해시)로도 맞는다.
- 만들기 전에 pytest 를 돌리고 실패하면 파일을 만들지 않는다 (--skip-tests 로 건너뜀).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

TEMPLATE = r'''# -*- coding: utf-8 -*-
r"""En-Genius 툴 온톨로지 업데이트 __FROM__ → __TO__ (__DATE__)

사용 (사내 PC):
  1. 이 파일의 확장자를 .py 로 바꾼다 (예: EnGenius_update___FROM___to___TO__.py). 두는 폴더는 어디든 된다.
  2. cmd 에서:  C:\EnGenius\engenius-tool-ontology\.venv\Scripts\python EnGenius_update___FROM___to___TO__.py
     저장소가 다른 곳이면 경로를 붙인다:  ... EnGenius_update___FROM___to___TO__.py D:\어딘가\engenius-tool-ontology
     묻지 않고 진행하려면 --yes 를 붙인다 (경고가 있어도 계속).
  3. 끝나면 scripts\selftest.bat 로 확인.
바꾸는 파일 __N__개 (추가 __NA__ · 변경 __NM__ · 삭제 __ND__). 원래 파일은 offline\backup___FROM___<일시>\ 에 남는다
(그 폴더의 MANIFEST.txt 가 무엇을 어떻게 바꿨는지 적는다 — 되돌리기는 README_offline.md 6-1).
이 파일은 누적이다: __FROM__ 과 __TO__ 사이 어느 판 위에도 적용된다 (사이 판의 파일 내용도 알고 있어 그대로 덮어쓴다).
사내에서 고친 파일(어느 판과도 다른 파일)은 덮지 않고 <파일>.new 를 옆에 쓴다 — 두 파일을 비교해 손으로 합치고 .new 는 지운다.
.venv · output · fuseki-data · data\real 은 건드리지 않는다. 표준 라이브러리만 쓴다.
"""
import base64
import datetime
import hashlib
import shutil
import sys
from pathlib import Path

FROM, TO = "__FROM__", "__TO__"
FROM_FULL, TO_FULL = "__FROM_FULL__", "__TO_FULL__"   # 전체 해시 — offline\installed_commit.txt 1행과 비교
FROM_N, TO_N = __FROM_N__, __TO_N__  # git rev-list --count — 설치 판 순서 비교용 (2행)
FILES = __FILES__      # (경로, TO sha256, KNOWN = FROM..TO 사이 판들의 sha256 튜플, base64) — 추가·변경
DELETED = __DELETED__  # (경로, KNOWN) — 저장소에서 지워진 파일 (백업으로 옮긴다)

ASK = True


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def same_commit(a: str, b: str) -> bool:
    """전체 해시와 짧은 해시(앞 7자 이상)를 섞어 비교해도 맞도록 — 한쪽이 다른 쪽의 접두어면 같은 커밋."""
    a, b = a.strip().lower(), b.strip().lower()
    return len(a) >= 7 and len(b) >= 7 and (a.startswith(b) or b.startswith(a))


def ask_yn(msg: str) -> bool:
    """y/N — EOF(파이프·더블클릭 없는 stdin)나 빈 입력은 N."""
    if not ASK:
        print(f"{msg} → --yes 로 계속")
        return True
    try:
        return input(f"{msg} 계속할까요? [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def read_installed(root: Path):
    """offline/installed_commit.txt → (해시, 번호) 또는 None (없음·형식 불명). 메모장이 BOM 을 붙여도 읽는다(utf-8-sig)."""
    p = root / "offline" / "installed_commit.txt"
    if not p.is_file():
        return None
    lines = [ln.strip() for ln in p.read_text(encoding="utf-8-sig").splitlines() if ln.strip()]
    if len(lines) < 2 or not lines[1].isdigit():
        return None
    return lines[0], int(lines[1])


def write_new(dst: Path, data: bytes, stamp: str) -> Path:
    """<파일>.new 를 쓴다. 이미 있고 내용이 다르면(앞선 업데이트의 .new 를 아직 안 합침) 덮지 않고 <파일>.new.<일시> 로 쓴다."""
    new = dst.with_name(dst.name + ".new")
    if new.is_file() and new.read_bytes() != data:
        alt = dst.with_name(f"{dst.name}.new.{stamp}")
        alt.write_bytes(data)
        return alt
    new.write_bytes(data)
    return new


def main() -> int:
    global ASK
    args = [a for a in sys.argv[1:] if a != "--yes"]
    ASK = "--yes" not in sys.argv[1:]
    root = Path(args[0]) if args else Path(r"C:\EnGenius\engenius-tool-ontology")
    if not ((root / "src" / "engenius_onto").is_dir() and (root / "scripts" / "env.bat").is_file()):
        print(f"[NG] 저장소를 찾지 못함: {root}\n     저장소 폴더(scripts·src·config 가 보이는 곳)를 인자로 준다.")
        return 1

    # 설치 판 순서 검사 — 표식이 없으면 첫 적용으로 본다
    installed = read_installed(root)
    if installed is None:
        print("[..] offline\\installed_commit.txt 없음 — 첫 적용으로 간주")
    else:
        full, n = installed
        if same_commit(full, TO_FULL):
            print(f"[..] 설치 판이 이미 {TO} — 다시 적용해도 같은 결과 (바뀐 파일 없으면 아무것도 안 바꿈)")
        elif n < FROM_N:
            if not ask_yn(f"[주의] 중간 업데이트 누락: 설치 판 {full[:7]}(#{n}) 이 이 파일의 기준 {FROM}(#{FROM_N}) 보다 이전. "
                          f"사이 업데이트를 먼저 적용하는 것이 안전."):
                print("[--] 중단 (아무것도 바꾸지 않았다)")
                return 1
        elif n > TO_N:
            if not ask_yn(f"[주의] 역행: 설치 판 {full[:7]}(#{n}) 이 이 파일의 {TO}(#{TO_N}) 보다 새것 — 적용하면 구판으로 되돌아간다."):
                print("[--] 중단 (아무것도 바꾸지 않았다)")
                return 1
        elif not same_commit(full, FROM_FULL):
            # FROM_N <= n <= TO_N 인데 기준 판이 아님 = 중간 판 위 적용 (누적 파일은 사이 판의 내용도 알고 있다)
            print(f"[..] 기준 판이 다르지만 사이 판: 설치 판 {full[:7]}(#{n}) 은 {FROM}(#{FROM_N})..{TO}(#{TO_N}) 사이 — 그대로 진행")
        # 설치 판 == FROM: 조용히 진행

    for rel, sha_to, _, b64 in FILES:
        if sha(base64.b64decode(b64)) != sha_to:
            print(f"[NG] 파일 손상: {rel} — 업데이트 파일을 다시 받는다 (아무것도 바꾸지 않았다)")
            return 1

    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    backup = root / "offline" / f"backup_{FROM}_{stamp}"
    manifest = []        # (A/M/D/K, 경로)
    same = 0
    for rel, sha_to, known, b64 in FILES:
        data = base64.b64decode(b64)
        dst = root / rel
        if dst.is_file():
            cur = sha(dst.read_bytes())
            if cur == sha_to:
                same += 1
                continue
            if cur not in known:         # FROM..TO 사이 어느 판도 아님 = 사내에서 고친 파일
                new = write_new(dst, data, stamp)
                manifest.append(("K", rel))
                if new.name.endswith(".new"):
                    print(f"[주의] 로컬 수정이 있어 덮지 않음: {rel} (새 판은 {rel}.new)")
                else:
                    print(f"[주의] 로컬 수정이 있어 덮지 않음: {rel} (새 판은 {rel}.new.{stamp} — 기존 .new 보존, 내용이 다름)")
                continue
            (backup / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, backup / rel)
            manifest.append(("M", rel))
        else:
            manifest.append(("A", rel))
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
    for rel, known in DELETED:
        dst = root / rel
        if not dst.is_file():
            continue
        if sha(dst.read_bytes()) not in known:
            manifest.append(("K", rel))
            print(f"[주의] 로컬 수정이 있어 지우지 않음: {rel} (새 판에는 없는 파일)")
            continue
        (backup / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(dst), str(backup / rel))
        manifest.append(("D", rel))

    counts = {k: sum(1 for s, _ in manifest if s == k) for k in "AMDK"}
    kept = [rel for s, rel in manifest if s == "K"]
    if manifest:
        backup.mkdir(parents=True, exist_ok=True)
        with (backup / "MANIFEST.txt").open("w", encoding="utf-8", newline="\n") as f:
            f.write(f"업데이트 {FROM} -> {TO} ({TO_FULL})  적용 {stamp}\n")
            f.write("A 추가(새 판에서 생김, 되돌리려면 지운다) · M 변경(원본은 이 폴더에) · D 삭제(이 폴더로 옮김) · K 로컬 수정 보존(.new 만 씀)\n")
            for status, rel in manifest:
                f.write(f"{status} {rel}\n")
            if kept:
                f.write(f"K {len(kept)}건: <파일>.new 를 손으로 합친 뒤 .new 를 지운다 (README_offline.md 6-1)\n")
    (root / "offline").mkdir(parents=True, exist_ok=True)
    (root / "offline" / "installed_commit.txt").write_text(f"{TO_FULL}\n{TO_N}\n", encoding="utf-8")
    with (root / "offline" / "applied_updates.txt").open("a", encoding="utf-8") as f:
        f.write(f"{stamp}  {FROM} -> {TO}  추가 {counts['A']} · 변경 {counts['M']} · 삭제 {counts['D']} · "
                f"로컬 수정 보존 {counts['K']} · 이미 같음 {same}\n")
        for rel in kept:
            f.write(f"    K {rel}\n")

    print(f"[OK] 업데이트 {FROM} → {TO}: 추가 {counts['A']} · 변경 {counts['M']} · 삭제 {counts['D']} · "
          f"로컬 수정 보존 {counts['K']} · 이미 같음 {same}")
    for status, rel in manifest:
        print(f"     {status} {rel}")
    if manifest:
        print(f"     원래 파일 백업·MANIFEST: {backup}")
    print(f"     설치 판 표식: offline\\installed_commit.txt = {TO} (#{TO_N})")
    if kept:
        print(f"     [주의] 보존된 로컬 수정 {len(kept)}건 — <파일>.new 를 손으로 합친 뒤 .new 를 지운다 (README_offline.md 6-1). "
              f"합치기 전까지 그 파일은 옛 내용으로 돈다")
    print("     다음: scripts\\selftest.bat")
    return 0


if __name__ == "__main__":
    rc = main()
    if sys.stdin and sys.stdin.isatty():      # 더블클릭으로 실행했을 때 창이 바로 닫히지 않게
        try:
            input("엔터를 누르면 닫힙니다")
        except EOFError:
            pass
    sys.exit(rc)
'''


def git(*args: str, binary: bool = False):
    r = subprocess.run(["git", *args], cwd=REPO, check=True, capture_output=True)
    return r.stdout if binary else r.stdout.decode("utf-8").strip()


def normalize(path: str, data: bytes) -> bytes:
    """.bat 은 CRLF 로 (cmd 호환). 그 밖은 그대로."""
    if path.lower().endswith(".bat"):
        return data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    return data


def run_pytest() -> bool:
    """pytest -q 를 돌려 통과 여부 (종료 코드) — 실패하면 업데이트·패키지를 만들지 않는다 (docs/11 3장 3번)."""
    env = dict(os.environ, PYTHONPATH=str(REPO / "src"))
    print("[..] pytest -q (약 90초) — 건너뛰려면 --skip-tests", flush=True)   # 자식 출력보다 먼저 보이게
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=REPO, env=env)
    if r.returncode != 0:
        print(f"[NG] pytest 종료 코드 {r.returncode} — 파일을 만들지 않는다", flush=True)
        return False
    return True


def render(frm: str, to: str, to_full: str, frm_n: int, to_n: int, date: str, files, deleted, frm_full: str = "") -> str:
    """템플릿 채우기 (git 없이도 됨 — 테스트에서 직접 부른다).

    files   = [(경로, TO sha256, KNOWN(sha256 튜플 — FROM..TO 사이 판들, TO 제외), base64, 상태 A/M)]
    deleted = [(경로, KNOWN)]
    frm_full 을 비우면 FROM 짧은 해시로 비교한다 (same_commit 은 접두어 비교).
    """
    body = "[\n" + "".join(f"    ({p!r}, {s!r}, {tuple(k)!r},\n     {b!r}),\n" for p, s, k, b, _ in files) + "]"
    dels = "[\n" + "".join(f"    ({p!r}, {tuple(k)!r}),\n" for p, k in deleted) + "]"
    return (TEMPLATE.replace("__FILES__", body).replace("__DELETED__", dels)
            .replace("__FROM_N__", str(frm_n)).replace("__TO_N__", str(to_n))
            .replace("__FROM_FULL__", frm_full or frm).replace("__TO_FULL__", to_full)
            .replace("__FROM__", frm).replace("__TO__", to).replace("__DATE__", date)
            .replace("__N__", str(len(files) + len(deleted))).replace("__NA__", str(sum(1 for f in files if f[4] == "A")))
            .replace("__NM__", str(sum(1 for f in files if f[4] == "M"))).replace("__ND__", str(len(deleted))))


def tree_blobs(commit: str) -> dict[str, str]:
    """커밋의 추적 파일 전부 → {경로: blob id} (`ls-tree -r -z`: 경로를 따옴표로 감싸지 않는다 — 한글 경로 그대로)."""
    out = {}
    for entry in git("ls-tree", "-r", "-z", commit, binary=True).split(b"\0"):
        if not entry:
            continue
        meta, path = entry.split(b"\t", 1)
        mode, kind, blob = meta.split()
        if kind == b"blob":
            out[path.decode("utf-8")] = blob.decode("ascii")
    return out


def collect(frm: str, to: str):
    """두 커밋 사이 변경 파일 — render() 입력.

    KNOWN = FROM 자체와 `git rev-list --reverse --topo-order FROM..TO` 의 각 커밋에서 그 파일의 (normalize 뒤) sha256 집합 (TO 의 sha 는
    뺀다 — 따로 싣는다). 그 커밋에 파일이 없으면 건너뛴다. 같은 blob 은 한 번만 읽는다.
    TO 의 내용은 rev-list 의 마지막 항목이 아니라 **TO 커밋의 트리에서 직접** 읽는다 — 머지나 커밋 시각이 뒤섞인 저장소에서는
    날짜순 rev-list 의 마지막이 TO 가 아닐 수 있다 (3차 검토 지적). --topo-order 는 KNOWN 의 순서를 부모→자식으로 고정한다.
    """
    commits = [frm] + git("rev-list", "--reverse", "--topo-order", f"{frm}..{to}").splitlines()
    trees = [tree_blobs(c) for c in commits]
    to_tree = tree_blobs(to)
    cache: dict[tuple[bool, str], str] = {}

    def sha_of(path: str, blob: str) -> str:
        key = (path.lower().endswith(".bat"), blob)
        if key not in cache:
            cache[key] = hashlib.sha256(normalize(path, git("cat-file", "blob", blob, binary=True))).hexdigest()
        return cache[key]

    files, deleted = [], []
    for line in git("-c", "core.quotepath=false", "diff", "--name-status", "--no-renames", frm, to).splitlines():
        status, path = line.split("\t", 1)
        known = []
        for tree in trees:
            blob = tree.get(path)
            if blob and (s := sha_of(path, blob)) not in known:
                known.append(s)
        if status == "D":
            deleted.append((path, tuple(known)))
            continue
        data = normalize(path, git("cat-file", "blob", to_tree[path], binary=True))
        sha_to = hashlib.sha256(data).hexdigest()
        files.append((path, sha_to, tuple(s for s in known if s != sha_to), base64.b64encode(data).decode("ascii"), status))
    return files, deleted


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm", required=True, help="사내에 이미 있는 판의 커밋 (예: f3a4f55)")
    ap.add_argument("--to", default="HEAD")
    ap.add_argument("--out", default=str(REPO / "offline"))
    ap.add_argument("--skip-tests", action="store_true", help="pytest 게이트 건너뜀 (리허설·문서만 바뀐 때)")
    args = ap.parse_args()
    frm, to = git("rev-parse", "--short", args.frm), git("rev-parse", "--short", args.to)
    if not args.skip_tests and not run_pytest():
        return 1
    frm_full, to_full = git("rev-parse", args.frm), git("rev-parse", args.to)
    frm_n, to_n = int(git("rev-list", "--count", args.frm)), int(git("rev-list", "--count", args.to))
    files, deleted = collect(frm, to)
    date = git("show", "-s", "--format=%cs", to)
    text = render(frm, to, to_full, frm_n, to_n, date, files, deleted, frm_full=frm_full)
    out = Path(args.out) / f"EnGenius_update_{frm}_to_{to}.py.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    n_commits = len(git("rev-list", f"{frm}..{to}").splitlines())
    print(f"[OK] {out} — 파일 {len(files)} (추가 {sum(1 for f in files if f[4] == 'A')} · 변경 {sum(1 for f in files if f[4] == 'M')}) · "
          f"삭제 {len(deleted)} · {out.stat().st_size / 1e6:.2f} MB · 판 번호 #{frm_n} → #{to_n} (사이 커밋 {n_commits}개의 파일 내용도 품음)")
    for p, _, known, _, st in files:
        mid = len(known) - (1 if st == "M" else 0)       # FROM 판을 뺀, 사이 판에서만 보인 내용 수
        print(f"  {st} {p}" + (f"  (사이 판 내용 {mid})" if mid > 0 else ""))
    for p, _ in deleted:
        print(f"  D {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
