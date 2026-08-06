"""Page 5 – Airport Counter-UAS Simulation / 机场反无决策演示."""
from __future__ import annotations
import math
import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from utils.ontology_loader import load_airports


# ---------------------------------------------------------------------------
# Simulation kernel
# ---------------------------------------------------------------------------
def simulate(
    n_uavs: int,
    threat_level: int,
    effectors: list,
    airport_data: dict,
    n_iterations: int = 12,
) -> dict:
    """Very fast deterministic-ish OODA simulation.

    Each OODA cycle (Observe → Orient → Decide → Act → Feedback) emits a
    tick.  We model the swarm as a 2-D field on a circle around the airport
    centroid.  Effectors apply their Pk inversely with range and crowd.
    """
    rng = np.random.default_rng(2025)

    # Use bayesian-style adaptive Pd that grows slightly with swarm size if more
    # effectors are present (mitigation).
    effector_eff = sum({"EW": 0.05, "HPM": 0.18, "HEL": 0.22, "Kinetic": 0.20, "Net": 0.10}.get(e, 0)
                       for e in effectors)
    base_pd = min(0.99, 0.85 + effector_eff)
    base_pk = min(0.99, 0.80 + 0.45 * effector_eff)

    # Threat energy scales with threat_level (1-5) and number of uavs
    energy = n_uavs * (0.6 + 0.2 * threat_level)
    pk = max(0.45, base_pk - 0.005 * energy + 0.02 * rng.normal())
    pk = float(np.clip(pk, 0.45, 0.99))

    # OODA — Bayesian squeeze reduces time, more nodes reduce it slightly
    observe = 0.6 + 0.20 / max(n_iterations, 5)
    orient = 0.8 + 0.10 * max(0, threat_level - 3) / 2
    decide = 0.9 + 0.10 * (n_uavs / 50)
    act = 1.1 + 0.05 * n_uavs / 10
    feedback = 0.35 + 0.05 * max(0, len(effectors) - 2)
    ooda_total = observe + orient + decide + act + feedback

    # FAR/Pd summary
    pd = base_pd - 0.002 * energy
    far = max(0.005, 0.04 - effector_eff * 0.4)

    # Build 2D trajectories
    centroid_lat, centroid_lon = airport_data["latitude"], airport_data["longitude"]
    n_frames = 60
    angles = rng.uniform(0, 2 * math.pi, size=n_uavs)
    distances_start = rng.uniform(3.5, 6.0, size=n_uavs)  # km
    distances_end = distances_start * rng.uniform(0.05, 0.6, size=n_uavs)

    # engagement speeds
    speeds = rng.uniform(0.06, 0.18, size=n_uavs)  # km/frame

    traj = np.zeros((n_uavs, n_frames, 2))
    for f in range(n_frames):
        t = f / (n_frames - 1)
        r = distances_start * (1 - t) + distances_end * t
        # small jitter
        jitter = rng.normal(0, 0.05, size=(n_uavs, 2)) * (1 - t)
        traj[:, f, 0] = centroid_lat + (r / 110.0) * np.cos(angles) + jitter[:, 0]
        traj[:, f, 1] = centroid_lon + (r / 111.0) * np.sin(angles) + jitter[:, 1]

    # engagement frames — each uav gets knocked down at a different frame
    eng_frames = rng.integers(int(n_frames * 0.4), int(n_frames * 0.9), size=n_uavs)

    return {
        "ooda_phases": [
            {"phase": "Observe",  "name_zh": "观察", "t": observe, "color": "#1565C0"},
            {"phase": "Orient",   "name_zh": "判断", "t": orient,  "color": "#2E7D32"},
            {"phase": "Decide",   "name_zh": "决策", "t": decide,  "color": "#E65100"},
            {"phase": "Act",      "name_zh": "行动", "t": act,     "color": "#C62828"},
            {"phase": "Feedback", "name_zh": "评估", "t": feedback,"color": "#6A1B9A"},
        ],
        "ooda_total": ooda_total,
        "pk": pk,
        "pd": float(np.clip(pd, 0.5, 0.99)),
        "far": float(far),
        "energy": float(energy),
        "traj": traj,                       # (n_uavs, n_frames, 2)
        "eng_frames": eng_frames.tolist(),  # per-uav engagement frame
        "centroid": (centroid_lat, centroid_lon),
        "effectors": effectors,
        "n_uavs": n_uavs,
        "threat_level": threat_level,
    }


# ---------------------------------------------------------------------------
# Visualisation helpers
# ---------------------------------------------------------------------------
def render_tactical_map(sim: dict, airport: dict, frame: int):
    traj = sim["traj"]
    n_uavs = sim["n_uavs"]
    engaged_so_far = sum(1 for ef in sim["eng_frames"] if ef <= frame)
    engaged_mask = np.array([ef <= frame for ef in sim["eng_frames"]])

    fig = go.Figure()

    # Asset locations (around centroid)
    cent_lat, cent_lon = sim["centroid"]
    for asset in airport["assets"]:
        # place near centroid with small offset
        offset_lat = (hash(asset["id"]) % 100 - 50) * 5e-4
        offset_lon = (hash(asset["id"]) % 73 - 36) * 7e-4
        fig.add_trace(go.Scattermap(
            lat=[cent_lat + offset_lat],
            lon=[cent_lon + offset_lon],
            mode="markers+text",
            text=[asset["name"]],
            textposition="top right",
            marker=dict(size=14, color="#1F4E79", symbol="castle"),
            name=f"资产 {asset['name']}",
            hovertext=f"{asset['id']} · {asset['name']} · {asset['criticality']}",
        ))

    # Equipment
    for eq in airport["equipment_deployed"]:
        fig.add_trace(go.Scattermap(
            lat=[eq["pos"][0]],
            lon=[eq["pos"][1]],
            mode="markers",
            marker=dict(size=11, color="#2E7D32", symbol="triangle"),
            name=eq["type"],
            text=[eq["type"]],
        ))

    # Drone trajectories up to current frame
    for i in range(n_uavs):
        xs = traj[i, :frame + 1, 1].tolist()
        ys = traj[i, :frame + 1, 0].tolist()
        engaged = engaged_mask[i]
        color = "#D62728" if not engaged else "#7F7F7F"
        fig.add_trace(go.Scattermap(
            lat=ys, lon=xs, mode="lines+markers",
            line=dict(width=2, color=color),
            marker=dict(size=8, color=color, symbol="circle" if not engaged else "x"),
            name=f"UAV {i+1}" + (" ⛔" if engaged else " ⚠️"),
            text=[f"UAV {i+1}: {'已拦截' if engaged else '飞行中'}"],
            showlegend=False,
            hoverinfo="text",
        ))

    # Defender range circles
    for r_km, color in [(3, "rgba(214,39,40,0.18)"), (5, "rgba(31,119,180,0.15)"), (8, "rgba(44,160,44,0.12)")]:
        theta = np.linspace(0, 2 * np.pi, 60)
        ring_lat = cent_lat + (r_km / 110.0) * np.cos(theta)
        ring_lon = cent_lon + (r_km / 111.0) * np.sin(theta)
        fig.add_trace(go.Scattermap(
            lat=ring_lat, lon=ring_lon,
            mode="lines", line=dict(width=1, color=color),
            name=f"防御圈 {r_km} km", showlegend=True,
        ))

    fig.update_layout(
        map=dict(
            style="open-street-map",
            center=dict(lat=cent_lat, lon=cent_lon),
            zoom=12,
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        height=520,
        title=f"{airport['name_zh']} · 帧 {frame+1}/{traj.shape[1]} · 已拦截 {engaged_so_far}/{n_uavs}",
    )
    return fig


def render_ooda_waterfall(sim: dict):
    """Build a waterfall chart that adds up OODA phases."""
    phases = sim["ooda_phases"]
    fig = go.Figure()
    # Cumulative waterfall
    cum = 0.0
    for p in phases:
        fig.add_trace(go.Waterfall(
            name=p["phase"],
            orientation="v",
            measure=["relative"] * 1,
            x=[p["name_zh"]],
            y=[p["t"]],
            text=[f"{p['t']:.2f}s"],
            textposition="outside",
            connector=dict(line=dict(color="rgb(63, 63, 63)")),
            increasing=dict(marker=dict(color=p["color"])),
        ))
        cum += p["t"]
    # total
    fig.add_trace(go.Waterfall(
        name="Total", orientation="v",
        measure=["total"], x=["闭环总时"], y=[cum],
        text=[f"{cum:.2f}s"], textposition="outside",
        connector=dict(line=dict(color="rgb(63, 63, 63)")),
        increasing=dict(marker=dict(color="#1F4E79")),
    ))
    fig.update_layout(
        title="⏱ OODA 闭环时延瀑布",
        yaxis_title="时延 (s)",
        showlegend=False,
        height=380,
        plot_bgcolor="#F8F9FB",
    )
    return fig


def render_pd_pie(sim: dict):
    """Pie chart of engagement outcomes."""
    n_uavs = sim["n_uavs"]
    engaged = int(round(n_uavs * sim["pk"]))
    missed = n_uavs - engaged
    labels = ["已拦截", "漏防"]
    values = [engaged, missed]
    colors = ["#2CA02C", "#D62728"]
    fig = go.Figure(
        data=[go.Pie(
            labels=labels, values=values, hole=0.55,
            marker=dict(colors=colors),
            textinfo="label+percent", textfont=dict(size=16),
        )]
    )
    fig.update_layout(
        title=f"🎯 处置效果 (Pk={sim['pk']*100:.1f}%)",
        height=380,
        annotations=[dict(text=f"{engaged}/{n_uavs}", x=0.5, y=0.5, font_size=28, showarrow=False)],
    )
    return fig


# ---------------------------------------------------------------------------
# Page entry
# ---------------------------------------------------------------------------
def show() -> None:
    st.title("🗺 机场反无决策演示")

    airports_data = load_airports()
    airports_list = airports_data["airports"]
    effectors_meta = airports_data["effectors"]
    demo_scenarios = airports_data["demo_scenarios"]

    # ------------------------------------------------------------------
    # Scenario selector
    # ------------------------------------------------------------------
    st.subheader("🌍 场景选择")

    scen_cols = st.columns([1, 1, 1])
    airport_choice = None
    for i, ap in enumerate(airports_list):
        with scen_cols[i]:
            if st.button(
                f"{ap['name_zh']}\n({ap['icao']})",
                key=f"ap_{ap['id']}",
                use_container_width=True,
                type="primary" if i == 0 else "secondary",
            ):
                airport_choice = ap
    if airport_choice is None:
        airport_choice = airports_list[0]

    airport = airport_choice

    st.markdown("---")

    # ------------------------------------------------------------------
    # Sidebar of parameters
    # ------------------------------------------------------------------
    st.subheader("⚙️ 仿真参数")

    cp1, cp2, cp3 = st.columns(3)

    with cp1:
        st.markdown("**🛸 无人机规模**")
        n_uavs = st.slider("无人机数量", 1, 50, 5, 1, key="n_uavs")

        st.markdown("**⚠️ 威胁等级**")
        threat_level = st.select_slider(
            "选择威胁等级 (1=低, 5=高)",
            options=[1, 2, 3, 4, 5],
            value=3,
            key="threat_level",
        )

    with cp2:
        st.markdown("**💥 效应器组合**")
        eff_options = [e["id"] for e in effectors_meta]
        eff_labels = {e["id"]: f"{e['name']}" for e in effectors_meta}
        effectors = st.multiselect(
            "可选效应器（多选）",
            options=eff_options,
            default=["EW", "Kinetic"],
            format_func=eff_labels.get,
            key="eff_choice",
        )

        st.markdown("**🎬 演示场景预设**")
        scen_labels = [s["name"] for s in demo_scenarios]
        scen_index = st.radio(
            "或选一个预设计算",
            options=list(range(len(demo_scenarios))),
            format_func=lambda i: demo_scenarios[i]["name"],
            key="scen_pick",
        )

    with cp3:
        st.markdown("**▶ 启动仿真**")
        run_sim = st.button("🚀 启动 OODA 仿真", type="primary", use_container_width=True)
        st.markdown("**🎞 帧控制**")
        # session-state based frame counter
        if "frame" not in st.session_state:
            st.session_state["frame"] = 0
        st.session_state["frame"] = st.slider(
            "动画帧 (0-59)", 0, 59, 0, 1, key="anim_frame",
        )
        if st.button("🔄 重置动画", use_container_width=True):
            st.session_state["frame"] = 0

    if scen_index is not None and demo_scenarios:
        # apply preset
        preset = demo_scenarios[scen_index]
        n_uavs = preset["uav_count"]
        # keep the current effectors
        airport_choice = next((a for a in airports_list if a["id"] == preset["airport"]), airport_choice)
        airport = airport_choice
        st.info(
            f"🎯 当前演示场景：{preset['name']} — "
            f"{preset['uav_type']} @ {preset['speed_mps']} m/s · "
            f"预估 OODA {preset['ooda_estimate_s']}s · Pk {preset['pk_estimate']*100:.0f}%"
        )

    # ------------------------------------------------------------------
    # Run sim button OR auto-run when defaults load
    # ------------------------------------------------------------------
    if "sim_result" not in st.session_state or run_sim:
        with st.spinner("正在运行 OODA 仿真..."):
            sim = simulate(
                n_uavs=n_uavs,
                threat_level=threat_level,
                effectors=effectors,
                airport_data=airport,
            )
            st.session_state["sim_result"] = sim

    sim = st.session_state["sim_result"]

    # ------------------------------------------------------------------
    # Results row
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📊 仿真结果")

    r1, r2, r3, r4, r5 = st.columns(5)
    r1.metric("OODA 闭环", f"{sim['ooda_total']:.2f} s",
              f"{airport['ooda_baseline_s']:.2f} baseline")
    r2.metric("拦截成功率 Pk", f"{sim['pk']*100:.1f}%",
              f"{airport['pk_baseline']*100:.1f}% baseline")
    r3.metric("探测概率 Pd", f"{sim['pd']*100:.1f}%")
    r4.metric("虚警率 FAR", f"{sim['far']*100:.2f}%",
              f"{airport['far_baseline']*100:.2f}% baseline")
    r5.metric("威胁能量", f"{sim['energy']:.1f}")

    # ------------------------------------------------------------------
    # Visualisations
    # ------------------------------------------------------------------
    st.markdown("### 🗺 战术地图（实时）")
    map_fig = render_tactical_map(sim, airport, st.session_state["frame"])
    st.plotly_chart(map_fig, use_container_width=True)

    # Animation control hint
    st.info(
        "💡 **操作提示**：拖动 `动画帧` 滑块可视化不同时间点的态势，"
        "已拦截无人机变为灰色 ✕ ，边界圆代表 3/5/8 km 防御圈。"
    )

    # Two side-by-side charts
    cw1, cw2 = st.columns(2)
    with cw1:
        st.markdown("### ⏱ OODA 闭环时延瀑布")
        st.plotly_chart(render_ooda_waterfall(sim), use_container_width=True)
    with cw2:
        st.markdown("### 🎯 处置效果饼图")
        st.plotly_chart(render_pd_pie(sim), use_container_width=True)

    # ------------------------------------------------------------------
    # Effector effectiveness radar
    # ------------------------------------------------------------------
    st.markdown("### 🛡️ 效应器效能比较")

    if effectors:
        e_df = pd.DataFrame([
            {"Effector": eff_labels.get(e["id"], e["id"]),
             "Pk_vs_Swarm": e["pk_against_swarm"],
             "Range_km": e["range_km"],
             "Cost": e["cost"]}
            for e in effectors_meta if e["id"] in effectors
        ])
        if not e_df.empty:
            fig_eff = go.Figure()
            fig_eff.add_trace(go.Bar(
                x=e_df["Effector"], y=e_df["Pk_vs_Swarm"],
                name="Pk 对蜂群",
                marker_color="#1F77B4",
                text=[f"{v*100:.0f}%" for v in e_df["Pk_vs_Swarm"]],
                textposition="outside",
            ))
            fig_eff.add_trace(go.Scatter(
                x=e_df["Effector"], y=e_df["Range_km"] / 10.0,
                name="射程 (归一化 ÷10)",
                yaxis="y2",
                marker=dict(color="#FF7F0E", size=14, symbol="diamond"),
                mode="markers+lines",
            ))
            fig_eff.update_layout(
                yaxis=dict(title="Pk 对蜂群", range=[0, 1]),
                yaxis2=dict(title="射程 (归一化)", overlaying="y", side="right", range=[0, 1]),
                height=380,
                plot_bgcolor="#F8F9FB",
                legend=dict(x=0.55, y=1.0),
            )
            st.plotly_chart(fig_eff, use_container_width=True)

    # ------------------------------------------------------------------
    # Kill web — which OT chain is being exercised in this scenario
    # ------------------------------------------------------------------
    st.markdown("### 🧬 本体杀伤链（本场景触发的 OT 序列）")
    chain_text = (
        "Scenario → Threat → Threat_targets_Asset → Asset → Mission →"
        " Mission_requires_Capability → Capability → Equipment → Operator"
    )
    st.code(chain_text, language="text")
    st.markdown(
        f"""
        - **场景**: {airport['name_zh']} ({airport['icao']})
        - **威胁等级**: **{threat_level} / 5**
        - **目标资产**: {', '.join(a['name'] for a in airport['assets'][:3])}
        - **响应效应器**: {', '.join(effectors) if effectors else '(无)'}
        - **OODA 时延**: **{sim['ooda_total']:.2f}s** (< 5s ✅)
        """
    )

    st.markdown("---")
    st.caption("页 5 · Airport Counter-UAS · Plotly Tactical Map")


if __name__ == "__main__":
    show()
