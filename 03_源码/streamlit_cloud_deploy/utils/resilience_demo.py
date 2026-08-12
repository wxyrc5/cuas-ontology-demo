"""Visible ontology hot-plug and failure traceability demonstrations."""
from __future__ import annotations

from time import perf_counter
from typing import Any

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD


CUAS = Namespace("http://cuas-ontology.org/cuas#")
PROV = Namespace("http://www.w3.org/ns/prov#")
DEMO = Namespace("https://cuas-ontology.org/demo#")


def _hardkill_equipment(graph: Graph) -> list[str]:
    query = """
    PREFIX cuas: <http://cuas-ontology.org/cuas#>
    SELECT DISTINCT ?equipment WHERE {
      ?equipment a cuas:Equipment ; cuas:implements ?capability .
      ?capability cuas:capabilityClass "HardKill" .
    } ORDER BY ?equipment
    """
    return [str(row.equipment).rsplit("#", 1)[-1] for row in graph.query(query)]


def evaluate_semantic_hotplug(tbox_path: str, data_path: str, shapes_path: str) -> dict[str, Any]:
    started = perf_counter()
    graph = Graph().parse(tbox_path, format="turtle")
    graph.parse(data_path, format="turtle")
    before = _hardkill_equipment(graph)
    equipment = CUAS.Eq_DE_Hotplug_002
    context = CUAS.STC_DE_Hotplug_002
    additions = {
        (equipment, RDF.type, CUAS.Equipment),
        (equipment, CUAS.equipmentSN, Literal("HEL-DEMO-002")),
        (equipment, CUAS.stanagProfile, CUAS.STANAG_4817_PMO),
        (equipment, CUAS.operationalStatus, Literal("Available")),
        (equipment, CUAS.healthScore, Literal(0.95, datatype=XSD.double)),
        (equipment, CUAS.hasSpatiotemporalContext, context),
        (equipment, CUAS.implements, CUAS.Cap_HPM_Group),
        (equipment, CUAS.covers, CUAS.Scenario_Engage_MSN001),
        (context, RDF.type, CUAS.SpatiotemporalContext),
        (context, CUAS.coordinateReferenceSystem, Literal("http://www.opengis.net/def/crs/OGC/1.3/CRS84", datatype=XSD.anyURI)),
        (context, CUAS.positionWKT, Literal("POINT (120.158 30.246)")),
        (context, CUAS.positionAccuracyM, Literal(8.0, datatype=XSD.double)),
        (context, CUAS.observedAt, Literal("2026-08-12T06:00:01Z", datatype=XSD.dateTime)),
        (context, CUAS.requiresTransformation, Literal(True, datatype=XSD.boolean)),
        (context, CUAS.targetCoordinateReferenceSystem, Literal("http://www.opengis.net/def/crs/EPSG/0/32651", datatype=XSD.anyURI)),
        (context, CUAS.transformationStatus, Literal("TRANSFORMED")),
    }
    for triple in additions:
        graph.add(triple)
    conforms, _, report_text = validate(
        data_graph=graph,
        shacl_graph=Graph().parse(shapes_path, format="turtle"),
        inference="rdfs",
        advanced=True,
    )
    after = _hardkill_equipment(graph)
    elapsed_ms = (perf_counter() - started) * 1000.0
    return {
        "before": before,
        "after": after,
        "new_equipment_visible": "Eq_DE_Hotplug_002" in after and "Eq_DE_Hotplug_002" not in before,
        "semantic_statements_added": len(additions),
        "executable_code_files_changed": 0,
        "query_changed": False,
        "process_restart_required": False,
        "shacl_conforms": bool(conforms),
        "elapsed_ms_current_host": elapsed_ms,
        "report": str(report_text),
        "boundary": "这是当前模型的数据热插拔实测，不是对所有 SQL 架构的普遍性能证明；SQL 也可设计为数据驱动。",
    }


def evaluate_failure_trace(health: float = 0.30, occluded: bool = True) -> dict[str, Any]:
    if not 0.0 <= health <= 1.0:
        raise ValueError("health must be within [0, 1]")
    graph = Graph()
    observation = DEMO.Observation_Radar_007
    fusion = DEMO.Fusion_Node_001
    decision = DEMO.WTA_HPM_001
    effect = DEMO.Effect_HPM_Failed
    equipment = CUAS.Eq_EW_HPM_001
    threat = DEMO.Threat_09
    graph.add((observation, PROV.wasAttributedTo, CUAS.Eq_RadarUnit_007))
    graph.add((fusion, PROV.used, observation))
    graph.add((decision, PROV.used, fusion))
    graph.add((decision, DEMO.selectedEquipment, equipment))
    graph.add((effect, PROV.wasGeneratedBy, decision))
    graph.add((effect, DEMO.affectsThreat, threat))
    graph.add((effect, DEMO.outcome, Literal("Failed")))
    graph.add((equipment, CUAS.healthScore, Literal(health, datatype=XSD.double)))
    graph.add((equipment, DEMO.lineOfSightOccluded, Literal(occluded, datatype=XSD.boolean)))
    query = """
    PREFIX cuas: <http://cuas-ontology.org/cuas#>
    PREFIX demo: <https://cuas-ontology.org/demo#>
    SELECT ?equipment ?health ?occluded WHERE {
      ?effect demo:outcome "Failed" ;
              <http://www.w3.org/ns/prov#wasGeneratedBy> ?decision .
      ?decision demo:selectedEquipment ?equipment .
      ?equipment cuas:healthScore ?health ; demo:lineOfSightOccluded ?occluded .
      FILTER (?health < 0.5 || ?occluded = true)
    }
    """
    roots = [
        {"equipment": str(row.equipment).rsplit("#", 1)[-1], "health": float(row.health), "occluded": bool(row.occluded.toPython())}
        for row in graph.query(query)
    ]
    return {
        "nodes": [str(node).rsplit("#", 1)[-1] for node in (observation, fusion, decision, effect, equipment, threat)],
        "edges": [
            ("Observation_Radar_007", "usedBy", "Fusion_Node_001"),
            ("Fusion_Node_001", "usedBy", "WTA_HPM_001"),
            ("WTA_HPM_001", "selected", "Eq_EW_HPM_001"),
            ("WTA_HPM_001", "generated", "Effect_HPM_Failed"),
            ("Effect_HPM_Failed", "affects", "Threat_09"),
        ],
        "root_causes": roots,
        "recommended_action": "隔离 HPM、重新计算 WTA，并请求 RF/EO 复核和替代效应器授权。" if roots else "未发现当前规则覆盖的根因。",
        "method": "SPARQL inverse trace plus explicit threshold rules",
        "not_identified_causal_effect": True,
    }
