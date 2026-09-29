"""반입 패키지 조립 (docs/04 6장, README_offline.md 1장) — 개발 PC 전용.

    python scripts/build_package.py [--out offline/package_<날짜>] [--downloads C:/EnGenius/tools/downloads]

만드는 것 (git 밖 폴더):
  En-genius-Ontology-<커밋>.zip   git archive HEAD (추적 파일만 — data/real·output 은 들어갈 수 없다)
  wheels_win_amd64_cp310.zip      offline/wheels/*.whl → 'wheels/…' (사내에서 setup_offline.bat 이 offline\ 에 푼다)
  OpenJDK21U-…zip · apache-jena-fuseki-6.2.0.zip   공급자 원본 그대로 (체크섬 = docs/04 1장)
  maps/preview_map_<판>.html · maps/preview_map3d_<판>.html   합성 데이터 연결 지도 (scripts/preview_map*.py 의 MAP_VERSION)
  README_offline.md · README.md(패키지 안내) · SHA256SUMS.txt
작업 트리에 커밋 안 된 변경이 있으면 멈춘다 — 패키지의 저장소 zip 이 HEAD 와 같아야 하므로.
import-package 브랜치에 올릴 때는 덮어쓰지 않는다 (Leo 2026-09-29): 산출물은 판 번호·커밋이 붙은 새 파일로 더하고,
README.md·SHA256SUMS.txt 는 기존 줄을 지우지 않고 합친다 (docs/04 6장).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VENDOR = {
    "OpenJDK21U-jdk_x64_windows_hotspot_21.0.12.1_1.zip": ("Java 21 (Temurin JDK) — Fuseki 실행용 런타임", "GPLv2 + Classpath Exception",
                                                          "https://github.com/adoptium/temurin21-binaries/releases"),
    "apache-jena-fuseki-6.2.0.zip": ("Apache Jena Fuseki 6.2.0 — 그래프 DB", "Apache 2.0", "https://dlcdn.apache.org/jena/binaries/"),
}


def map_version(script: Path) -> str:
    """preview 스크립트의 MAP_VERSION (없으면 v1)."""
    m = re.search(r'^MAP_VERSION = "([^"]+)"', script.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else "v1"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, check=True, capture_output=True, text=True).stdout.strip()


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mb(n: int) -> str:
    return f"{n / 1_000_000:,.1f} MB" if n >= 100_000 else f"{n / 1000:,.0f} KB"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "offline" / f"package_{dt.date.today():%Y%m%d}"))
    ap.add_argument("--downloads", default=r"C:\EnGenius\tools\downloads")
    args = ap.parse_args()

    if git("status", "--porcelain", "--untracked-files=no"):
        print("[NG] 커밋 안 된 변경이 있다 — 커밋한 뒤 다시 (저장소 zip 은 HEAD 로 만든다)")
        return 1
    head = git("rev-parse", "--short", "HEAD")
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    (out / "maps").mkdir(parents=True)

    repo_zip = out / f"En-genius-Ontology-{head}.zip"
    git("archive", "--format=zip", "--prefix=engenius-tool-ontology/", "-o", str(repo_zip), "HEAD")

    wheels = sorted((REPO / "offline" / "wheels").glob("*.whl"))
    if len(wheels) < 90:
        print(f"[NG] offline/wheels 에 wheel 이 {len(wheels)}개 — docs/04 5장대로 먼저 모은다")
        return 1
    wz = out / "wheels_win_amd64_cp310.zip"
    with zipfile.ZipFile(wz, "w", zipfile.ZIP_STORED) as z:  # wheel 은 이미 압축돼 있다
        for w in wheels:
            z.write(w, f"wheels/{w.name}")

    for name in VENDOR:
        shutil.copy2(Path(args.downloads) / name, out / name)

    maps = {}
    for script, html in [("preview_map.py", "preview_map.html"), ("preview_map3d.py", "preview_map3d.html")]:
        subprocess.run([sys.executable, str(REPO / "scripts" / script)], cwd=REPO, check=True, capture_output=True)
        maps[script] = f"maps/{Path(html).stem}_{map_version(REPO / 'scripts' / script)}.html"  # 판 번호를 붙여 덮어쓰지 않게
        shutil.copy2(REPO / "output" / html, out / maps[script])

    shutil.copy2(REPO / "README_offline.md", out / "README_offline.md")

    rows = [
        (repo_zip.name, "저장소 — 코드·스키마·설정·합성 데이터·설치 스크립트·안내", "사내 소유 코드 (의존성은 docs/04)", f"git archive {head}"),
        (wz.name, f"파이썬 패키지 wheel {len(wheels)}개 (Windows x64 · Python 3.10) — 풀지 말고 저장소의 offline\\ 에", "Apache·MIT·BSD 계열 (docs/04 부록 A)", "PyPI (antlr4 4.9.3 은 sdist 를 빌드)"),
        *[(n, d, lic, src) for n, (d, lic, src) in VENDOR.items()],
        (maps["preview_map.py"], "툴 연결 지도 2D (합성 데이터) — 브라우저로 바로 열림", "—", "scripts/preview_map.py"),
        (maps["preview_map3d.py"], "툴 연결 지도 3D (합성 데이터) — 드래그 회전·휠 줌", "—", "scripts/preview_map3d.py"),
        ("README_offline.md", "사내 설치·실행 안내 (저장소 zip 안에도 있음)", "—", "—"),
    ]
    table = "\n".join(f"| `{n}` | {mb((out / n).stat().st_size)} | {d} | {lic} | {src} |" for n, d, lic, src in rows)
    readme = f"""# En-Genius 툴 온톨로지 — 반입 패키지 (연습용 v0.1, {dt.date.today():%Y-%m-%d}, 커밋 `{head}`)

이 브랜치(`import-package`)는 코드가 아니라 **사내(폐쇄망)로 들여갈 파일 보관용**이다. 코드는 `main` 브랜치.
**합성 데이터 연습 전용** — 실데이터 적재는 M3.1(적재기 보강) 판을 다시 반입한 뒤. 그때는 저장소 zip 만 새로 받으면 된다.

## 받는 법

파일 이름을 눌러 들어가 **Download**(원본 받기). 큰 zip 은 Git LFS 라 브랜치 전체 'Download ZIP' 에는 알맹이가 없다 — 파일마다 받는다.
받은 뒤 체크섬 확인 (PowerShell): `Get-FileHash <파일> -Algorithm SHA256` → `SHA256SUMS.txt` 와 비교. cmd 면 `certutil -hashfile <파일> SHA256`.

| 파일 | 크기 | 용도 | 라이선스 | 출처 |
|---|---|---|---|---|
{table}

JDK·Fuseki 는 공급자 원본 그대로다 — 반입 심사에서 원 출처에서 직접 받기를 요구하면 위 출처에서 같은 파일을 받아 체크섬이 같은지 보면 된다
(공급자 체크섬: 저장소 `docs/04_반입목록.md` 1장).

## 들여간 뒤

`README_offline.md` 순서대로: 저장소 zip 풀기 → wheels zip 을 `engenius-tool-ontology\\offline\\` 에 그대로 → JDK·Fuseki zip 을
`C:\\EnGenius\\tools\\` 에 풀기 → `scripts\\setup_offline.bat` 더블클릭 → `scripts\\load.bat` (합성 데이터 연습).
연결 지도는 `maps\\*.html` 을 Edge 로 바로 연다.
"""
    (out / "README.md").write_text(readme, encoding="utf-8", newline="\n")

    files = sorted(p for p in out.rglob("*") if p.is_file())
    sums = "".join(f"{sha256(p)}  {p.relative_to(out).as_posix()}\n" for p in files)
    (out / "SHA256SUMS.txt").write_text(sums, encoding="utf-8", newline="\n")
    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"[OK] {out} — 파일 {len(files) + 1}개, {mb(total)} (저장소 {head}, wheel {len(wheels)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
