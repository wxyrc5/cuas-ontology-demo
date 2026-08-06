"""SPARQL execution utilities.

We expose:

- ``run_query(query)`` — execute against the rdflib graph built from
  ``ontology.json`` and return a list of dict rows.
- ``run_query_from_json(template_name)`` — execute one of the 5 bundled query
  templates and return a pandas DataFrame.
- ``Built-in templates`` — anti-swarm / airport-protection style queries that
  demonstrate the ontological reasoning over the kill web.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional

import pandas as pd
import streamlit as st

try:
    from SPARQLWrapper import SPARQLWrapper  # noqa: F401  (only here for friendly import err)
except ImportError:  # noqa
    pass

from .ontology_loader import ontology_as_rdf


# ---------------------------------------------------------------------------
# 5 built-in templates
# ---------------------------------------------------------------------------
BUILTIN_TEMPLATES: List[Dict[str, Any]] = [
    {
        "key": "anti_swarm",
        "name": "🔴 反蜂群：探测-效应器完整杀伤链",
        "description": "Finding the equipment in the kill-web that can detect → identify → engage each threat in a swarm scenario.",
        "sparql": """
            PREFIX cuas: <https://cuas.ontology.org/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?threat ?threatName ?equipment ?equipmentName ?capability WHERE {
              ?edge1 a cuas:Edge ; cuas:linkType cuas:scenario_involves_threat ;
                     cuas:from_instance ?scenario ;
                     cuas:to_instance ?threat .
              ?edge2 a cuas:Edge ; cuas:linkType cuas:equipment_counters_threat ;
                     cuas:from_instance ?equipment ;
                     cuas:to_instance ?threat .
              ?edge3 a cuas:Edge ; cuas:linkType cuas:capability_implemented_by_equipment ;
                     cuas:from_instance ?capability ;
                     cuas:to_instance ?equipment .
              OPTIONAL { ?threat rdfs:label ?threatName }
              OPTIONAL { ?equipment rdfs:label ?equipmentName }
              OPTIONAL { ?capability rdfs:label ?capability }
            } LIMIT 50
        """,
        "viz": "table",
    },
    {
        "key": "asset_protection",
        "name": "🛡️ 机场防护：威胁→资产→使命反向追溯",
        "description": "For each protected asset, find the threats that target it and the missions that protect it.",
        "sparql": """
            PREFIX cuas: <https://cuas.ontology.org/>
            SELECT ?threat ?asset ?mission WHERE {
              ?e1 a cuas:Edge ; cuas:linkType cuas:threat_targets_asset ;
                  cuas:from_instance ?threat ; cuas:to_instance ?asset .
              ?e2 a cuas:Edge ; cuas:linkType cuas:mission_protects_asset ;
                  cuas:from_instance ?mission ; cuas:to_instance ?asset .
            }
        """,
        "viz": "table",
    },
    {
        "key": "kill_chain",
        "name": "⚙️ 杀伤链：装备-能力-指标闭环",
        "description": "Compute the equipment → capability → effect-metric chain that defines operational effectiveness.",
        "sparql": """
            PREFIX cuas: <https://cuas.ontology.org/>
            SELECT ?equipment ?capability ?metric WHERE {
              ?e1 a cuas:Edge ; cuas:linkType cuas:capability_implemented_by_equipment ;
                  cuas:from_instance ?capability ; cuas:to_instance ?equipment .
              ?e2 a cuas:Edge ; cuas:linkType cuas:capability_achieves_metric ;
                  cuas:from_instance ?capability ; cuas:to_instance ?metric .
            }
        """,
        "viz": "table",
    },
    {
        "key": "operator_roster",
        "name": "👤 操作员：装备-使命-人员配置",
        "description": "List each operator's certified equipment and assigned mission.",
        "sparql": """
            PREFIX cuas: <https://cuas.ontology.org/>
            SELECT ?operator ?equipment ?mission WHERE {
              ?e1 a cuas:Edge ; cuas:linkType cuas:equipment_operated_by_operator ;
                  cuas:from_instance ?equipment ; cuas:to_instance ?operator .
              ?e2 a cuas:Edge ; cuas:linkType cuas:operator_assigned_to_mission ;
                  cuas:from_instance ?operator ; cuas:to_instance ?mission .
            }
        """,
        "viz": "table",
    },
    {
        "key": "ontology_schema",
        "name": "🧬 本体架构：8 OT ↔ 10 LT 全图",
        "description": "Dump of all object types, link types and their domain/range — perfect for visualising the ontology schema.",
        "sparql": """
            PREFIX cuas: <https://cuas.ontology.org/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?prop ?domain ?range WHERE {
              ?prop a ?ptype ;
                    rdfs:domain ?domain ;
                    rdfs:range  ?range .
              FILTER (STRSTARTS(STR(?prop),   "https://cuas.ontology.org/"))
              FILTER (STRSTARTS(STR(?domain), "https://cuas.ontology.org/"))
              FILTER (STRSTARTS(STR(?range),  "https://cuas.ontology.org/"))
              FILTER (REGEX(STR(?domain), "cuas.ontology.org/(Mission|Scenario|TechnicalCapability|Equipment|EffectMetric|Threat|Asset|Operator)$"))
            }
        """,
        "viz": "network",
    },
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="查询本体中...")
def run_query(query: str) -> pd.DataFrame:
    """Execute SPARQL against the in-memory ontology and return a DataFrame.

    We catch rdflib errors so the UI doesn't crash on malformed input.
    """
    try:
        from rdflib.plugins.sparql.evaluate import SPARQLError, ParseException  # type: ignore
        SPARQL_ERRORS: tuple = (SPARQLError, ParseException, ValueError, SyntaxError)
    except ImportError:  # older rdflib versions
        SPARQL_ERRORS = (ValueError, SyntaxError)  # type: ignore

    g = ontology_as_rdf()
    try:
        res = g.query(query)
    except SPARQL_ERRORS as e:
        raise ValueError(f"SPARQL 语法错误: {e}") from e
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"查询失败: {e}") from e

    # Convert to list of dicts by inspecting the result vars
    rows = []
    # rdflib 7.x: vars attribute; older: labels
    var_names = getattr(res, "vars", None) or getattr(res, "labels", None) or []
    for row in res:
        try:
            # Row may be a sequence of rdflib Terms
            rows.append({str(k): _stringify(v) for k, v in zip(var_names, row)})
        except TypeError:
            # Defensive fallback: treat as iterable
            values = list(row)
            rows.append({str(var_names[i] if i < len(var_names) else f"col{i}"):
                         _stringify(v) for i, v in enumerate(values)})
    df = pd.DataFrame(rows, columns=[str(v) for v in var_names]) if rows else pd.DataFrame()
    return df


def _stringify(node) -> str:
    """Convert an rdflib term to a printable string (cut the URI prefix)."""
    s = str(node)
    if "/" in s and ("#" in s or s.count("/") > 3):
        return s.split("/")[-1]
    return s


@st.cache_data(show_spinner=False)
def template_dataframe(key: str) -> pd.DataFrame:
    tpl = next((t for t in BUILTIN_TEMPLATES if t["key"] == key), None)
    if tpl is None:
        raise KeyError(f"Template {key} not found")
    return run_query(tpl["sparql"])


def list_templates() -> List[Dict[str, Any]]:
    return BUILTIN_TEMPLATES
