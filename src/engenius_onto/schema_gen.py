"""스키마 생성물 만들기·점검 — python -m engenius_onto schema [--check].

LinkML 스키마(schema/engenius_tool.yaml)가 마스터다. 여기서 만드는 것:
  schema/generated/engenius_tool.owl.ttl    OWL (Protégé 검토용, Fuseki schema 그래프)
  schema/generated/engenius_tool.shacl.ttl  SHACL (인스턴스 검증)
  schema/generated/form_mapping.md          양식 열 ↔ 슬롯 매핑표 (스키마 주석에서 자동)
  schema/generated/docs/                    사람용 문서 (gen-doc)
  src/engenius_onto/schema_model.py         Pydantic 클래스 (적재기 검증용)

gen-owl·gen-shacl 은 실행할 때마다 Turtle 줄 순서가 바뀐다 (docs/04 부록 C) — 빈 노드 이름을
정규화(rdflib.compare.to_canonical_graph)한 뒤 직렬화해 git diff 가 의미 있는 변경만 보이게 한다.
"""

from __future__ import annotations

import re
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path

import yaml

from engenius_onto.config import REPO_ROOT

SCHEMA = REPO_ROOT / "schema" / "engenius_tool.yaml"
DATASET_SCHEMA = REPO_ROOT / "schema" / "engenius_tool_dataset.yaml"
LINT_CONFIG = REPO_ROOT / "schema" / ".linkmllint.yaml"
GEN_DIR = REPO_ROOT / "schema" / "generated"
DOCS_DIR = GEN_DIR / "docs"
MODEL_PY = REPO_ROOT / "src" / "engenius_onto" / "schema_model.py"
FORM_XLSX = REPO_ROOT / "reference" / "SW조사양식_EnGenius_v1.0.xlsx"
FORM_SPEC_MD = REPO_ROOT / "reference" / "양식_명세.md"

FORM_SHEETS = ("SW기본정보", "SW입출력")
RDFS_LITERAL = "http://www.w3.org/2000/01/rdf-schema#Literal"
GENERATED_BANNER = "자동 생성 — 직접 고치지 말 것. 원본: schema/engenius_tool.yaml, 명령: python -m engenius_onto schema"


def _norm_header(h: str) -> str:
    """헤더 비교용 정규화 — '*' 와 공백 무시 (docs/02 5장)."""
    return re.sub(r"[\s*]", "", h or "")


# ---------------------------------------------------------------------------
# lint
# ---------------------------------------------------------------------------
def lint() -> list[str]:
    from linkml.linter.linter import Linter

    cfg = yaml.safe_load(LINT_CONFIG.read_text(encoding="utf-8"))
    problems = []
    for p in Linter(cfg).lint(str(SCHEMA)):
        problems.append(f"{p.level}: {p.message} ({p.rule_name})")
    return problems


# ---------------------------------------------------------------------------
# OWL / SHACL / Pydantic / docs
# ---------------------------------------------------------------------------
def _canonical_turtle(ttl: str) -> str:
    from rdflib import Graph
    from rdflib.compare import to_canonical_graph

    src = Graph().parse(data=ttl, format="turtle")
    canon = Graph()
    for prefix, ns in src.namespaces():
        canon.bind(prefix, ns, override=True)
    for t in to_canonical_graph(src):
        canon.add(t)
    return canon.serialize(format="turtle")


def build_owl() -> str:
    from linkml.generators.owlgen import OwlSchemaGenerator

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        gen = OwlSchemaGenerator(
            str(SCHEMA),
            # 파이썬 API 기본값은 CLI(gen-owl) 기본값과 반대다 — CLI 와 같게 명시:
            #   문자열 슬롯 = owl:DatatypeProperty, 메타모델 클래스 섞지 않음, slot_uri(rdfs:label 등) 사용
            type_objects=False,
            metaclasses=False,
            use_native_uris=False,
            # 선택지 값을 문자열 리터럴(owl:oneOf)로 — SHACL(sh:in)·데이터 표현과 일치, IRI 인코딩 없음
            default_permissible_value_type=RDFS_LITERAL,
            skip_vacuous_min_zero_cardinality_axioms=True,
            skip_vacuous_local_range_axioms=True,
            consolidate_cardinality_axioms=True,
        )
        ttl = gen.serialize()
    return f"# {GENERATED_BANNER}\n" + _canonical_turtle(_owl_dl_tidy(ttl))


# OWL 2 에서 주석 속성으로 쓰는 예약·표준 어휘 — 데이터 속성으로 선언하거나 클래스 제약에 쓰면 DL 위반
_ANNOTATION_PROPS = (
    "http://www.w3.org/2000/01/rdf-schema#label",
    "http://www.w3.org/2004/02/skos/core#prefLabel",
    "http://www.w3.org/2004/02/skos/core#altLabel",
)


def _owl_dl_tidy(ttl: str) -> str:
    """gen-owl 출력을 OWL 2 DL 규칙에 맞게 정리한다.

    1. rdfs:label·skos:prefLabel·skos:altLabel — gen-owl 이 DatatypeProperty 로 선언하고 최소
       개수 제약을 건다. OWL 2 에서 이들은 주석 속성이므로 선언을 AnnotationProperty 로 바꾸고
       (rdfs:label 은 내장이라 선언하지 않음) 클래스 제약을 뺀다. 필수 여부는 SHACL 이 검사한다.
    2. 선택지(열거형) — 리터럴 값 목록(rdfs:Literal 옵션)인데도 gen-owl 이 owl:Class 겸
       rdfs:Datatype 으로 선언하고 슬롯을 ObjectProperty 로 둔다. 이름 있는 데이터타입의 OWL 2
       정식 표현(owl:equivalentClass [a rdfs:Datatype; owl:oneOf (...)])으로 바꾸고, 선택지 값을
       갖는 슬롯은 DatatypeProperty 로 바꾼다. 데이터의 선택지 값은 언어 태그 없는 문자열이어야
       한다 (SHACL sh:in 과 같은 표현).
    """
    from rdflib import BNode, Graph, URIRef
    from rdflib.namespace import OWL, RDF, RDFS

    g = Graph().parse(data=ttl, format="turtle")

    for p in map(URIRef, _ANNOTATION_PROPS):
        for t in (OWL.DatatypeProperty, OWL.ObjectProperty):
            g.remove((p, RDF.type, t))
        if p != RDFS.label:
            g.add((p, RDF.type, OWL.AnnotationProperty))
        for r in list(g.subjects(OWL.onProperty, p)):
            if isinstance(r, BNode):
                for s, pp in list(g.subject_predicates(r)):
                    g.remove((s, pp, r))
                g.remove((r, None, None))

    enums = {e for e in g.subjects(RDF.type, RDFS.Datatype) if (e, OWL.oneOf, None) in g}
    for e in enums:
        values = g.value(e, OWL.oneOf)
        g.remove((e, OWL.oneOf, values))
        g.remove((e, RDF.type, OWL.Class))
        dt = BNode()
        g.add((dt, RDF.type, RDFS.Datatype))
        g.add((dt, OWL.oneOf, values))
        g.add((e, OWL.equivalentClass, dt))
    enum_props = {g.value(r, OWL.onProperty) for r in g.subjects(OWL.onProperty, None)
                  if {g.value(r, OWL.allValuesFrom), g.value(r, OWL.someValuesFrom)} & enums}
    enum_props |= {p for p, e in g.subject_objects(RDFS.range) if e in enums}  # 전역 슬롯은 rdfs:range 로 온다
    for p in enum_props:
        g.remove((p, RDF.type, OWL.ObjectProperty))
        g.add((p, RDF.type, OWL.DatatypeProperty))
    return g.serialize(format="turtle")


def build_shacl() -> str:
    from linkml.generators.shaclgen import ShaclGenerator

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ttl = ShaclGenerator(str(SCHEMA)).serialize()
    return f"# {GENERATED_BANNER}\n" + _canonical_turtle(_shacl_tidy(ttl))


def _shacl_tidy(ttl: str) -> str:
    """이름 속성(rdfs:label·skos:prefLabel·skos:altLabel)의 값 타입을 rdf:langString 으로.

    설계상 모든 이름은 @ko 언어 태그를 단다 (docs/02 4장) — 태그 붙은 리터럴의 데이터타입은
    rdf:langString 이라, gen-shacl 이 넣는 xsd:string 그대로면 모든 노드가 위반이 된다.
    """
    from rdflib import Graph, Namespace, URIRef
    from rdflib.namespace import RDF, XSD

    sh = Namespace("http://www.w3.org/ns/shacl#")
    g = Graph().parse(data=ttl, format="turtle")
    for p in map(URIRef, _ANNOTATION_PROPS):
        for ps in list(g.subjects(sh.path, p)):
            if (ps, sh.datatype, XSD.string) in g:
                g.remove((ps, sh.datatype, XSD.string))
                g.add((ps, sh.datatype, RDF.langString))
    return g.serialize(format="turtle")


def build_pydantic() -> str:
    from linkml.generators.pydanticgen import PydanticGenerator

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        code = PydanticGenerator(str(DATASET_SCHEMA)).serialize()
    # 개발 PC 절대경로가 섞이지 않게 (재현성·정보 노출)
    return f"# {GENERATED_BANNER}\n" + _strip_repo_path(code)


def _strip_repo_path(text: str) -> str:
    """생성물에서 개발 PC 절대경로 제거 (그대로·파이썬 repr 이스케이프·슬래시 세 가지 표기)."""
    root = str(REPO_ROOT)
    for form in (root.replace("\\", "\\\\"), root, REPO_ROOT.as_posix()):
        text = text.replace(form, "<repo>")
    # OS 마다 구분자가 달라 --check 가 거짓 불일치를 내지 않도록 '/' 로 통일
    return re.sub(r"<repo>((?:\\\\|\\|/)[\w.\\/-]+)", lambda m: "<repo>" + re.sub(r"\\\\|\\", "/", m.group(1)), text)


def build_docs() -> dict[str, str]:
    from linkml.generators.docgen import DocGenerator

    with tempfile.TemporaryDirectory() as tmp, warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        DocGenerator(str(SCHEMA), mergeimports=False).serialize(directory=tmp)
        out = {}
        for p in sorted(Path(tmp).rglob("*")):
            if p.is_file():
                txt = p.read_text(encoding="utf-8")
                out[p.relative_to(tmp).as_posix()] = _strip_repo_path(txt)
        return out


# ---------------------------------------------------------------------------
# 양식 매핑
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MappingRow:
    sheet: str
    column: str
    header: str
    cls: str
    slot: str
    range: str
    required: bool
    multivalued: bool


def _schema_view():
    from linkml_runtime.utils.schemaview import SchemaView

    return SchemaView(str(SCHEMA))


def _ann(elem, key):
    """주석 값 — LinkML 은 경우에 따라 dict 또는 JsonObj 로 준다."""
    anns = elem.annotations
    if not anns:
        return None
    try:
        a = anns[key]
    except (KeyError, TypeError, AttributeError):
        a = getattr(anns, key, None)
    if a is None:
        return None
    return str(getattr(a, "value", a))


def form_mapping(sv=None) -> list[MappingRow]:
    sv = sv or _schema_view()
    rows = []
    for cname in sv.all_classes():
        for s in sv.class_induced_slots(cname):
            sheet = _ann(s, "form_sheet")
            if not sheet:
                continue
            rows.append(MappingRow(sheet, _ann(s, "form_column") or "", _ann(s, "form_header") or "",
                                   cname, s.name, s.range or "string", bool(s.required), bool(s.multivalued)))
    order = {sh: i for i, sh in enumerate(FORM_SHEETS)}
    return sorted(rows, key=lambda r: (order.get(r.sheet, 9), len(r.column), r.column))


def excluded_columns(sv=None) -> list[tuple[str, str, str]]:
    sv = sv or _schema_view()
    raw = _ann(sv.schema, "form_excluded_columns")
    out = []
    for item in raw.split(";"):
        sheet, header, reason = (x.strip() for x in item.split("|", 2))
        out.append((sheet, header, reason))
    return out


def internal_slots(sv=None) -> list[tuple[str, str, str, str]]:
    """양식 열에서 직접 오지 않는 슬롯 (파생·해석·provenance) — 매핑표 부록."""
    sv = sv or _schema_view()
    out = []
    for cname in sv.all_classes():
        c = sv.get_class(cname)
        if c.mixin:
            continue
        for s in sv.class_induced_slots(cname):
            if _ann(s, "form_sheet") or s.name == "id":
                continue
            desc = (s.description or "").replace("\n", " ").replace("|", "/")
            out.append((cname, s.name, s.range or "string", desc))
    return out


def form_headers_xlsx(path: Path = FORM_XLSX) -> dict[str, list[tuple[str, str]]]:
    import openpyxl
    from openpyxl.utils import get_column_letter

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = {}
    for sheet in FORM_SHEETS:
        ws = wb[sheet]
        row2 = next(ws.iter_rows(min_row=2, max_row=2, values_only=True))
        out[sheet] = [(get_column_letter(i + 1), str(h)) for i, h in enumerate(row2) if h]
    wb.close()
    return out


def form_headers_spec_md(path: Path = FORM_SPEC_MD) -> dict[str, list[tuple[str, str]]]:
    out, sheet = {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## (SW기본정보|SW입출력) \(", line)
        if m:
            sheet = m.group(1)
            out[sheet] = []
            continue
        if line.startswith("## ") or line.startswith("**"):
            sheet = None if line.startswith("## ") else sheet
        if sheet and re.match(r"^\| [A-Z]{1,2} \|", line):
            cells = [c.strip() for c in line.strip("|").split("|")]
            out[sheet].append((cells[0], cells[2]))
    return out


def check_mapping(sv=None) -> list[str]:
    """양식 헤더 전부가 슬롯 하나 또는 의도적 제외에 대응하는지 (M1 완료 기준: 누락 0)."""
    sv = sv or _schema_view()
    rows = form_mapping(sv)
    excl = excluded_columns(sv)
    problems = []
    for source, headers in (("xlsx", form_headers_xlsx()), ("양식_명세.md", form_headers_spec_md())):
        for sheet in FORM_SHEETS:
            mapped = [r for r in rows if r.sheet == sheet]
            ex = [h for sh, h, _ in excl if sh == sheet]
            got = headers.get(sheet, [])
            if not got:
                problems.append(f"[{source}] {sheet}: 헤더를 찾지 못함")
                continue
            for col, h in got:
                hits = [r for r in mapped if _norm_header(r.header) == _norm_header(h)]
                if len(hits) > 1:
                    problems.append(f"[{source}] {sheet} {col} '{h}': 슬롯 {len(hits)}개에 중복 매핑")
                elif not hits and _norm_header(h) not in {_norm_header(x) for x in ex}:
                    problems.append(f"[{source}] {sheet} {col} '{h}': 매핑 누락")
                elif hits and hits[0].column != col:
                    problems.append(f"[{source}] {sheet} '{h}': 열 표기 불일치 스키마 {hits[0].column} vs {col}")
            known = {_norm_header(h) for _, h in got}
            for r in mapped:
                if _norm_header(r.header) not in known:
                    problems.append(f"[{source}] {sheet} 슬롯 {r.cls}.{r.slot}: 헤더 '{r.header}' 가 양식에 없음")
            for h in ex:
                if _norm_header(h) not in known:
                    problems.append(f"[{source}] {sheet} 제외 열 '{h}' 가 양식에 없음")
    return problems


def form_choice_lists(path: Path = FORM_XLSX) -> dict[str, list[str]]:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = list(wb["선택지"].iter_rows(min_row=2, values_only=True))  # 읽기전용 시트는 열 순회가 없다
    wb.close()
    out = {}
    for col in zip(*rows):
        vals = [str(v) for v in col if v is not None]
        if vals:
            out[vals[0]] = vals[1:]
    return out


def check_enums_vs_form(sv=None) -> list[str]:
    """열거형 값이 원본 양식 '선택지' 시트 목록과 같은지 (순서 포함)."""
    sv = sv or _schema_view()
    lists = form_choice_lists()
    problems, used = [], set()
    for ename in sv.all_enums():
        e = sv.get_enum(ename)
        fl = _ann(e, "form_list")
        if not fl:
            continue
        used.add(fl)
        if fl not in lists:
            problems.append(f"열거형 {ename}: 선택지 목록 '{fl}' 이 양식에 없음")
        elif list(e.permissible_values) != lists[fl]:
            problems.append(f"열거형 {ename}: 값 불일치 스키마 {list(e.permissible_values)} vs 양식 {lists[fl]}")
    # 클래스 노드로 모델링한 목록 (열거형이 아님)
    class_lists = {"담당부서": "Field", "온톨로지분류": "DataCategory"}
    for fl in lists:
        if fl not in used and fl not in class_lists:
            problems.append(f"양식 선택지 목록 '{fl}' 에 대응하는 열거형·클래스가 없음")
    return problems


def render_mapping_md(sv=None) -> str:
    sv = sv or _schema_view()
    rows = form_mapping(sv)
    lines = [
        f"<!-- {GENERATED_BANNER} -->",
        "# 양식 열 ↔ 스키마 슬롯 매핑표",
        "",
        f"스키마 v{sv.schema.version} · 원본 양식 `{FORM_XLSX.name}` 기준. 열 문자는 **원본** 양식의 위치다 — "
        "사내 배포본은 위치가 다를 수 있어 적재기는 헤더 이름으로 매핑한다 (docs/02 5장).",
        "",
    ]
    for sheet in FORM_SHEETS:
        rs = [r for r in rows if r.sheet == sheet]
        lines += [f"## {sheet} ({len(rs)}열 적재)", "",
                  "| 열 | 헤더 | 클래스.슬롯 | 범위 | 필수 |", "|---|---|---|---|---|"]
        for r in rs:
            rng = r.range + ("[]" if r.multivalued else "")
            lines.append(f"| {r.column} | {r.header} | `{r.cls}.{r.slot}` | {rng} | {'예' if r.required else ''} |")
        lines.append("")
    lines += ["## 의도적으로 적재하지 않는 열", "", "| 시트 | 헤더 | 이유 |", "|---|---|---|"]
    for sheet, header, reason in excluded_columns(sv):
        lines.append(f"| {sheet} | {header} | {reason} |")
    lines += ["", "## 양식에서 직접 오지 않는 슬롯 (파생·해석·provenance)", "",
              "| 클래스 | 슬롯 | 범위 | 설명 |", "|---|---|---|---|"]
    for cname, slot, rng, desc in internal_slots(sv):
        lines.append(f"| {cname} | `{slot}` | {rng} | {desc} |")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 실행
# ---------------------------------------------------------------------------
def outputs() -> dict[Path, str]:
    out = {
        GEN_DIR / "engenius_tool.owl.ttl": build_owl(),
        GEN_DIR / "engenius_tool.shacl.ttl": build_shacl(),
        GEN_DIR / "form_mapping.md": render_mapping_md(),
        MODEL_PY: build_pydantic(),
    }
    for rel, txt in build_docs().items():
        out[DOCS_DIR / rel] = txt
    return out


def _read(p: Path) -> str | None:
    return p.read_text(encoding="utf-8") if p.exists() else None


def run(check: bool = False) -> int:
    problems = []
    lp = lint()
    problems += [f"[lint] {p}" for p in lp]
    problems += [f"[매핑] {p}" for p in check_mapping()]
    problems += [f"[선택지] {p}" for p in check_enums_vs_form()]
    for p in problems:
        print(p)
    if problems:
        print(f"점검 실패 {len(problems)}건 — 생성하지 않음")
        return 1
    print("[OK] lint 0건 · 양식 매핑 누락 0 · 선택지 일치")

    new = outputs()
    stale_docs = [p for p in DOCS_DIR.rglob("*") if p.is_file() and p not in new] if DOCS_DIR.exists() else []
    changed = [p for p, txt in new.items() if _read(p) != txt]
    rel = lambda p: p.relative_to(REPO_ROOT).as_posix()  # noqa: E731
    if check:
        for p in changed:
            print(f"[불일치] {rel(p)} — 생성물이 스키마와 다르다")
        for p in stale_docs:
            print(f"[잔존] {rel(p)} — 스키마에 없는 문서")
        if changed or stale_docs:
            print("python -m engenius_onto schema 로 다시 생성할 것")
            return 1
        print(f"[OK] 생성물 {len(new)}개가 스키마와 일치")
        return 0
    for p in changed:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(new[p], encoding="utf-8", newline="\n")
    for p in stale_docs:
        p.unlink()
    print(f"생성 {len(new)}개 (변경 {len(changed)}, 삭제 {len(stale_docs)})")
    return 0
