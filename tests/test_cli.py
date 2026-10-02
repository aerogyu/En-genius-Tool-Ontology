"""CLI 동작 중 Fuseki 없이 검사할 수 있는 것 — push 의 derived 그래프 비우기 (docs/09 #25a, docs/11 7장), 설정 오류 한 줄 보고."""

from __future__ import annotations

import shutil

import pytest

from engenius_onto import backends, cli
from engenius_onto.config import fuseki_config
from engenius_onto.survey_load import DATA_SETS


def _fake_fuseki(monkeypatch, calls: list) -> None:
    monkeypatch.setattr(backends, "fuseki_alive", lambda cfg: True)
    monkeypatch.setattr(backends, "push_graph", lambda cfg, iri, data: calls.append(("PUT", iri)) or 0)
    monkeypatch.setattr(backends, "delete_graph", lambda cfg, iri: calls.append(("DELETE", iri)) or True)


def test_push_without_derived_clears_derived_graph(tmp_path, monkeypatch, capsys):
    """실행 폴더에 derived.ttl 이 없으면 survey 를 올리기 전에 derived 그래프를 지운다 — 옛 파생 결과가 새 survey 와 섞이지 않게."""
    calls: list = []
    _fake_fuseki(monkeypatch, calls)
    run = tmp_path / "20260924T120000"
    run.mkdir()
    (run / "survey.ttl").write_text("", encoding="utf-8")
    assert cli.main(["push", "--run", str(run)]) == 0
    g = fuseki_config().graphs
    assert calls == [("DELETE", g["derived"]), ("PUT", g["schema"]), ("PUT", g["survey"])]
    assert "[OK] derived 비움" in capsys.readouterr().out


def test_push_with_derived_puts_it(tmp_path, monkeypatch):
    calls: list = []
    _fake_fuseki(monkeypatch, calls)
    run = tmp_path / "20260924T120000"
    run.mkdir()
    (run / "survey.ttl").write_text("", encoding="utf-8")
    (run / "derived.ttl").write_text("", encoding="utf-8")
    assert cli.main(["push", "--run", str(run)]) == 0
    g = fuseki_config().graphs
    assert calls == [("PUT", g["schema"]), ("PUT", g["survey"]), ("PUT", g["derived"])]


def test_load_reports_config_error_in_one_line(tmp_path, capsys):
    """오버레이의 값 없는 키(`loader:`) 같은 설정 오류는 traceback 없이 '[NG] 설정 오류: …' 한 줄, rc 2 (load.bat 안내문의 '2 stopped';
    load·apply-review·graph_view 공통 — diag 는 설정을 읽지 않는다)."""
    over = tmp_path / "over"
    over.mkdir()
    (over / "rules.yaml").write_text("manual_transfer_values:\nloader:\n", encoding="utf-8")
    reg = tmp_path / "registry"
    shutil.copytree(DATA_SETS["synthetic"][1], reg)
    rc = cli.main(["load", "--registry", str(reg), "--out", str(tmp_path / "out"), "--overlay", str(over), "--no-shacl"])
    assert rc == 2
    err = capsys.readouterr().err
    where = str((over / "rules.yaml").resolve())                                   # 실제 오버레이 파일 경로 (저장소 밖이면 절대 경로)
    assert err.startswith(f"[NG] 설정 오류: {where} manual_transfer_values: 값이 비어 있다") and "Traceback" not in err
    assert not (tmp_path / "out").exists()
    # YAML 문법 오류도 한 줄 — 자리(행·열)만, 줄 내용·값은 넣지 않는다 (오버레이에는 실 툴명이 든다)
    (over / "rules.yaml").write_text("manual_transfer_values: [메일\nloader:\n  x: 1\n", encoding="utf-8")
    rc = cli.main(["load", "--registry", str(reg), "--out", str(tmp_path / "out"), "--overlay", str(over), "--no-shacl"])
    err = capsys.readouterr().err
    assert rc == 2 and "Traceback" not in err and "메일" not in err
    assert err.startswith(f"[NG] 설정 오류: {where} ") and "행 " in err and "열: YAML 문법 오류 — 들여쓰기·괄호·콜론 뒤 공백을 확인" in err
    # --overlay 와 --no-overlay 를 같이 주면 argparse 가 거부한다 (rc 2)
    with pytest.raises(SystemExit) as e:
        cli.main(["load", "--registry", str(reg), "--out", str(tmp_path / "out"), "--overlay", str(over), "--no-overlay"])
    assert e.value.code == 2 and "not allowed with" in capsys.readouterr().err
    # apply-review 가 직접 읽는 tool_aliases.yaml 의 형식 오류(aliases 가 목록)·문법 오류도 '[NG] 설정 오류' 한 줄
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / "tool_aliases.yaml").write_text("aliases: [Excel]\n", encoding="utf-8")
    (tmp_path / "r.csv").write_text("툴A_키,툴A_표기,툴B_키,툴B_표기,유사도,사유,판정(통합/별개),대표 이름(통합 시)\na,a,b,b,0.9,포함,통합,\n",
                                    encoding="utf-8-sig")
    assert cli.main(["apply-review", str(tmp_path / "r.csv"), "--config-dir", str(cfg)]) == 2
    err = capsys.readouterr().err
    assert err.startswith(f"[NG] 설정 오류: {(cfg / 'tool_aliases.yaml').resolve()} aliases: 형식은 매핑(이름: [목록])") and "Traceback" not in err
    (cfg / "tool_aliases.yaml").write_text("aliases:\n  Excel: [엑셀\n", encoding="utf-8")
    assert cli.main(["apply-review", str(tmp_path / "r.csv"), "--config-dir", str(cfg)]) == 2
    err = capsys.readouterr().err
    assert err.startswith("[NG] 설정 오류: ") and "YAML 문법 오류" in err and "엑셀" not in err
    assert (cfg / "tool_aliases.yaml").read_text(encoding="utf-8") == "aliases:\n  Excel: [엑셀\n"      # 오류면 파일은 그대로
    # apply-review 는 ValueError 전반을 한 줄로 (판정 값 오류)
    (tmp_path / "r.csv").write_text("툴A_키,툴A_표기,툴B_키,툴B_표기,유사도,사유,판정(통합/별개),대표 이름(통합 시)\na,a,b,b,0.9,포함,보류,\n",
                                    encoding="utf-8-sig")
    assert cli.main(["apply-review", str(tmp_path / "r.csv"), "--config-dir", str(tmp_path / "cfg2")]) == 1
    assert capsys.readouterr().err.startswith("[NG] 판정 값은")


def test_delete_graph_treats_404_as_empty(monkeypatch):
    """Graph Store Protocol DELETE — 그래프가 없어 404 가 와도 정상(False), 다른 오류는 올린다."""
    import urllib.error
    import urllib.request

    def raise_http(code):
        def _open(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, code, "x", {}, None)
        return _open

    monkeypatch.setattr(urllib.request, "urlopen", raise_http(404))
    assert backends.delete_graph(fuseki_config(), "http://en-genius.local/graph/none") is False
    monkeypatch.setattr(urllib.request, "urlopen", raise_http(500))
    try:
        backends.delete_graph(fuseki_config(), "http://en-genius.local/graph/none")
    except urllib.error.HTTPError as e:
        assert e.code == 500
    else:
        raise AssertionError("500 은 올라와야 한다")
