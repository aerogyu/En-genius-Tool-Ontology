"""SHACL 검증 — Fuseki 배포본 jar 에 들어 있는 Jena SHACL 로 실행한다 (추가 반입물 없음).

    java -cp <FUSEKI_HOME>/fuseki-server.jar shacl.shacl validate --shapes S --data D

Jena 는 Windows 절대경로의 '\\' 를 IRI 로 받지 못하므로 임시 폴더에 복사해 상대경로로 넘긴다.
검증 범위 규칙 (docs/05): survey ∪ derived 합집합에 대해 돌린다 — derived 만 따로 돌리면 Feed 가
가리키는 IOSpec·ToolUsage 의 rdf:type 이 없어 sh:class 위반이 난다. schema 그래프(OWL)는 넣지
않는다 — rdfs:subClassOf 를 따라 믹스인 모양까지 대상이 되어 결과가 중복된다.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ShaclResult:
    conforms: bool
    results: list[tuple[str, str, str]] = field(default_factory=list)  # (focus, path, message)
    raw: str = ""


def find_tools(fuseki_home: str | Path | None = None, java: str | None = None) -> tuple[str, Path] | None:
    """(java 실행파일, fuseki-server.jar). FUSEKI_HOME·JAVA_HOME 환경변수 → PATH 의 java 순."""
    home = Path(fuseki_home or os.environ.get("FUSEKI_HOME", ""))
    jar = home / "fuseki-server.jar" if str(home) else None
    if not jar or not jar.is_file():
        return None
    if not java:
        jh = os.environ.get("JAVA_HOME")
        cand = Path(jh) / "bin" / ("java.exe" if os.name == "nt" else "java") if jh else None
        java = str(cand) if cand and cand.is_file() else shutil.which("java")
    return (java, jar) if java else None


def validate(shapes: Path, data_ttl: str, java: str, jar: Path, timeout: float = 120) -> ShaclResult:
    from rdflib import Graph, Namespace

    sh = Namespace("http://www.w3.org/ns/shacl#")
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        shutil.copyfile(shapes, t / "shapes.ttl")
        (t / "data.ttl").write_text(data_ttl, encoding="utf-8")
        proc = subprocess.run(
            [java, "-cp", str(jar), "shacl.shacl", "validate", "--shapes", "shapes.ttl", "--data", "data.ttl"],
            cwd=tmp, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
    out = proc.stdout
    if proc.returncode != 0 or "conforms" not in out:
        raise RuntimeError(f"Jena SHACL 실행 실패 (rc={proc.returncode}): {proc.stderr[-800:] or out[-800:]}")
    report = Graph().parse(data=out, format="turtle")
    # Graph.value(None, p) 는 주어·목적어가 모두 비면 None 을 돌려준다 — 직접 순회
    flags = list(report.objects(None, sh.conforms))
    if len(flags) != 1:
        raise RuntimeError(f"SHACL 보고서에 sh:conforms 가 {len(flags)}개: {out[:500]}")
    conforms = bool(flags[0].toPython())
    results = []
    for r in report.subjects(sh.focusNode, None):
        results.append((str(report.value(r, sh.focusNode)), str(report.value(r, sh.resultPath) or ""),
                        str(report.value(r, sh.resultMessage) or "")))
    return ShaclResult(conforms, sorted(results), out)
