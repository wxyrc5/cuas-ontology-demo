#!/usr/bin/env python3
"""Run reproducible OWL 2 DL consistency and SHACL quality checks.

The validator deliberately separates four claims:
1. RDF/Turtle syntax can be parsed;
2. the TBox plus valid ABox is satisfiable in HermiT;
3. an intentionally disjoint individual is rejected by HermiT;
4. valid data conforms to SHACL while two controlled bad values are detected.

This prevents an RDF parse or an RDFS closure from being reported as an OWL
consistency proof.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from owlready2 import (
    OwlReadyInconsistentOntologyError,
    World,
    sync_reasoner,
)
from pyshacl import validate
from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef, XSD


CUAS = Namespace("http://cuas-ontology.org/cuas#")
SH = Namespace("http://www.w3.org/ns/shacl#")

CORE_CLASSES = [
    CUAS.Mission,
    CUAS.Scenario,
    CUAS.TechnicalCapability,
    CUAS.Equipment,
    CUAS.EffectMetric,
    CUAS.Threat,
    CUAS.Asset,
    CUAS.Operator,
]

CORE_LINKS = [
    CUAS.governs,
    CUAS.allocates,
    CUAS.measuredBy,
    CUAS.implements,
    CUAS.covers,
    CUAS.produces,
    CUAS.protects,
    CUAS.confronts,
    CUAS.validates,
    CUAS.operates,
]


@dataclass
class Check:
    name: str
    passed: bool
    evidence: str
    duration_seconds: float


def parse_graph(path: Path) -> Graph:
    graph = Graph()
    graph.parse(path, format="turtle")
    return graph


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clone_graph(graph: Graph) -> Graph:
    clone = Graph()
    for triple in graph:
        clone.add(triple)
    return clone


def run_hermit(graph: Graph, *, expect_consistent: bool) -> tuple[bool, float, str]:
    """Serialize through RDF/XML because Owlready2 does not read Turtle."""
    start = time.perf_counter()
    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(suffix=".rdf", delete=False) as handle:
            temp_path = Path(handle.name)
        graph.serialize(destination=temp_path, format="xml")

        world = World()
        with temp_path.open("rb") as handle:
            world.get_ontology("http://cuas-ontology.org/cuas").load(fileobj=handle)

        try:
            sync_reasoner(
                world,
                infer_property_values=True,
                debug=0,
                ignore_unsupported_datatypes=False,
            )
            consistent = True
        except OwlReadyInconsistentOntologyError:
            consistent = False

        passed = consistent is expect_consistent
        evidence = (
            f"HermiT consistent={consistent}; expected={expect_consistent}; "
            f"input_triples={len(graph)}"
        )
        return passed, time.perf_counter() - start, evidence
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def shacl_results(report_graph: Graph) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for result in set(report_graph.subjects(RDF.type, SH.ValidationResult)):
        focus = next(report_graph.objects(result, SH.focusNode), None)
        path = next(report_graph.objects(result, SH.resultPath), None)
        component = next(report_graph.objects(result, SH.sourceConstraintComponent), None)
        message = next(report_graph.objects(result, SH.resultMessage), None)
        results.append(
            {
                "focus_node": str(focus) if focus is not None else "",
                "path": str(path) if path is not None else "",
                "constraint": str(component) if component is not None else "",
                "message": str(message) if message is not None else "",
            }
        )
    return sorted(results, key=lambda item: (item["focus_node"], item["path"]))


def java_version() -> str:
    completed = subprocess.run(
        ["java", "-version"],
        capture_output=True,
        text=True,
        check=False,
    )
    text = (completed.stderr or completed.stdout).splitlines()
    return text[0].strip() if text else "unavailable"


def write_markdown(report: dict[str, Any], path: Path) -> None:
    status = "通过" if report["all_passed"] else "未通过"
    lines = [
        "# C-UAS 本体一致性验证报告",
        "",
        f"- 总结论：**{status}**",
        f"- 执行时间：{report['executed_at']}",
        f"- Python：{report['environment']['python']}",
        f"- Java：{report['environment']['java']}",
        f"- Owlready2 / HermiT：{report['environment']['owlready2']} / bundled",
        "",
        "## 四层验证结果",
        "",
        "| 检查 | 结果 | 实际证据 | 用时（秒） |",
        "|---|---:|---|---:|",
    ]
    for check in report["checks"]:
        mark = "通过" if check["passed"] else "失败"
        evidence = check["evidence"].replace("|", "\\|")
        lines.append(
            f"| {check['name']} | {mark} | {evidence} | {check['duration_seconds']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## SHACL 负向对照（期望且仅期望 2 项）",
            "",
            "| Focus node | Path | 约束 |",
            "|---|---|---|",
        ]
    )
    for item in report["shacl_negative_results"]:
        lines.append(
            f"| `{item['focus_node'].split('#')[-1]}` | "
            f"`{item['path'].split('#')[-1]}` | {item['message']} |"
        )

    lines.extend(
        [
            "",
            "## 结论边界",
            "",
            "- HermiT 证明的是当前 OWL 2 DL TBox 与正向 ABox 可满足；负向对照证明核心类型互斥公理能够实际检出冲突。",
            "- SHACL 证明的是实例字段、枚举、关系方向和基数满足项目约束；它不替代描述逻辑一致性推理。",
            "- SWRL 规则保存在独立文件，不混入 Turtle TBox；规则执行正确性应作为单独规则测试评价。",
            "",
            "## 输入文件摘要",
            "",
            "| 文件 | 三元组数 | SHA-256 |",
            "|---|---:|---|",
        ]
    )
    for name, details in report["inputs"].items():
        lines.append(f"| `{name}` | {details['triples']} | `{details['sha256']}` |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    default_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=default_root)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Default: 05_Notebook与数据/验证输出",
    )
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    model_dir = project_root / "03_源码" / "本体模型"
    output_dir = args.output_dir or project_root / "05_Notebook与数据" / "验证输出"
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "cuas-ontology.ttl": model_dir / "cuas-ontology.ttl",
        "cuas-data-valid.ttl": model_dir / "cuas-data-valid.ttl",
        "cuas-data-test.ttl": model_dir / "cuas-data-test.ttl",
        "cuas-shapes.ttl": model_dir / "cuas-shapes.ttl",
    }

    checks: list[Check] = []
    graphs: dict[str, Graph] = {}
    parse_start = time.perf_counter()
    try:
        for name, path in paths.items():
            graphs[name] = parse_graph(path)
        checks.append(
            Check(
                "RDF/Turtle 语法解析",
                True,
                ", ".join(f"{name}={len(graphs[name])}" for name in paths),
                time.perf_counter() - parse_start,
            )
        )
    except Exception as exc:
        checks.append(
            Check(
                "RDF/Turtle 语法解析",
                False,
                f"{type(exc).__name__}: {exc}",
                time.perf_counter() - parse_start,
            )
        )
        raise

    ontology = graphs["cuas-ontology.ttl"]
    valid_data = graphs["cuas-data-valid.ttl"]
    negative_overrides = graphs["cuas-data-test.ttl"]
    shapes = graphs["cuas-shapes.ttl"]
    # pySHACL may enrich graphs internally while resolving shapes/inference.
    # Freeze source metadata now and validate clones so the report describes
    # the files that were actually read, not an in-memory post-validation graph.
    input_metadata = {
        name: {
            "path": str(paths[name].resolve()),
            "triples": len(graph),
            "sha256": sha256(paths[name]),
        }
        for name, graph in graphs.items()
    }

    structure_start = time.perf_counter()
    missing_classes = [str(item) for item in CORE_CLASSES if (item, RDF.type, OWL.Class) not in ontology]
    missing_links = [str(item) for item in CORE_LINKS if (item, RDF.type, OWL.ObjectProperty) not in ontology]
    unsupported_datatypes = {
        XSD.duration,
        URIRef(f"{XSD}dateTimeInterval"),
    }
    unsupported_ranges = {
        str(obj)
        for obj in ontology.objects(None, RDFS.range)
        if obj in unsupported_datatypes
    }
    structure_ok = not missing_classes and not missing_links and not unsupported_ranges
    checks.append(
        Check(
            "8 OT / 10 LT 结构审计",
            structure_ok,
            f"core_classes={8-len(missing_classes)}/8; core_links={10-len(missing_links)}/10; "
            f"unsupported_datatype_ranges={len(unsupported_ranges)}",
            time.perf_counter() - structure_start,
        )
    )

    shacl_start = time.perf_counter()
    valid_conforms, _, valid_text = validate(
        clone_graph(valid_data),
        shacl_graph=clone_graph(shapes),
        ont_graph=clone_graph(ontology),
        inference="rdfs",
        advanced=True,
    )
    checks.append(
        Check(
            "SHACL 正向实例验证",
            bool(valid_conforms),
            "Conforms=True" if valid_conforms else valid_text.strip().replace("\n", " ")[:500],
            time.perf_counter() - shacl_start,
        )
    )

    negative_data = clone_graph(valid_data)
    negative_data.remove((CUAS.Mission_G20Summit, CUAS.priority, None))
    negative_data.remove((CUAS.Eq_RadarUnit_007, CUAS.operationalStatus, None))
    for triple in negative_overrides:
        negative_data.add(triple)

    negative_start = time.perf_counter()
    negative_conforms, negative_report_graph, _ = validate(
        clone_graph(negative_data),
        shacl_graph=clone_graph(shapes),
        ont_graph=clone_graph(ontology),
        inference="rdfs",
        advanced=True,
    )
    negative_results = shacl_results(negative_report_graph)
    expected_pairs = {
        (str(CUAS.Mission_G20Summit), str(CUAS.priority)),
        (str(CUAS.Eq_RadarUnit_007), str(CUAS.operationalStatus)),
    }
    actual_pairs = {(item["focus_node"], item["path"]) for item in negative_results}
    negative_ok = (
        not negative_conforms
        and len(negative_results) == 2
        and actual_pairs == expected_pairs
    )
    checks.append(
        Check(
            "SHACL 负向对照",
            negative_ok,
            f"Conforms={negative_conforms}; violations={len(negative_results)}; "
            f"expected_paths=priority,operationalStatus",
            time.perf_counter() - negative_start,
        )
    )

    combined = ontology + valid_data
    hermit_ok, hermit_seconds, hermit_evidence = run_hermit(
        combined,
        expect_consistent=True,
    )
    checks.append(Check("HermiT 正向一致性", hermit_ok, hermit_evidence, hermit_seconds))

    contradiction = clone_graph(combined)
    contradiction_node = CUAS.HermiT_NegativeControl
    contradiction.add((contradiction_node, RDF.type, CUAS.Mission))
    contradiction.add((contradiction_node, RDF.type, CUAS.Equipment))
    hermit_negative_ok, hermit_negative_seconds, hermit_negative_evidence = run_hermit(
        contradiction,
        expect_consistent=False,
    )
    checks.append(
        Check(
            "HermiT 类型互斥负向对照",
            hermit_negative_ok,
            hermit_negative_evidence,
            hermit_negative_seconds,
        )
    )

    report: dict[str, Any] = {
        "schema_version": "1.0",
        "executed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "all_passed": all(check.passed for check in checks),
        "checks": [asdict(check) for check in checks],
        "shacl_negative_results": negative_results,
        "environment": {
            "python": platform.python_version(),
            "java": java_version(),
            "rdflib": version("rdflib"),
            "pyshacl": version("pyshacl"),
            "owlready2": version("owlready2"),
        },
        "inputs": input_metadata,
    }

    json_path = output_dir / "ontology_consistency_report.json"
    markdown_path = output_dir / "ontology_consistency_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, markdown_path)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"JSON_REPORT={json_path.resolve()}")
    print(f"MARKDOWN_REPORT={markdown_path.resolve()}")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
