"""Page 3 – SPARQL Query / 查询."""
from __future__ import annotations
import re

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from utils.sparql_runner import (
    list_templates,
    template_dataframe,
    run_query,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _try_run(query: str):
    try:
        df = run_query(query)
        return df, None
    except Exception as e:  # noqa: BLE001
        return pd.DataFrame(), str(e)


def _visualize(df: pd.DataFrame, kind: str):
    """Return a Plotly figure for the chosen visualisation kind.

    Charts
    ------
    - ``table`` : no chart
    - ``bar``   : top frequent values for first object-like column
    - ``network`` : build a small directed graph from the result
    """
    if df is None or df.empty:
        return None

    if kind == "table":
        return None

    if kind == "bar":
        # treat the longest-valued string column as a "category" axis
        str_cols = [c for c in df.columns if df[c].dtype == "object"]
        if not str_cols:
            return None
        cat_col = max(str_cols, key=lambda c: df[c].astype(str).str.len().sum())
        cnt = df[cat_col].astype(str).value_counts().head(15)
        fig = px.bar(
            x=cnt.values,
            y=cnt.index.astype(str),
            orientation="h",
            labels={"x": "Count", "y": cat_col},
            title=f"📊 {cat_col} 计数（前 15）",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=420)
        return fig

    if kind == "network":
        # use first 2 string columns as (from, to).  Fall back gracefully.
        str_cols = [c for c in df.columns if df[c].dtype == "object"]
        if len(str_cols) < 2:
            return None
        c1, c2 = str_cols[0], str_cols[1]
        # also use a third column (if exists) as label
        label_col = str_cols[2] if len(str_cols) > 2 else None
        sample = df[[c1, c2] + ([label_col] if label_col else [])].dropna().head(50)
        if sample.empty:
            return None

        nodes = sorted({*sample[c1].astype(str), *sample[c2].astype(str)})
        nid = {n: i for i, n in enumerate(nodes)}
        import math
        # place nodes on a circle
        coords = {}
        n = len(nodes)
        for i, node in enumerate(nodes):
            theta = 2 * math.pi * i / max(n, 1)
            coords[node] = (math.cos(theta), math.sin(theta))

        ex, ey = [], []
        for _, row in sample.iterrows():
            x0, y0 = coords[str(row[c1])]
            x1, y1 = coords[str(row[c2])]
            ex += [x0, x1, None]
            ey += [y0, y1, None]

        edge_trace = go.Scatter(
            x=ex, y=ey, mode="lines",
            line=dict(width=1, color="#888"),
            hoverinfo="none", showlegend=False,
        )
        nx = [coords[n][0] for n in nodes]
        ny = [coords[n][1] for n in nodes]
        node_trace = go.Scatter(
            x=nx, y=ny, mode="markers+text",
            text=nodes, textposition="top center",
            marker=dict(size=20, color="#1F4E79", line=dict(color="white", width=2)),
            hoverinfo="text",
            showlegend=False,
        )
        fig = go.Figure(data=[edge_trace, node_trace])
        fig.update_layout(
            title=f"🕸 {c1} → {c2} 关系图（前 {len(sample)} 条）",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=520,
            plot_bgcolor="#F8F9FB",
        )
        return fig

    return None


# ---------------------------------------------------------------------------
# Page entry
# ---------------------------------------------------------------------------
def show() -> None:
    st.title("🔍 SPARQL 实时查询")
    st.markdown(
        """
        直接在通过 HermiT/SHACL 验证的 TBox + 正向 ABox 上运行 **SPARQL 查询**，追踪使命、场景、能力、装备与效果闭环。

        - **5 个内置模板** 一键运行
        - **完全自由** 的自定义查询
        - **实时可视化**（表格 / 条形图 / 网络图）
        """
    )

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------
    st.header("📜 内置查询模板（5 个）")

    templates = list_templates()
    tab_labels = [t["name"] for t in templates]
    tabs = st.tabs(tab_labels)

    for i, (tab, tpl) in enumerate(zip(tabs, templates)):
        with tab:
            st.markdown(f"**📌 说明**：{tpl['description']}")
            with st.expander("🔎 查看 SPARQL 源码", expanded=False):
                st.code(tpl["sparql"].strip(), language="sparql")

            run_t = st.button(f"▶ 运行查询：{tpl['name']}", key=f"run_tpl_{i}")

            if run_t:
                with st.spinner(f"正在执行 {tpl['name']} ..."):
                    df = template_dataframe(tpl["key"])
                st.session_state[f"tpl_result_{i}"] = (df, tpl["viz"])

            if f"tpl_result_{i}" in st.session_state:
                df, viz_kind = st.session_state[f"tpl_result_{i}"]
                if df.empty:
                    st.warning("查询返回空结果。请检查本体实例是否包含对应边。")
                else:
                    # Stats
                    k1, k2, k3 = st.columns(3)
                    k1.metric("结果行数", len(df))
                    k2.metric("列数", len(df.columns))
                    k3.metric("可视化", {"table": "📋 表格", "bar": "📊 条形图", "network": "🕸 网络图"}.get(viz_kind, viz_kind))
                    fig = _visualize(df, viz_kind)
                    if fig is not None:
                        st.plotly_chart(fig, width="stretch")
                    st.dataframe(df, width="stretch", hide_index=True)

    st.markdown("---")

    # ------------------------------------------------------------------
    # Custom SPARQL
    # ------------------------------------------------------------------
    st.header("✍️ 自定义 SPARQL 查询")

    if "custom_query" not in st.session_state:
        st.session_state["custom_query"] = (
            "PREFIX cuas: <http://cuas-ontology.org/cuas#>\n"
            "SELECT ?mission ?asset WHERE {\n"
            "  ?mission a cuas:Mission ; cuas:protects ?asset .\n"
            "} LIMIT 20"
        )

    cust = st.text_area(
        "输入您的 SPARQL 查询",
        value=st.session_state["custom_query"],
        height=180,
        help="前缀建议：PREFIX cuas: <http://cuas-ontology.org/cuas#>",
    )
    st.session_state["custom_query"] = cust

    viz_choice = st.radio(
        "结果可视化",
        options=["table", "bar", "network"],
        horizontal=True,
        format_func=lambda k: {"table": "📋 仅表格", "bar": "📊 条形图", "network": "🕸 网络图"}[k],
        key="custom_viz",
    )

    cols_run = st.columns([1, 5])
    if cols_run[0].button("▶ 运行", key="run_custom"):
        with st.spinner("正在执行 SPARQL ..."):
            df, err = _try_run(cust)
        if err:
            st.error(err)
        elif df.empty:
            st.warning("返回 0 行。请检查变量名与本体 URIs。")
        else:
            st.success(f"✅ 查询成功，返回 {len(df)} 行 · {len(df.columns)} 列")
            cc1, cc2 = st.columns(2)
            cc1.metric("结果行数", len(df))
            cc2.metric("列数", len(df.columns))
            fig = _visualize(df, viz_choice)
            if fig is not None:
                st.plotly_chart(fig, width="stretch")
            st.dataframe(df, width="stretch", hide_index=True)

    # ------------------------------------------------------------------
    # Reference / Help
    # ------------------------------------------------------------------
    with st.expander("📚 本体前缀与变量参考", expanded=False):
        st.markdown(
            """
            | 前缀 | 命名空间 | 说明 |
            |------|---------|------|
            | `cuas:` | `http://cuas-ontology.org/cuas#` | 本体主命名空间 |
            | `rdf:`  | `http://www.w3.org/1999/02/22-rdf-syntax-ns#` | RDF 核心 |
            | `rdfs:` | `http://www.w3.org/2000/01/rdf-schema#` | RDF Schema |
            | `owl:`  | `http://www.w3.org/2002/07/owl#` | OWL |

            **常用类 / 属性**：

            - 核心类：`cuas:Mission` `cuas:Scenario` `cuas:TechnicalCapability` `cuas:Equipment` `cuas:EffectMetric` `cuas:Threat` `cuas:Asset` `cuas:Operator`
            - 核心关系：`governs` `allocates` `measuredBy` `implements` `covers` `produces` `protects` `confronts` `validates` `operates`
            - 实例：`Mission_G20Summit` · `Threat_Swarm_20` · `Eq_EW_HPM_001` 等
            """
        )

    st.markdown("---")
    st.caption("页 3 · SPARQL Query · 基于 rdflib 7.0")


if __name__ == "__main__":
    show()
