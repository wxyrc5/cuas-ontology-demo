"""Ontology loader utilities for C-UAS application.

Loads the aligned browser metadata from ``ontology.json`` and exposes the
validated canonical Turtle TBox + positive ABox as an in-memory RDFLib graph.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Any

import streamlit as st


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MODEL_DIR = Path(__file__).resolve().parents[2] / "本体模型"


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
    """Count only the instance fixtures actually bundled in ontology.json."""
    return {ot["id"]: len(ot.get("sample_instances", []))
            for ot in get_object_types()}


# ---------------------------------------------------------------------------
# rdflib materialisation (used by SPARQL runner)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def ontology_as_rdf() -> "rdflib.Graph":  # type: ignore
    """Load the validated canonical OWL TBox and coherent positive ABox.

    The SPARQL page therefore queries the same ``cuas-ontology.ttl`` and
    ``cuas-data-valid.ttl`` files that Notebook 01 sends to SHACL/HermiT,
    instead of a separately materialised demo graph with different links.
    """
    from rdflib import Graph, Namespace

    tbox_path = MODEL_DIR / "cuas-ontology.ttl"
    abox_path = MODEL_DIR / "cuas-data-valid.ttl"
    if not tbox_path.is_file() or not abox_path.is_file():
        raise FileNotFoundError(f"Canonical ontology files missing under {MODEL_DIR}")

    graph = Graph()
    graph.parse(tbox_path, format="turtle")
    graph.parse(abox_path, format="turtle")
    graph.bind("cuas", Namespace("http://cuas-ontology.org/cuas#"))
    return graph
