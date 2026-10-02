"""scripts/build_update.py 가 만드는 업데이트 스크립트(템플릿)의 적용 로직 — 임시 폴더의 가짜 저장소에서 실제로 실행한다.

검사하는 것 (docs/11 3장 1·3·10번, 2차 검토 수리):
- 현재 sha == TO → 이미 같음 / 파일 없음·현재 sha ∈ KNOWN(FROM..TO 사이 판) → 쓴다 / 그 밖(로컬 수정) → 덮지 않고 <파일>.new
- 누적 파일을 중간 판 위에 적용: 중간 판 내용은 KNOWN 에 있으니 덮어쓴다 (K 가 아니다), '[..] 기준 판이 다르지만 사이 판' 한 줄
- <파일>.new 가 이미 있고 내용이 다르면 <파일>.new.<일시> 로 쓰고 기존 .new 보존
- 삭제 파일도 로컬 수정이면 지우지 않는다
- 백업 폴더 MANIFEST.txt(A/M/D/K), offline/installed_commit.txt(전체 해시 + 번호), applied_updates.txt(K 목록 포함)
- 설치 판 순서 검사: 번호 < FROM → '중간 업데이트 누락' y/N, > TO → '역행' y/N, EOF 는 N, --yes 는 계속
- 표식은 BOM(utf-8-sig)·짧은 해시(앞 7자)로도 읽힌다
- 손상(sha 불일치)이면 아무것도 바꾸지 않는다
- collect(): 임시 git 저장소에서 FROM·중간·TO 세 판의 sha 가 KNOWN 에 모이는지 (git 이 없으면 skip)
- collect(): 머지·커밋 시각 뒤섞임에서도 TO 내용은 TO 트리에서, KNOWN 은 --topo-order (3차 검토 — rev-list 마지막 ≠ TO 일 수 있음)
- selftest.bat: installed_commit.txt 에 BOM 이 있어도 결과 파일 이름은 selftest_<7자>.txt (cmd /c 로 실제 실행, Windows 전용)
"""
from __future__ import annotations

import base64
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_update  # noqa: E402

FROM_FULL = "1111111" + "f" * 33
TO_FULL = "2222222" + "a" * 33
FROM_N, TO_N = 60, 63


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


OLD = {  # FROM 판 내용
    "config/a.yaml": b"a: old\n",
    "config/b.yaml": b"b: old\n",
    "config/d.yaml": b"d: old\n",
    "config/e.yaml": b"e: old\n",
    "scripts/x.bat": b"@echo new\r\n",
}
MID = {  # 중간 판(#61·#62)에서만 보인 내용 — KNOWN 에 들어간다
    "config/a.yaml": b"a: mid\n",
    "config/d.yaml": b"d: mid\n",
}
NEW = {  # TO 판 내용
    "config/a.yaml": b"a: new\n",
    "config/b.yaml": b"b: new\n",
    "config/c.yaml": b"c: new\n",   # 추가
    "scripts/x.bat": b"@echo new\r\n",  # 이미 같음
}


def _known(p: str) -> tuple:
    return tuple(_sha(d) for d in (OLD.get(p), MID.get(p)) if d is not None)


def _files():
    return [(p, _sha(NEW[p]), _known(p), _b64(NEW[p]), "M" if p in OLD else "A") for p in NEW]


def _deleted():
    return [("config/d.yaml", _known("config/d.yaml")), ("config/e.yaml", _known("config/e.yaml"))]


def _make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "src" / "engenius_onto").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "scripts" / "env.bat").write_bytes(b"@echo off\r\n")
    for rel, data in OLD.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)
    (root / "config" / "b.yaml").write_bytes(b"b: edited in-house\n")   # 로컬 수정
    (root / "config" / "e.yaml").write_bytes(b"e: edited in-house\n")   # 삭제 대상인데 로컬 수정
    return root


def _write_update(tmp_path: Path, files=None, deleted=None) -> Path:
    text = build_update.render("1111111", "2222222", TO_FULL, FROM_N, TO_N, "2026-10-02",
                               files if files is not None else _files(), deleted if deleted is not None else _deleted(),
                               frm_full=FROM_FULL)
    assert "__" not in text.replace("__name__", "").replace("__main__", "").replace("__file__", ""), "채워지지 않은 자리"
    p = tmp_path / "EnGenius_update_1111111_to_2222222.py"
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


def _run(script: Path, root: Path, *extra: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, str(script), str(root), *extra], input=stdin, capture_output=True,
                          text=True, encoding="utf-8", env=env, cwd=script.parent)


def _marker(root: Path, full: str, n: int, encoding: str = "utf-8") -> None:
    (root / "offline").mkdir(exist_ok=True)
    (root / "offline" / "installed_commit.txt").write_text(f"{full}\n{n}\n", encoding=encoding)


def test_apply_writes_backs_up_and_keeps_local_edits(tmp_path):
    root = _make_repo(tmp_path)
    r = _run(_write_update(tmp_path), root, "--yes")
    assert r.returncode == 0, r.stdout + r.stderr
    # M: 쓰고 원본은 백업
    assert (root / "config" / "a.yaml").read_bytes() == NEW["config/a.yaml"]
    backups = sorted((root / "offline").glob("backup_1111111_*"))
    assert len(backups) == 1
    assert (backups[0] / "config" / "a.yaml").read_bytes() == OLD["config/a.yaml"]
    # K: 로컬 수정은 그대로, .new 가 옆에
    assert (root / "config" / "b.yaml").read_bytes() == b"b: edited in-house\n"
    assert (root / "config" / "b.yaml.new").read_bytes() == NEW["config/b.yaml"]
    assert "[주의] 로컬 수정이 있어 덮지 않음: config/b.yaml (새 판은 config/b.yaml.new)" in r.stdout
    # A: 새 파일
    assert (root / "config" / "c.yaml").read_bytes() == NEW["config/c.yaml"]
    # D: 백업으로 이동 / 로컬 수정된 삭제 대상은 남긴다
    assert not (root / "config" / "d.yaml").exists()
    assert (backups[0] / "config" / "d.yaml").read_bytes() == OLD["config/d.yaml"]
    assert (root / "config" / "e.yaml").read_bytes() == b"e: edited in-house\n"
    assert "지우지 않음: config/e.yaml" in r.stdout
    # 이미 같음
    assert "이미 같음 1" in r.stdout
    # MANIFEST (K 목록 요약 줄 포함)
    manifest = (backups[0] / "MANIFEST.txt").read_text(encoding="utf-8").splitlines()
    assert manifest[0].startswith(f"업데이트 1111111 -> 2222222 ({TO_FULL})  적용 ")
    assert set(manifest[2:7]) == {"M config/a.yaml", "K config/b.yaml", "A config/c.yaml", "D config/d.yaml", "K config/e.yaml"}
    assert manifest[7].startswith("K 2건:")
    # 설치 판 표식은 K 가 있어도 전진·적용 기록에 K 목록
    assert (root / "offline" / "installed_commit.txt").read_text(encoding="utf-8") == f"{TO_FULL}\n{TO_N}\n"
    log = (root / "offline" / "applied_updates.txt").read_text(encoding="utf-8").splitlines()
    assert "1111111 -> 2222222  추가 1 · 변경 1 · 삭제 1 · 로컬 수정 보존 2 · 이미 같음 1" in log[0]
    assert log[1:] == ["    K config/b.yaml", "    K config/e.yaml"]
    # 끝에 바뀐 파일 목록과 K 재안내
    assert "     M config/a.yaml" in r.stdout and "     A config/c.yaml" in r.stdout and "     D config/d.yaml" in r.stdout
    assert "[주의] 보존된 로컬 수정 2건" in r.stdout and ".new 를 지운다" in r.stdout


def test_intermediate_version_is_overwritten_not_kept(tmp_path):
    """설치 #61(중간 판: a.yaml=mid, d.yaml=mid) 에 #60→#63 누적 파일 — 중간 판 내용은 KNOWN 이라 M/D, K 가 아니다."""
    root = _make_repo(tmp_path)
    (root / "config" / "a.yaml").write_bytes(MID["config/a.yaml"])
    (root / "config" / "d.yaml").write_bytes(MID["config/d.yaml"])
    _marker(root, "3333333" + "c" * 33, FROM_N + 1)
    r = _run(_write_update(tmp_path), root, stdin="")       # 묻지 않는다
    assert r.returncode == 0, r.stdout + r.stderr
    assert "[..] 기준 판이 다르지만 사이 판: 설치 판 3333333(#61) 은 1111111(#60)..2222222(#63) 사이 — 그대로 진행" in r.stdout
    assert (root / "config" / "a.yaml").read_bytes() == NEW["config/a.yaml"]
    assert not (root / "config" / "a.yaml.new").exists()
    assert not (root / "config" / "d.yaml").exists()
    backup = next((root / "offline").glob("backup_1111111_*"))
    assert (backup / "config" / "a.yaml").read_bytes() == MID["config/a.yaml"]       # 백업은 중간 판 원본
    assert (backup / "config" / "d.yaml").read_bytes() == MID["config/d.yaml"]
    manifest = (backup / "MANIFEST.txt").read_text(encoding="utf-8").splitlines()
    assert "M config/a.yaml" in manifest and "D config/d.yaml" in manifest
    assert "로컬 수정 보존 2 ·" in r.stdout        # b.yaml·e.yaml 만 (진짜 로컬 수정) — a·d 는 K 가 아니다
    assert r.stderr == ""                         # 템플릿 컴파일 경고(잘못된 이스케이프 등) 없음
    assert (root / "offline" / "installed_commit.txt").read_text(encoding="utf-8") == f"{TO_FULL}\n{TO_N}\n"


def test_installed_equals_from_is_quiet(tmp_path):
    root = _make_repo(tmp_path)
    _marker(root, FROM_FULL, FROM_N)
    r = _run(_write_update(tmp_path), root, stdin="")
    assert r.returncode == 0 and "[..]" not in r.stdout.split("[OK]")[0]


def test_existing_dot_new_with_other_content_is_preserved(tmp_path):
    """앞선 업데이트의 b.yaml.new 를 아직 안 합친 상태 — 덮지 않고 .new.<일시> 로 쓴다. 같은 내용이면 새 파일을 만들지 않는다."""
    root = _make_repo(tmp_path)
    (root / "config" / "b.yaml.new").write_bytes(b"b: from previous update\n")
    r = _run(_write_update(tmp_path), root, "--yes")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (root / "config" / "b.yaml.new").read_bytes() == b"b: from previous update\n"
    alts = sorted((root / "config").glob("b.yaml.new.*"))
    assert len(alts) == 1 and alts[0].read_bytes() == NEW["config/b.yaml"]
    assert f"(새 판은 config/b.yaml.new.{alts[0].name.rsplit('.', 1)[1]} — 기존 .new 보존" in r.stdout
    assert (root / "config" / "b.yaml").read_bytes() == b"b: edited in-house\n"
    # 같은 내용의 .new 가 있으면 그대로 두고 추가 파일 없음
    root2 = _make_repo(tmp_path / "second")
    (root2 / "config" / "b.yaml.new").write_bytes(NEW["config/b.yaml"])
    r = _run(_write_update(tmp_path / "second"), root2, "--yes")
    assert r.returncode == 0 and not list((root2 / "config").glob("b.yaml.new.*"))
    assert "(새 판은 config/b.yaml.new)" in r.stdout


def test_reapply_is_idempotent(tmp_path):
    root = _make_repo(tmp_path)
    upd = _write_update(tmp_path)
    assert _run(upd, root, "--yes").returncode == 0
    r = _run(upd, root, "--yes")
    assert r.returncode == 0
    assert "설치 판이 이미 2222222" in r.stdout
    assert "추가 0 · 변경 0 · 삭제 0" in r.stdout and "이미 같음 3" in r.stdout
    assert (root / "config" / "b.yaml").read_bytes() == b"b: edited in-house\n"   # 로컬 수정은 여전히 보존


@pytest.mark.parametrize("n, msg", [(FROM_N - 1, "중간 업데이트 누락"), (TO_N + 1, "역행")])
def test_order_check_eof_means_no(tmp_path, n, msg):
    root = _make_repo(tmp_path)
    _marker(root, "b" * 40, n)
    r = _run(_write_update(tmp_path), root, stdin="")          # EOF → N
    assert r.returncode == 1
    assert msg in r.stdout and "중단" in r.stdout
    assert (root / "config" / "a.yaml").read_bytes() == OLD["config/a.yaml"]      # 아무것도 안 바꿈
    assert not (root / "config" / "c.yaml").exists()
    assert (root / "offline" / "installed_commit.txt").read_text(encoding="utf-8").splitlines()[1] == str(n)


def test_order_check_yes_continues(tmp_path):
    root = _make_repo(tmp_path)
    _marker(root, "b" * 40, TO_N + 5)
    r = _run(_write_update(tmp_path), root, stdin="y\n")
    assert r.returncode == 0, r.stdout
    assert "역행" in r.stdout
    assert (root / "config" / "a.yaml").read_bytes() == NEW["config/a.yaml"]
    assert (root / "offline" / "installed_commit.txt").read_text(encoding="utf-8") == f"{TO_FULL}\n{TO_N}\n"


def test_order_in_range_is_quiet_and_missing_marker_is_first_apply(tmp_path):
    root = _make_repo(tmp_path)
    r = _run(_write_update(tmp_path), root, stdin="")           # 표식 없음 — 물어보지 않는다
    assert r.returncode == 0 and "첫 적용으로 간주" in r.stdout and "[주의] 중간" not in r.stdout
    root2 = _make_repo(tmp_path / "second")
    _marker(root2, "c" * 40, FROM_N + 1)
    r = _run(_write_update(tmp_path / "second"), root2, stdin="")
    assert r.returncode == 0 and "중간 업데이트 누락" not in r.stdout and "역행" not in r.stdout and "첫 적용" not in r.stdout
    assert "사이 판" in r.stdout


@pytest.mark.parametrize("first_line, encoding", [(TO_FULL, "utf-8-sig"), (TO_FULL[:7], "utf-8"), (TO_FULL[:7].upper(), "utf-8-sig")])
def test_marker_reads_bom_and_short_hash(tmp_path, first_line, encoding):
    """메모장이 BOM 을 붙이거나 사람이 앞 7자만 적어도 '이미 같음' 으로 알아본다."""
    root = _make_repo(tmp_path)
    _marker(root, first_line, TO_N, encoding=encoding)
    r = _run(_write_update(tmp_path), root, stdin="")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "설치 판이 이미 2222222" in r.stdout


def test_corrupt_payload_changes_nothing(tmp_path):
    root = _make_repo(tmp_path)
    files = _files()
    p, s, k, b, st = files[0]
    files[0] = (p, s, k, _b64(b"tampered\n"), st)
    r = _run(_write_update(tmp_path, files=files), root, "--yes")
    assert r.returncode == 1 and "[NG] 파일 손상" in r.stdout
    assert (root / "config" / "a.yaml").read_bytes() == OLD["config/a.yaml"]
    assert not (root / "config" / "c.yaml").exists() and not (root / "offline").exists()


def test_repo_not_found(tmp_path):
    r = _run(_write_update(tmp_path), tmp_path / "nowhere", "--yes")
    assert r.returncode == 1 and "[NG] 저장소를 찾지 못함" in r.stdout


def test_normalize_bat_crlf():
    assert build_update.normalize("scripts/x.bat", b"a\nb\r\n") == b"a\r\nb\r\n"
    assert build_update.normalize("config/x.yaml", b"a\nb\r\n") == b"a\nb\r\n"


# ── collect(): 실제 git 저장소에서 KNOWN 이 모이는지 (개발 PC 전용 — git 이 없으면 skip) ─────────────────────────────

@pytest.mark.skipif(shutil.which("git") is None, reason="git 없음")
def test_collect_gathers_shas_of_every_commit_between(tmp_path, monkeypatch):
    repo = tmp_path / "g"
    repo.mkdir()

    def g(*args):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.autocrlf=false", *args],
                              cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()

    def commit(msg, **files):
        for rel, data in files.items():
            if data is None:
                (repo / rel).unlink()
            else:
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                (repo / rel).write_bytes(data)
        g("add", "-A")
        g("commit", "-q", "-m", msg)
        return g("rev-parse", "--short", "HEAD")

    g("init", "-q")
    c0 = commit("v0", **{"a.yaml": b"a: v0\n", "gone.yaml": b"gone: v0\n", "same.yaml": b"same\n", "s.bat": b"@echo v0\n"})
    c1 = commit("v1", **{"a.yaml": b"a: v1\n", "gone.yaml": b"gone: v1\n", "added.yaml": b"added: v1\n", "s.bat": b"@echo v1\n"})
    c2 = commit("v2", **{"a.yaml": b"a: v2\n", "gone.yaml": None, "added.yaml": b"added: v2\n", "s.bat": b"@echo v2\r\n"})
    c3 = commit("v3", **{"a.yaml": b"a: v3\n", "한글.md": "# 한글 경로\n".encode("utf-8")})
    monkeypatch.setattr(build_update, "REPO", repo)

    files, deleted = build_update.collect(c0, c3)
    by_path = {p: (s, k, b64, st) for p, s, k, b64, st in files}
    # a.yaml: FROM(v0)·사이(v1·v2) 가 KNOWN, TO(v3) 는 따로. 순서는 FROM 부터
    s, k, b64, st = by_path["a.yaml"]
    assert st == "M" and s == _sha(b"a: v3\n") and base64.b64decode(b64) == b"a: v3\n"
    assert k == (_sha(b"a: v0\n"), _sha(b"a: v1\n"), _sha(b"a: v2\n"))
    # added.yaml: FROM 에 없음 → A, KNOWN 은 사이 판(v1)만 (v2 == TO 는 뺀다)
    s, k, _, st = by_path["added.yaml"]
    assert st == "A" and s == _sha(b"added: v2\n") and k == (_sha(b"added: v1\n"),)
    # 한글 경로 추가, 사이 판 없음
    s, k, _, st = by_path["한글.md"]
    assert st == "A" and k == ()
    # .bat 은 normalize(CRLF) 뒤 sha — v2 는 이미 CRLF 라 TO 와 같음 → KNOWN 에서 빠짐
    s, k, b64, _ = by_path["s.bat"]
    assert base64.b64decode(b64) == b"@echo v2\r\n" and k == (_sha(b"@echo v0\r\n"), _sha(b"@echo v1\r\n"))
    # same.yaml 은 안 바뀌어 목록에 없음
    assert "same.yaml" not in by_path
    # gone.yaml: 삭제, KNOWN 은 v0·v1
    assert deleted == [("gone.yaml", (_sha(b"gone: v0\n"), _sha(b"gone: v1\n")))]
    # render 에 그대로 들어가 템플릿이 평가된다
    text = build_update.render(c0, c3, "d" * 40, 1, 4, "2026-10-02", files, deleted, frm_full="e" * 40)
    ns: dict = {}
    exec(compile(text.split("\nASK = True")[0], "upd", "exec"), ns)     # 상수 정의부만 실행
    assert ns["FROM_FULL"] == "e" * 40 and len(ns["FILES"]) == 4 and ns["DELETED"][0][0] == "gone.yaml"


@pytest.mark.skipif(shutil.which("git") is None, reason="git 없음")
def test_collect_reads_to_from_to_tree_not_rev_list_tail(tmp_path, monkeypatch):
    """머지 + 커밋 시각 뒤섞임(GIT_COMMITTER_DATE): TO 내용은 TO 트리에서, KNOWN 은 부모→자식(--topo-order) 순서로.

    rev-list 기본 순서는 날짜순이라 사이 커밋이 뒤섞이고, 옛 git 은 TO 가 마지막이 아닐 수도 있다. 이 저장소에서 git 이 TO 를 어디에
    두든 결과가 같아야 하므로 git 래퍼가 rev-list 를 거꾸로 돌려주는 경우(TO 가 맨 앞)도 같이 검사한다.
    """
    repo = tmp_path / "g"
    repo.mkdir()

    def g(*args, date=None):
        env = dict(os.environ)
        if date:
            env["GIT_COMMITTER_DATE"] = env["GIT_AUTHOR_DATE"] = date
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.autocrlf=false", *args],
                              cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8", env=env).stdout.strip()

    def commit(msg, date, **files):
        for rel, data in files.items():
            (repo / rel).write_bytes(data)
        g("add", "-A")
        g("commit", "-q", "-m", msg, date=date)
        return g("rev-parse", "--short", "HEAD")

    g("init", "-q", "-b", "main")
    c0 = commit("v0", "2026-01-01T00:00:00", **{"a.yaml": b"a: v0\n"})
    c1 = commit("v1", "2026-01-02T00:00:00", **{"a.yaml": b"a: v1\n"})
    commit("v2", "2026-01-03T00:00:00", **{"a.yaml": b"a: v2\n"})
    commit("v3-clock-behind", "2025-12-01T00:00:00", **{"a.yaml": b"a: v3\n"})       # 시계가 뒤로 간 커밋
    g("checkout", "-q", "-b", "side", c1)
    commit("side-clock-ahead", "2026-02-01T00:00:00", **{"b.yaml": b"b: side\n"})    # 가지 커밋이 머지보다 늦은 시각
    g("checkout", "-q", "main")
    g("merge", "-q", "--no-edit", "side", date="2025-11-01T00:00:00")               # 머지(TO) 가 모든 부모보다 이른 시각
    to = g("rev-parse", "--short", "HEAD")
    monkeypatch.setattr(build_update, "REPO", repo)

    # 기본 순서(날짜순)는 사이 커밋이 뒤섞여 있다 — 전제 확인
    default_order = g("rev-list", "--reverse", f"{c0}..{to}").split()
    topo_order = g("rev-list", "--reverse", "--topo-order", f"{c0}..{to}").split()
    assert default_order != topo_order

    expected_known = (_sha(b"a: v0\n"), _sha(b"a: v1\n"), _sha(b"a: v2\n"))   # 부모→자식 (--topo-order); v3 == TO 는 뺀다
    real_git = build_update.git

    def check():
        files, deleted = build_update.collect(c0, to)
        by_path = {p: (s, k, b64, st) for p, s, k, b64, st in files}
        s, k, b64, st = by_path["a.yaml"]
        assert base64.b64decode(b64) == b"a: v3\n" and s == _sha(b"a: v3\n") and st == "M"   # TO(머지) 트리의 내용
        assert k == expected_known
        s, k, b64, st = by_path["b.yaml"]
        assert base64.b64decode(b64) == b"b: side\n" and st == "A" and k == ()                 # 가지에서만 — 사이 판 없음
        assert deleted == []

    check()

    # git 이 rev-list 를 거꾸로(TO 가 맨 앞, 마지막은 사이 커밋) 돌려주더라도 TO 내용은 TO 트리에서 읽어 같아야 한다
    def reversed_rev_list(*args, binary=False):
        out = real_git(*args, binary=binary)
        if args[0] == "rev-list" and "--reverse" in args:
            return "\n".join(reversed(out.splitlines()))
        return out

    monkeypatch.setattr(build_update, "git", reversed_rev_list)
    files, _ = build_update.collect(c0, to)
    s, k, b64, st = {p: (s, k, b64, st) for p, s, k, b64, st in files}["a.yaml"]
    assert base64.b64decode(b64) == b"a: v3\n" and s == _sha(b"a: v3\n")
    assert set(k) == set(expected_known)        # 집합은 같다 (순서만 뒤집힘)


# ── selftest.bat: installed_commit.txt 의 BOM 이 결과 파일 이름에 들어가지 않는지 (cmd 가 있는 Windows 전용) ───────────

@pytest.mark.skipif(sys.platform != "win32", reason="cmd.exe 전용")
@pytest.mark.parametrize("marker, expect", [
    ("﻿" + TO_FULL + "\n63\n", TO_FULL[:7]),      # 메모장이 붙인 BOM
    (TO_FULL + "\n63\n", TO_FULL[:7]),
    ("  " + TO_FULL[:7].upper() + "  \n63\n", TO_FULL[:7].upper()),   # 앞뒤 공백·짧은 해시
    (None, "unknown"),                                 # 표식 없음
])
def test_selftest_bat_reads_commit_without_bom(tmp_path, marker, expect):
    """selftest.bat 의 '설치 판 읽기' 줄을 그대로 떼어 cmd /c 로 돌린다 — BOM 이 있어도 결과 파일 이름은 selftest_<7자>.txt."""
    bat = (Path(__file__).resolve().parents[1] / "scripts" / "selftest.bat").read_bytes()
    assert b"\r\n" in bat and b"\n" not in bat.replace(b"\r\n", b"") and all(c < 128 for c in bat), ".bat 은 CRLF·ASCII"
    lines = [ln for ln in bat.decode("ascii").split("\r\n") if ln.startswith("set COMMIT=") or ln.startswith("for /f ")]
    assert len(lines) == 2 and "utf-8-sig" in lines[1]
    assert "set /p COMMIT=" not in bat.decode("ascii")       # BOM 을 그대로 읽던 옛 방식이 남아 있지 않다
    (tmp_path / "offline").mkdir()
    if marker is not None:
        (tmp_path / "offline" / "installed_commit.txt").write_text(marker, encoding="utf-8")
    # .venv\Scripts\python 자리에 이 파이썬을 부르는 .bat 심 (cmd 는 확장자 없는 이름을 PATHEXT 로 찾는다)
    (tmp_path / ".venv" / "Scripts").mkdir(parents=True)
    (tmp_path / ".venv" / "Scripts" / "python.bat").write_bytes(f'@"{sys.executable}" %*\r\n'.encode("ascii"))
    probe = tmp_path / "probe.bat"
    probe.write_bytes("\r\n".join(["@echo off", "setlocal", 'cd /d "%~dp0"', *lines,
                                  "echo OUT=selftest_%COMMIT%.txt", "endlocal", ""]).encode("ascii"))
    r = subprocess.run(["cmd", "/c", str(probe)], capture_output=True, cwd=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.replace(b"\r\n", b"\n").strip().splitlines()[-1] == f"OUT=selftest_{expect}.txt".encode("ascii")
    assert b"\xef\xbb\xbf" not in r.stdout
