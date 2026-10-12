"""3D 뷰어(scripts/graph_view3d.py) 스모크 — 합성 적재 뒤 build() 가 돌고, 건수가 load_log.json 과 맞고, HTML 에 외부 참조가 없다 (docs/11 4장 (8)).
인명 토큰·정렬 단조성·part_code 검사는 다른 테스트와 중복이라 두지 않는다.
설정 오버레이·비활성 툴 거르기 검사는 실행 폴더 사본 위에서 (survey.ttl·load_log.json 만 고쳐 다시 build).
JS 동작(팬 유지·순위표·안내선)은 브라우저 확인 기록 — 파이썬 테스트는 HTML 에 그 경로가 들어 있는지만 본다."""
from __future__ import annotations

import datetime as dt
import json
import shutil
import sys
from pathlib import Path

import pytest

from engenius_onto.config import REPO_ROOT
from engenius_onto.registry import copy_registry
from engenius_onto.survey_load import DATA_SETS, run_load

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import graph_view3d  # noqa: E402

NOW = dt.datetime(2026, 9, 24, 12, 0, 0)


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("view")
    reg = tmp / "registry"
    copy_registry(DATA_SETS["synthetic"][1], reg)
    return run_load(registry_dir=reg, out_root=tmp / "out", now=NOW, shacl=False).out_dir


@pytest.fixture(scope="module")
def built(run_dir):
    return graph_view3d.build(run_dir)


def test_counts_match_load_log(built, run_dir):
    data, _ = built
    log = json.loads((run_dir / "load_log.json").read_text(encoding="utf-8"))["counts"]
    c = data["counts"]
    assert c["fields"] == log["fields"]
    assert c["usages"] == log["usages"]
    assert c["tools"] == log["tools"]
    assert c["inactive_tools"] == 0                                    # 첫 적재 — 통합됨·폐기 툴 없음
    assert c["ios"] == log["io_specs"] - log["orphan_io_specs"]       # 고아 입출력(주인 툴사용 없음)은 지도에 없다
    assert c["noio"] == sum(1 for n in data["nodes"] if n["type"] == "u" and not n["ios"])
    assert len(data["nodes"]) == c["usages"] + c["tools"]
    assert data["view"]["label_min_parts"] == graph_view3d.VIEW["label_min_parts"]
    assert data["overlay"] is False                                    # 합성 적재는 오버레이 없이 (load_log config_overlay.dir = None)


def test_html_has_no_external_reference(built):
    _, out = built
    html = out.read_text(encoding="utf-8")
    assert out.name == "graph3d.html" and graph_view3d.VIEW_VERSION in html
    for token in ("<script src", "<link href", "fetch("):
        assert token not in html, token
    assert "설정 오버레이 적용" not in html.split("<script>")[0]       # 오버레이 없으면 제목에 표시 안 함


def _copy_run(run_dir: Path, dst: Path) -> Path:
    dst.mkdir()
    for name in ("survey.ttl", "load_log.json"):
        shutil.copy(run_dir / name, dst / name)
    return dst


def test_overlay_rules_change_manual_kind_and_mark_html(run_dir, tmp_path):
    """적재가 쓴 오버레이(load_log config_overlay.dir)의 rules.yaml 로 수기 판정 — 오버레이가 '메일·수기 전달' 을 수기 목록에서 빼면
    수기 선이 0 이 되고, 제목·건수 상자에 '설정 오버레이 적용' 이 붙는다."""
    base, _ = graph_view3d.build(run_dir)
    assert base["counts"]["manual"] > 0
    run = _copy_run(run_dir, tmp_path / "run")
    overlay = tmp_path / "overlay"
    overlay.mkdir()
    (overlay / "rules.yaml").write_text("manual_transfer_values: []\n", encoding="utf-8")
    log = json.loads((run / "load_log.json").read_text(encoding="utf-8"))
    log["config_overlay"] = {"used": True, "dir": str(overlay), "files": ["rules.yaml"]}   # 절대 경로도 받는다
    (run / "load_log.json").write_text(json.dumps(log, ensure_ascii=False), encoding="utf-8")
    data, out = graph_view3d.build(run)
    assert data["overlay"] is True
    assert data["counts"]["manual"] == 0
    assert data["counts"]["pairs"] == base["counts"]["pairs"]          # 선 수는 같고 종류만 바뀐다
    html = out.read_text(encoding="utf-8")
    assert "설정 오버레이 적용" in html.split("<script>")[0]          # 제목에
    assert '"overlay": true' in html                                   # 건수 상자(JS)에


def _write_log(run: Path, config_overlay) -> None:
    """실행 폴더 사본의 load_log.json 에 config_overlay 를 넣거나(값) 지운다(None)."""
    log = json.loads((run / "load_log.json").read_text(encoding="utf-8"))
    if config_overlay is None:
        log.pop("config_overlay", None)
    else:
        log["config_overlay"] = config_overlay
    (run / "load_log.json").write_text(json.dumps(log, ensure_ascii=False), encoding="utf-8")


def test_overlay_dir_missing_is_reported_not_substituted(run_dir, tmp_path):
    """load_log 가 가리키는 오버레이 폴더가 없으면(사내 실행 폴더를 밖에서 열 때) 기본 data/real/config 로 바꿔 타지 않고
    저장소 rules.yaml 만 쓰며, 제목·건수 상자에 '오버레이 폴더 못 찾음' 을 표시한다."""
    run = _copy_run(run_dir, tmp_path / "run")
    _write_log(run, {"used": True, "dir": "data/real/config_없음", "files": ["rules.yaml"]})
    assert graph_view3d.overlay_dir_of(run) == (None, True)
    data, out = graph_view3d.build(run)
    assert data["overlay"] is False and data["overlay_missing"] is True
    html = out.read_text(encoding="utf-8")
    assert "오버레이 폴더 못 찾음" in html.split("<script>")[0]       # 제목에
    assert '"overlay_missing": true' in html                           # 건수 상자(JS)에
    assert "설정 오버레이 적용" not in html.split("<script>")[0]


def test_overlay_used_false_ignores_dir(run_dir, tmp_path):
    """적재가 오버레이 없이 돌았다고(used=false) 적혀 있으면 dir 가 실제 폴더를 가리켜도, 기본 data/real/config 가 있어도 쓰지 않는다."""
    run = _copy_run(run_dir, tmp_path / "run")
    overlay = tmp_path / "overlay"
    overlay.mkdir()
    (overlay / "rules.yaml").write_text("manual_transfer_values: []\n", encoding="utf-8")
    _write_log(run, {"used": False, "dir": str(overlay), "files": []})
    assert graph_view3d.overlay_dir_of(run) == (None, False)
    data, out = graph_view3d.build(run)
    assert data["overlay"] is False and data["overlay_missing"] is False
    assert data["counts"]["manual"] > 0                                 # 오버레이의 빈 수기 목록이 반영되지 않았다
    head = out.read_text(encoding="utf-8").split("<script>")[0]
    assert "오버레이" not in head


def test_old_log_without_config_overlay_key_falls_back_to_default(run_dir, tmp_path):
    """config_overlay 키가 없는 옛 실행(M3.1 이전 load_log)만 기본 data/real/config (있을 때) 로 떨어진다 — 개발 PC 에는 없으므로 None."""
    run = _copy_run(run_dir, tmp_path / "run")
    _write_log(run, None)
    assert graph_view3d.overlay_dir_of(run) == (graph_view3d.default_overlay_dir(), False)
    data, _ = graph_view3d.build(run)
    assert data["overlay"] is (graph_view3d.default_overlay_dir() is not None)
    assert data["overlay_missing"] is False


def test_overlay_outside_repo_is_recorded_absolute_and_found(tmp_path):
    """저장소 밖 --overlay 폴더는 load_log config_overlay.dir 에 절대 경로 그대로 + outside_repo: true 로 남고(이름만 남던 문제),
    overlay_dir_of 가 그 폴더를 다시 찾는다. 폴더가 사라지면 (None, True)."""
    reg = tmp_path / "registry"
    copy_registry(DATA_SETS["synthetic"][1], reg)
    overlay = tmp_path / "overlay"
    overlay.mkdir()
    (overlay / "rules.yaml").write_text("manual_transfer_values: []\n", encoding="utf-8")
    out = run_load(registry_dir=reg, out_root=tmp_path / "out", now=NOW, shacl=False, overlay_dir=overlay)
    assert out.log["config_overlay"] == {"used": True, "dir": str(overlay.resolve()), "files": ["rules.yaml"], "outside_repo": True}
    assert Path(out.log["config_overlay"]["dir"]).is_absolute()
    assert graph_view3d.overlay_dir_of(out.out_dir) == (overlay.resolve(), False)
    data, _ = graph_view3d.build(out.out_dir)
    assert data["overlay"] is True and data["overlay_missing"] is False and data["counts"]["manual"] == 0
    shutil.rmtree(overlay)
    assert graph_view3d.overlay_dir_of(out.out_dir) == (None, True)


def test_inactive_tools_are_not_drawn(run_dir, tmp_path):
    """레지스트리가 survey 그래프에 남기는 '통합됨'·'폐기' 툴(D7·C2)은 사용 선이 없으므로 점으로 그리지 않는다 — 건수에만 '제외' 로 센다."""
    run = _copy_run(run_dir, tmp_path / "run")
    ttl = run / "survey.ttl"
    text = ttl.read_text(encoding="utf-8")
    active_line = next(line for line in text.splitlines() if 'eg:status "활성"' in line)
    assert active_line                                                 # 활성 상태가 적히는 형태를 그대로 쓴다
    extra = """
egid:TOOL-999001 a eg:Tool ; rdfs:label "옛 뷰어 툴"@ko ; skos:prefLabel "옛 뷰어 툴"@ko ; eg:status "폐기" .
egid:TOOL-999002 a eg:Tool ; rdfs:label "합쳐진 툴"@ko ; skos:prefLabel "합쳐진 툴"@ko ; eg:status "통합됨" ; eg:merged_into egid:TOOL-000011 .
"""
    ttl.write_text(text + extra, encoding="utf-8")
    base, _ = graph_view3d.build(run_dir)
    data, out = graph_view3d.build(run)
    names = {n["name"] for n in data["nodes"] if n["type"] == "t"}
    assert "옛 뷰어 툴" not in names and "합쳐진 툴" not in names
    assert data["counts"]["tools"] == base["counts"]["tools"]
    assert data["counts"]["inactive_tools"] == 2
    assert all(n["uses"] > 0 for n in data["nodes"] if n["type"] == "t")   # 유령 점 없음 — 모든 툴 점에 사용 선이 있다
    assert len(data["edges"]) == len(base["edges"])
    assert "옛 뷰어 툴" not in out.read_text(encoding="utf-8")


def test_html_keeps_user_pan_and_bounds_leader(built):
    """브라우저 확인(2026-10-02)과 짝 — 드래그 이동 뒤 refit 이 panX/panY 를 되돌리지 않는 경로와 안내선 2 글자높이 상한이 HTML 에 들어 있다."""
    _, out = built
    html = out.read_text(encoding="utf-8")
    assert "S.userPan = true" in html and "if (!S.userPan) { S.panX = 0; S.panY = 0; }" in html
    assert "S.userPan = false" in html                                 # 시점 초기화로 해제
    assert "> 2 * fs) continue" in html                                # 안내선 길이 상한
    assert "stats.forced++" in html                                    # 겹쳐도 그린다 (건너뛰지 않음)
