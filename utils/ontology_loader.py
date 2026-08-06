"""Ontology loader utilities for C-UAS application.

Loads the bundled ontology.json (a Palantir-style 8 OT + 10 LT model) into
convenient Python data structures.  Also exposes a function to materialise it
as an in-memory rdflib Graph (so the SPARQL runner can execute against it).
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Any

import streamlit as st


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ---------------------------------------------------------------------------
# caching helpers
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_ontology() -> Dict[str, Any]:
    """Load and return the whole ontology dictionary (cached)."""
    path = DATA_DIR / "ontology.json"
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


@st.cache_data(show_spinner=False)
def load_airports() -> Dict[str, Any]:
    path = DATA_DIR / "airports.json"
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


@st.cache_data(show_spinner=False)
def load_bayes_params() -> Dict[str, Any]:
    path = DATA_DIR / "bayes_params.json"
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# accessors
# ---------------------------------------------------------------------------
def get_object_types() -> List[Dict[str, Any]]:
    return load_ontology()["object_types"]


def get_link_types() -> List[Dict[str, Any]]:
    return load_ontology()["link_types"]


def get_edges() -> List[Dict[str, Any]]:
    return load_ontology()["edge_instances"]


def summary_stats() -> Dict[str, int]:
    return load_ontology()["summary_stats"]


def get_object_type_by_id(ot_id: str) -> Dict[str, Any]:
    for ot in get_object_types():
        if ot["id"] == ot_id:
            return ot
    raise KeyError(f"ObjectType {ot_id} not found")


def count_instances_by_type() -> Dict[str, int]:
    """Count instances per OT from the bundled sample_instances lists.

    For demo purposes we extrapolate the declared ``instance_count`` value.
    """
    return {ot["id"]: ot.get("instance_count", len(ot.get("sample_instances", [])))
            for ot in get_object_types()}


# ---------------------------------------------------------------------------
# rdflib materialisation (used by SPARQL runner)
# ---------------------------------------------------------------------------
def ontology_as_rdf() -> "rdflib.Graph":  # type: ignore
    """Build an rdflib Graph that mirrors the JSON ontology.

    The graph uses ``cuas:`` as the default namespace and produces triples of the
    form::

        cuas:ObjectType/Mission    rdf:type            owl:Class
        cuas:Mission               rdfs:label          "使命"@zh
        cuas:Mission               cuas:icon           "🛡️"
        cuas:Mission               cuas:color          "#1F4E79"
        cuas:LinkType/L01          rdf:type            owl:ObjectProperty
        cuas:mission_requires_capability  rdfs:domain   cuas:Mission
        cuas:mission_requires_capability  rdfs:range    cuas:TechnicalCapability
        cuas:Edge/L01/MSN-001/CAP-001   cuas:linkType   cuas:L01
    """
    import rdflib
    from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal, URIRef

    g = Graph()
    CUAS = Namespace("https://cuas.ontology.org/")
    g.bind("cuas", CUAS)

    ont = load_ontology()

    # Object Types become OWL classes
    for ot in ont["object_types"]:
        cls = URIRef(CUAS + ot["id"])
        g.add((cls, RDF.type, OWL.Class))
        g.add((cls, RDFS.label,
               Literal(f"{ot['name_zh']} / {ot['name_en']}", lang="zh")))
        g.add((cls, CUAS.icon, Literal(ot["icon"])))
        g.add((cls, CUAS.color, Literal(ot["color"])))
        g.add((cls, CUAS.description, Literal(ot["description"], lang="zh")))
        # Mark as subclass of cuas:ObjectType
        g.add((cls, RDFS.subClassOf, CUAS.ObjectType))

        # Instances
        for inst in ot.get("sample_instances", []):
            inst_uri = URIRef(CUAS + ot["id"] + "/" + inst["id"])
            g.add((inst_uri, RDF.type, cls))
            g.add((inst_uri, RDFS.label, Literal(inst.get("name", inst["id"]), lang="zh")))
            for k, v in inst.items():
                if k in ("id", "name"):
                    continue
                g.add((inst_uri, CUAS[k], Literal(str(v))))

    # Link Types become OWL object properties
    for lt in ont["link_types"]:
        prop = URIRef(CUAS + lt["name"])
        g.add((prop, RDF.type, OWL.ObjectProperty))
        g.add((prop, RDFS.label, Literal(lt["name_zh"], lang="zh")))
        g.add((prop, RDFS.domain, CUAS[lt["from"]]))
        g.add((prop, RDFS.range,  CUAS[lt["to"]]))
        g.add((prop, CUAS.cardinality, Literal(lt["cardinality"])))
        # mark every link type instance
        lt_node = URIRef(CUAS + "LinkType/" + lt["id"])
        g.add((lt_node, RDF.type, CUAS.LinkType))
        g.add((lt_node, RDFS.label, Literal(lt["name_zh"], lang="zh")))

    # Edge instances: reify each triple for traceability.  We store the link
    # type by NAME (e.g. ``cuas:mission_requires_capability``) so the
    # SPARQL templates can filter on it directly.
    for e in ont["edge_instances"]:
        link_id = e["link"]  # e.g. "L01"
        lt_def = next((lt for lt in ont["link_types"] if lt["id"] == link_id), None)
        link_name = lt_def["name"] if lt_def else link_id
        e_uri = URIRef(CUAS + "Edge/" + link_id + "/" + e["from"] + "/" + e["to"])
        g.add((e_uri, RDF.type, CUAS.Edge))
        g.add((e_uri, RDF.type, CUAS.EdgeInstance))
        g.add((e_uri, CUAS.linkType, CUAS[link_name]))
        g.add((e_uri, CUAS.from_instance, Literal(e["from"])))
        g.add((e_uri, CUAS.to_instance,   Literal(e["to"])))

    return g
