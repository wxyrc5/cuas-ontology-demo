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
from utils.ontology_action_engine import (
    action_result_to_json,
    action_result_to_turtle,
    evaluate_action_feedback,
    load_baseline_operational_state,
)


def show() -> None:
    stats = load_ontology()["summary_stats"]
    st.title("🧬 反无人机体系本体浏览")
    st.markdown(
        f"""
        基于 **Palantir Ontology** 方法论构建：
        - **8 个 Object Type** （对象类型）
        - **10 个 Link Type** （关系类型）
        - **{stats['total_edge_instances']} 条正向 ABox 关系** （Instance-level edges）
        - **{stats['total_object_instances']} 个正向 ABox 核心实例** （与 HermiT/SHACL 验证同源）
        """
    )
    st.info(
        "💡 本页的 8 OT、10 LT 和实例关系与正式 Turtle 模型一致；实例仍是工程验证夹具，不代表真实部署规模。"
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
            cc3.metric("随包样例数", counts[sel["id"]])
            cc4.metric("属性数", len(sel.get("properties", [])))

            st.markdown(f"**📝 描述**：{sel['description']}")
            st.markdown("**🔑 属性（Property Type）**:")
            st.code(" · ".join(sel.get("properties", [])), language="text")

            sample_df = pd.DataFrame(sel.get("sample_instances", []))
            if not sample_df.empty:
                st.markdown("**📋 示例实例（前 5 个）**")
                st.dataframe(sample_df, width="stretch", hide_index=True)
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
            edge_labels.append((mx, my, f"{lt['id']}: {lt['name_zh']}"))

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
                f"随包样例数: {counts.get(n, 0)}"
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

        st.plotly_chart(fig, width="stretch")

    with right:
        st.markdown("### 🗒️ Link Type 列表")
        lt_df = pd.DataFrame([
            {
                "ID": str(lt["id"]),
                "名称": lt["name"],
                "中文": lt["name_zh"],
                "From": lt["from"],
                "To": lt["to"],
            }
            for lt in link_types
        ])
        st.dataframe(lt_df, width="stretch", hide_index=True, height=540)

    st.markdown("---")

    # ------------------------------------------------------------------
    # Click-and-explore: pick a Link Type → see all instances
    # ------------------------------------------------------------------
    st.header("🎯 按 Link Type 浏览实例")

    link_choice = st.selectbox(
        "选择 Link Type",
        options=[lt["id"] for lt in link_types],
        format_func=lambda x: f"{x} · "
            + next((lt["name_zh"] for lt in link_types if lt["id"] == x), ""),
    )

    edges_filt = edges_df[edges_df["link"] == link_choice] if not edges_df.empty else edges_df
    if edges_filt.empty:
        st.info("该 Link Type 在样例中没有实例。")
    else:
        st.dataframe(edges_filt, width="stretch", hide_index=True)

    st.markdown("---")

    # ------------------------------------------------------------------
    # Manuscript Effect -> Action -> Mission feedback prototype
    # ------------------------------------------------------------------
    st.header("🔁 Effect → Action → Mission 写回原型")
    st.info(
        "本模块把文字稿中的阈值规则变成确定性 Action 计划：自动动作写入会话状态，"
        "资源增配与批量授权进入人工审批队列，并可导出带溯源的 RDF。"
        "正式 OWL/ABox 文件始终只读；这不是 Palantir Foundry 或真实装备接入。"
    )

    baseline_state = load_baseline_operational_state()
    left_controls, right_controls = st.columns(2)
    with left_controls:
        detection_coverage = st.slider(
            "探测覆盖率", 0.50, 1.00, 0.88, 0.01, key="action_detection"
        )
        identification_accuracy = st.slider(
            "识别准确率", 0.50, 1.00, 0.83, 0.01, key="action_identification"
        )
        interception_success = st.slider(
            "拦截成功率", 0.50, 1.00, 0.82, 0.01, key="action_interception"
        )
        false_alarm_rate = st.slider(
            "虚警率", 0.0, 0.10, 0.025, 0.001, format="%.3f", key="action_false_alarm"
        )
    with right_controls:
        ooda_closure_time = st.slider(
            "OODA 完整闭环（秒）", 1.0, 10.0, 5.4, 0.1, key="action_ooda"
        )
        mission_priority = st.slider(
            "当前使命优先级", 1, 5, 3, 1, key="action_mission_priority"
        )
        previous_threat_level = st.slider(
            "上一周期威胁等级", 1, 5, 3, 1, key="action_threat_previous"
        )
        current_threat_level = st.slider(
            "当前威胁等级", 1, 5, 5, 1, key="action_threat_current"
        )
        failed_equipment = st.multiselect(
            "本周期故障装备",
            options=sorted(baseline_state["equipment_status"]),
            default=["Eq_EW_HPM_001"],
            key="action_failed_equipment",
        )

    baseline_state["priority"] = mission_priority
    action_result = evaluate_action_feedback(
        metrics={
            "detection_coverage": detection_coverage,
            "identification_accuracy": identification_accuracy,
            "ooda_closure_time_s": ooda_closure_time,
            "interception_success_rate": interception_success,
            "false_alarm_rate": false_alarm_rate,
        },
        context={
            "threat_level_previous": previous_threat_level,
            "threat_level_current": current_threat_level,
            "failed_equipment_ids": failed_equipment,
        },
        state=baseline_state,
    )
    summary = action_result["summary"]
    ac1, ac2, ac3, ac4 = st.columns(4)
    ac1.metric("触发规则", summary["triggered_rules"])
    ac2.metric("自动写回", summary["auto_applied"])
    ac3.metric("待人工授权", summary["pending_human_authorization"])
    ac4.metric("决策编号", action_result["decision_id"])

    action_df = pd.DataFrame(
        [
            {
                "规则": item["rule_id"],
                "Action": item["action_code"],
                "状态": item["execution_status"],
                "说明": item["description"],
            }
            for item in action_result["actions"]
        ]
    )
    if action_df.empty:
        st.success("当前输入未触发调整规则，使命状态保持不变。")
    else:
        st.dataframe(action_df, width="stretch", hide_index=True)

    before = action_result["before_state"]
    after = action_result["after_state"]
    state_diff = pd.DataFrame(
        [
            {"状态项": "使命优先级", "写回前": before["priority"], "写回后": after["priority"]},
            {"状态项": "雷达扫描模式", "写回前": before["controls"]["scan_mode"], "写回后": after["controls"]["scan_mode"]},
            {"状态项": "融合模型", "写回前": before["controls"]["fusion_model"], "写回后": after["controls"]["fusion_model"]},
            {"状态项": "告警确认", "写回前": before["controls"]["fusion_confirmation"], "写回后": after["controls"]["fusion_confirmation"]},
            {"状态项": "WTA 重算", "写回前": before["controls"]["wta_recompute_requested"], "写回后": after["controls"]["wta_recompute_requested"]},
            {"状态项": "待人工授权", "写回前": "无", "写回后": "、".join(after["pending_human_actions"]) or "无"},
        ]
    ).astype(str)
    st.dataframe(state_diff, width="stretch", hide_index=True)

    action_ttl = action_result_to_turtle(action_result)
    with st.expander("查看 RDF 写回预览（独立图，不修改正式本体）"):
        st.code(action_ttl, language="turtle")
    download_left, download_right = st.columns(2)
    with download_left:
        st.download_button(
            "下载 Action JSON",
            data=action_result_to_json(action_result),
            file_name=f"{action_result['decision_id']}.json",
            mime="application/json",
        )
    with download_right:
        st.download_button(
            "下载 RDF 写回预览",
            data=action_ttl,
            file_name=f"{action_result['decision_id']}.ttl",
            mime="text/turtle",
        )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📈 本体规模")
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Object Type", stats["total_object_types"])
    sc2.metric("Link Type", stats["total_link_types"])
    sc3.metric("随包样例实例", stats["total_object_instances"])
    sc4.metric("随包样例边", stats["total_edge_instances"])


if __name__ == "__main__":
    show()
