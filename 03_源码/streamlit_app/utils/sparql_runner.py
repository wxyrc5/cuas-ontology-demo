"""SPARQL execution utilities.

We expose:

- ``run_query(query)`` — execute against the validated canonical Turtle TBox
  plus positive ABox and return a pandas DataFrame.
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
        "name": "🔴 反蜂群：使命-威胁-能力-装备-效果",
        "description": "沿着技术方案规定的核心关系，追溯反蜂群使命分配的能力、实现装备与反馈效果。",
        "sparql": """
            PREFIX cuas: <http://cuas-ontology.org/cuas#>
            SELECT ?mission ?threat ?capability ?equipment ?effect WHERE {
              ?mission a cuas:Mission ;
                       cuas:confronts ?threat ;
                       cuas:allocates ?capability .
              ?equipment cuas:implements ?capability .
              ?capability cuas:produces ?effect .
            } ORDER BY ?capability
        """,
        "viz": "network",
    },
    {
        "key": "asset_protection",
        "name": "🛡️ 要地防护：使命→资产与威胁",
        "description": "查询同一使命保护的资产和所对抗的蜂群威胁。",
        "sparql": """
            PREFIX cuas: <http://cuas-ontology.org/cuas#>
            SELECT ?threat ?asset ?mission WHERE {
              ?mission a cuas:Mission ; cuas:protects ?asset ; cuas:confronts ?threat .
            }
        """,
        "viz": "table",
    },
    {
        "key": "kill_chain",
        "name": "⚙️ 杀伤链：装备-能力-指标闭环",
        "description": "查询 Equipment→implements→Capability→produces→EffectMetric，并显示装备覆盖的 OODA 场景。",
        "sparql": """
            PREFIX cuas: <http://cuas-ontology.org/cuas#>
            SELECT ?equipment ?capability ?metric ?scenario WHERE {
              ?equipment a cuas:Equipment ;
                         cuas:implements ?capability ;
                         cuas:covers ?scenario .
              ?capability cuas:produces ?metric .
            }
        """,
        "viz": "table",
    },
    {
        "key": "operator_roster",
        "name": "👤 操作员：人员-装备-能力-场景",
        "description": "从 Operator→operates→Equipment 继续追踪该装备实现的能力和覆盖场景。",
        "sparql": """
            PREFIX cuas: <http://cuas-ontology.org/cuas#>
            SELECT ?operator ?equipment ?capability ?scenario WHERE {
              ?operator a cuas:Operator ; cuas:operates ?equipment .
              ?equipment cuas:implements ?capability ; cuas:covers ?scenario .
            }
        """,
        "viz": "table",
    },
    {
        "key": "ontology_schema",
        "name": "🧬 本体架构：8 OT ↔ 10 LT 全图",
        "description": "Dump of all object types, link types and their domain/range — perfect for visualising the ontology schema.",
        "sparql": """
            PREFIX cuas: <http://cuas-ontology.org/cuas#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            SELECT ?prop ?domain ?range WHERE {
              ?prop a owl:ObjectProperty ;
                    rdfs:domain ?domain ;
                    rdfs:range  ?range .
              VALUES ?prop { cuas:governs cuas:allocates cuas:measuredBy cuas:implements
                             cuas:covers cuas:produces cuas:protects cuas:confronts
                             cuas:validates cuas:operates }
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
    if "#" in s:
        return s.rsplit("#", 1)[-1]
    if "/" in s and s.count("/") > 3:
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
