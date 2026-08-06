"""Page 2 – Ontology Browser / 本体浏览."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import networkx as nx

from utils.ontology_loader import (
    load_ontology,
    get_object_types,
    get_link_types,
    get_edges,
    count_instances_by_type,
)


def show() -> None:
    st.title("🧬 反无人机体系本体浏览")
    st.markdown(
        """
        基于 **Palantir Ontology** 方法论构建：
        - **8 个 Object Type** （对象类型）
        - **10 个 Link Type** （关系类型）
        - **39+ 实例边** （Instance-level edges）
        - **200+ 对象实例** （可继续语义推理）
        """
    )
    st.info(
        "💡 **点击 OT 卡片** 展开实例，点击 **网络图节点** 查看其上下游链接。"
    )

    # ------------------------------------------------------------------
    # 8 OT Cards
    # ------------------------------------------------------------------
    st.header("🎨 8 个核心 Object Type")

    classes = [
        ("Mission",              "使命",         "🛡️", "#1F4E79"),
        ("Scenario",             "场景",         "📍", "#2E7D32"),
        ("TechnicalCapability",  "技术能力",     "⚙️", "#E65100"),
        ("Equipment",            "装备",         "🔧", "#6A1B9A"),
        ("EffectMetric",         "效果指标",     "📊", "#C62828"),
        ("Threat",               "威胁",         "⚠️", "#B71C1C"),
        ("Asset",                "资产",         "🏢", "#00695C"),
        ("Operator",             "操作员",       "👤", "#4E342E"),
    ]

    cols = st.columns(4)
    for i, (en, cn, icon, color) in enumerate(classes):
        with cols[i % 4]:
            st.markdown(
                f"""
                <div style="background:{color}; color:white; padding:18px;
                            border-radius:10px; text-align:center; margin:5px;
                            box-shadow:0 4px 8px rgba(0,0,0,0.12);">
                  <div style="font-size:32px;">{icon}</div>
                  <div style="font-size:13px; opacity:0.85; margin-top:6px;">{en}</div>
                  <div style="font-size:20px; font-weight:bold;">{cn}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("")

    # ------------------------------------------------------------------
    # Interactive OT selector → instance table
    # ------------------------------------------------------------------
    with st.container(border=True):
        st.subheader("🔍 点击查看 Object Type 实例")

        ot_objs = get_object_types()
        ot_dict = {ot["id"]: ot for ot in ot_objs}
        counts = count_instances_by_type()

        ot_choice = st.selectbox(
            "选择 Object Type",
            options=[ot["id"] for ot in ot_objs],
            format_func=lambda k: f"{ot_dict[k]['icon']}  {ot_dict[k]['name_zh']} ({k})  —  {counts[k]} 实例",
            key="ot_select",
        )

        if ot_choice:
            sel = ot_dict[ot_choice]
            cc1, cc2, cc3, cc4 = st.columns(4)
            cc1.metric("Object Type", sel["id"])
            cc2.metric("中文名", sel["name_zh"])
            cc3.metric("实例数", counts[sel["id"]])
            cc4.metric("属性数", len(sel.get("properties", [])))

            st.markdown(f"**📝 描述**：{sel['description']}")
            st.markdown("**🔑 属性（Property Type）**:")
            st.code(" · ".join(sel.get("properties", [])), language="text")

            sample_df = pd.DataFrame(sel.get("sample_instances", []))
            if not sample_df.empty:
                st.markdown("**📋 示例实例（前 5 个）**")
                st.dataframe(sample_df, use_container_width=True, hide_index=True)
            else:
                st.warning("暂无样本实例。")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Network graph of 10 Link Types
    # ------------------------------------------------------------------
    st.header("🔗 10 个核心 Link Type 网络图")

    link_types = get_link_types()
    edges_df = pd.DataFrame(get_edges())

    left, right = st.columns([3, 1])
    with left:
        # Build a multi-graph so we can have multiple edges between the same OTs
        G = nx.MultiDiGraph()
        for ot in get_object_types():
            G.add_node(ot["id"], label=ot["name_zh"], color=ot["color"], icon=ot["icon"])
        for lt in link_types:
            # do not add an edge for every instance — just the schema-level edge
            G.add_edge(lt["from"], lt["to"],
                       label=lt["name"], label_zh=lt["name_zh"],
                       lid=lt["id"], weight=1)

        # Use a deterministic layout — Kamada–Kawai for clean visuals
        pos = nx.spring_layout(G, seed=42, k=2.2, iterations=200)

        edge_traces = []
        edge_labels = []
        for lt in link_types:
            x0, y0 = pos[lt["from"]]
            x1, y1 = pos[lt["to"]]
            edge_traces.append(
                go.Scatter(
                    x=[x0, x1, None],
                    y=[y0, y1, None],
                    line=dict(width=2.0, color="#888"),
                    hoverinfo="none",
                    mode="lines",
                    showlegend=False,
                )
            )
            # Mid-point label
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            edge_labels.append((mx, my, f"L{lt['id']}: {lt['name_zh']}"))

        node_xs, node_ys, node_text, node_colors, node_sizes, node_hover = [], [], [], [], [], []
        for n in G.nodes():
            x, y = pos[n]
            node_xs.append(x)
            node_ys.append(y)
            node_text.append(G.nodes[n]["label"])
            node_colors.append(G.nodes[n]["color"])
            node_sizes.append(60)
            node_hover.append(
                f"<b>{n}</b><br>{G.nodes[n]['label']}<br>"
                f"实例数: {counts.get(n, 0)}"
            )

        node_trace = go.Scatter(
            x=node_xs,
            y=node_ys,
            mode="markers+text",
            text=node_text,
            textposition="top center",
            hovertext=node_hover,
            hoverinfo="text",
            marker=dict(
                size=node_sizes,
                color=node_colors,
                line=dict(width=3, color="white"),
            ),
            showlegend=False,
        )

        layout = go.Layout(
            title=dict(text="8 OT (节点)  ×  10 LT (有向边)", x=0.5),
            hovermode="closest",
            margin=dict(b=20, l=20, r=20, t=50),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=540,
            plot_bgcolor="#F8F9FB",
        )

        fig = go.Figure(data=edge_traces + [node_trace], layout=layout)
        # Edge labels as annotations
        for mx, my, lbl in edge_labels:
            fig.add_annotation(
                x=mx, y=my,
                text=f"<span style='font-size:10px;color:#444'>{lbl}</span>",
                showarrow=False,
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor="#999",
                borderwidth=0,
            )

        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("### 🗒️ Link Type 列表")
        lt_df = pd.DataFrame([
            {
                "ID": lt["id"],  # already "L01" .. "L10"
                "名称": lt["name"],
                "中文": lt["name_zh"],
                "From": lt["from"],
                "To": lt["to"],
            }
            for lt in link_types
        ])
        st.dataframe(lt_df, use_container_width=True, hide_index=True, height=540)

    st.markdown("---")

    # ------------------------------------------------------------------
    # Click-and-explore: pick a Link Type → see all instances
    # ------------------------------------------------------------------
    st.header("🎯 按 Link Type 浏览实例")

    link_choice = st.selectbox(
        "选择 Link Type",
        options=[lt["id"] for lt in link_types],
        format_func=lambda x: f"L{x} · "
            + next((lt["name_zh"] for lt in link_types if lt["id"] == x), ""),
    )

    edges_filt = edges_df[edges_df["link"] == link_choice] if not edges_df.empty else edges_df
    if edges_filt.empty:
        st.info("该 Link Type 在样例中没有实例。")
    else:
        st.dataframe(edges_filt, use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📈 本体规模")
    stats = load_ontology()["summary_stats"]
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Object Type", stats["total_object_types"])
    sc2.metric("Link Type", stats["total_link_types"])
    sc3.metric("样本实例", stats["total_object_instances"])
    sc4.metric("实例边", stats["total_edge_instances"])


if __name__ == "__main__":
    show()
