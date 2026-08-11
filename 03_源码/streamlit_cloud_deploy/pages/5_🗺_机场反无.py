"""Page 5 – Airport Counter-UAS Simulation / 机场反无决策演示."""
from __future__ import annotations
import base64
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.ontology_loader import load_airports
from utils.defense_envelope import (
    contains_xy,
    envelope_boundary_latlon,
    envelope_boundary_xy,
    envelope_surface_xyz,
    hex_to_rgba,
    validate_envelopes,
)
from utils.ooda_model import simulate_ooda_timing
from utils.swarm_adjudication import (
    evaluate_closed_loop_swarm,
    resource_capacity_rows,
)


# ---------------------------------------------------------------------------
# Simulation kernel
# ---------------------------------------------------------------------------
def simulate(
    n_uavs: int,
    threat_level: int,
    effectors: list,
    airport_data: dict,
    degradation_profile: str = "nominal",
    authorization_mode: str = "batch",
    resource_package_count: int = 1,
    n_model_runs: int = 3_000,
    seed: int = 20260812,
    n_frames: int = 60,
) -> dict:
    """Run shared full-chain OODA and capacity-constrained swarm models.

    The display keeps the Final-package V10 trajectory fixes: fixed seed,
    three altitude waves, per-aircraft curved paths, and synchronized events.
    Engagement timing is additionally constrained by entry into the configured
    anisotropic defense envelope.
    """
    rng = np.random.default_rng(seed)
    validate_envelopes(airport_data["defense_envelopes"])

    selected_effectors = list(dict.fromkeys(effectors))
    ooda_effector = next(
        (item for item in ("HPM", "EW", "HEL", "Kinetic", "Net") if item in selected_effectors),
        "EW",
    )
    ooda_degradation = "contested" if degradation_profile == "contested" else "nominal"
    timing = simulate_ooda_timing(
        effector_id=ooda_effector,
        threat_count=n_uavs,
        authorization_mode=authorization_mode,
        degradation_profile=ooda_degradation,
        resource_package_count=resource_package_count,
        coordination_mode="coordination_aware",
        n_runs=n_model_runs,
        seed=seed + 1,
    )

    if selected_effectors:
        closed_loop = evaluate_closed_loop_swarm(
            threat_count=n_uavs,
            enabled_effectors=selected_effectors,
            policy="adaptive",
            degradation_profile=degradation_profile,
            resource_package_count=resource_package_count,
            authorization_mode=authorization_mode,
            coordination_mode="coordination_aware",
            n_runs=n_model_runs,
            seed=seed,
        )
        pk = closed_loop.closed_loop_mission_probability
        engagement_pk = closed_loop.swarm.mission_success_probability
        mean_neutralized = closed_loop.swarm.mean_neutralized
        mission_required = closed_loop.swarm.neutralizations_required
        resource_cost = closed_loop.swarm.mean_resource_cost
        usage_rows = closed_loop.swarm.resource_usage_rows
    else:
        pk = 0.0
        engagement_pk = 0.0
        mean_neutralized = 0.0
        mission_required = int(math.ceil(0.8 * n_uavs))
        resource_cost = 0.0
        usage_rows = []

    phase_names = {
        "Observe": ("观察", "#1565C0"),
        "Orient": ("判断", "#2E7D32"),
        "Decide": ("决策", "#E65100"),
        "Act": ("行动", "#C62828"),
        "Feedback": ("评估", "#6A1B9A"),
    }
    phases = []
    phase_cursor = 0.0
    for phase in timing.phase_rows:
        name_zh, color = phase_names[phase["phase"]]
        duration = float(phase["mean_s"])
        phases.append({
            "phase": phase["phase"],
            "name_zh": name_zh,
            "t": duration,
            "color": color,
            "start": phase_cursor,
            "end": phase_cursor + duration,
        })
        phase_cursor += duration
    ooda_total = float(timing.full_loop_summary["mean_s"])

    # Pd/FAR remain transparent synthetic display indicators; Pk and time use
    # the shared audited models above.
    energy = n_uavs * (0.6 + 0.2 * threat_level)
    degradation_penalty = {"nominal": 0.0, "sensor_degraded": 0.11, "contested": 0.07, "hpm_offline": 0.0}[degradation_profile]
    pd = float(np.clip(0.97 - degradation_penalty - 0.002 * max(0, threat_level - 3), 0.55, 0.99))
    far = float(np.clip(0.018 + 0.004 * max(0, threat_level - 3) + degradation_penalty * 0.08, 0.005, 0.08))

    # Final V10 display model: three altitude waves and continuous curves.
    centroid_lat, centroid_lon = airport_data["latitude"], airport_data["longitude"]
    angles = rng.uniform(0, 2 * math.pi, size=n_uavs)
    distances_start = rng.uniform(9.0, 12.0, size=n_uavs)
    distances_end = rng.uniform(0.5, 2.0, size=n_uavs)
    curve_strength = rng.uniform(0.3, 0.8, size=n_uavs)
    curve_direction = rng.choice([-1, 1], size=n_uavs)
    speed_variation = rng.uniform(0.8, 1.2, size=n_uavs)

    wave = np.zeros(n_uavs, dtype=int)
    altitudes = np.zeros(n_uavs)
    altitude_bands = ((0.05, 0.15), (0.20, 0.35), (0.40, 0.60))
    for wave_id, indices in enumerate(np.array_split(np.arange(n_uavs), 3), start=1):
        if len(indices):
            low, high = altitude_bands[wave_id - 1]
            wave[indices] = wave_id
            altitudes[indices] = rng.uniform(low, high, size=len(indices))

    traj = np.zeros((n_uavs, n_frames, 3))
    longitude_km_per_degree = 111.32 * math.cos(math.radians(centroid_lat))
    for f in range(n_frames):
        t = f / (n_frames - 1)
        progress = np.clip(t * 1.35 * speed_variation, 0.0, 1.0)
        radius = distances_start * (1 - progress) + distances_end * progress
        angle_offset = curve_direction * curve_strength * (1 - progress) * 0.5
        actual_angles = angles + angle_offset
        traj[:, f, 0] = centroid_lat + (radius / 110.57) * np.cos(actual_angles)
        traj[:, f, 1] = centroid_lon + (radius / longitude_km_per_degree) * np.sin(actual_angles)
        traj[:, f, 2] = altitudes * (1 - progress * 0.2)

    # Intercepts occur only after entering the configured engagement envelope
    # and during the Act portion of the synchronized OODA display.
    act_phase = next(phase for phase in phases if phase["phase"] == "Act")
    act_start_frame = int(math.ceil(act_phase["start"] / ooda_total * (n_frames - 1)))
    act_end_frame = int(math.floor(act_phase["end"] / ooda_total * (n_frames - 1)))
    act_end_frame = max(act_start_frame + 1, min(n_frames - 1, act_end_frame))
    engagement_envelope = next(
        envelope for envelope in airport_data["defense_envelopes"]
        if envelope["id"] == "engagement"
    )
    traj_x = (traj[:, :, 1] - centroid_lon) * longitude_km_per_degree
    traj_y = (traj[:, :, 0] - centroid_lat) * 110.57
    inside_engagement = contains_xy(engagement_envelope, traj_x, traj_y)
    entry_frames = []
    for index in range(n_uavs):
        entries = np.flatnonzero(inside_engagement[index])
        entry_frames.append(int(entries[0]) if len(entries) else n_frames - 1)

    # The animation must not draw an intercept before a target reaches the
    # engagement envelope.  Restrict visual intercepts to targets that are
    # physically eligible during the displayed Act window.
    eligible_indices = np.flatnonzero(np.asarray(entry_frames) <= act_end_frame)
    requested_intercepts = min(n_uavs, max(0, int(round(mean_neutralized))))
    intercept_count = min(requested_intercepts, len(eligible_indices))
    intercepted_indices = rng.choice(
        eligible_indices, size=intercept_count, replace=False
    ) if intercept_count else np.asarray([], dtype=int)
    eng_frames: list[int | None] = [None] * n_uavs
    for index in intercepted_indices:
        earliest = max(act_start_frame, entry_frames[int(index)])
        eng_frames[int(index)] = int(rng.integers(earliest, act_end_frame + 1))

    return {
        "ooda_phases": phases,
        "ooda_total": ooda_total,
        "ooda_p90": float(timing.full_loop_summary["p90_s"]),
        "ooda_under_5s": float(timing.full_loop_summary["probability_under_deadline"]),
        "pk": pk,
        "engagement_pk": engagement_pk,
        "pd": pd,
        "far": far,
        "energy": float(energy),
        "mean_neutralized": float(mean_neutralized),
        "displayed_intercepts": int(intercept_count),
        "mission_required": mission_required,
        "resource_cost": float(resource_cost),
        "resource_package_count": int(resource_package_count),
        "resource_usage_rows": usage_rows,
        "timing_component_rows": timing.component_rows,
        "resource_capacity_rows": resource_capacity_rows(
            selected_effectors,
            degradation_profile=degradation_profile,
            resource_package_count=resource_package_count,
        ) if selected_effectors else [],
        "degradation_profile": degradation_profile,
        "authorization_mode": authorization_mode,
        "ooda_effector": ooda_effector,
        "traj": traj,                         # (n_uavs, n_frames, lat/lon/alt_km)
        "eng_frames": eng_frames,             # None means the UAV is not intercepted
        "envelope_entry_frames": entry_frames,
        "wave": wave.tolist(),
        "centroid": (centroid_lat, centroid_lon),
        "effectors": selected_effectors,
        "n_uavs": n_uavs,
        "n_frames": n_frames,
        "n_model_runs": int(n_model_runs),
        "threat_level": threat_level,
        "seed": seed,
        "act_start_frame": act_start_frame,
        "act_end_frame": act_end_frame,
    }


# ---------------------------------------------------------------------------
# Visualisation helpers
# ---------------------------------------------------------------------------
MAPS_DIR = Path(__file__).resolve().parents[1] / "static" / "maps"
WAVE_COLORS = {1: "#D62728", 2: "#FF7F0E", 3: "#9467BD"}
WAVE_NAMES = {1: "低空突防", 2: "中空协同", 3: "高空侦察"}


@lru_cache(maxsize=8)
def _load_offline_map(airport_id: str) -> tuple[dict, str] | None:
    index_path = MAPS_DIR / "index.json"
    if not index_path.exists():
        return None
    with index_path.open(encoding="utf-8") as handle:
        metadata = json.load(handle)
    map_info = metadata.get("airports", {}).get(airport_id)
    if not map_info:
        return None
    image_path = MAPS_DIR / map_info["file"]
    if not image_path.exists():
        return None
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    image_payload = f"data:image/png;base64,{encoded}"
    return {**map_info, "attribution": metadata.get("attribution", "")}, image_payload


def _stable_asset_position(
    asset_index: int,
    asset_count: int,
    latitude: float,
    longitude: float,
) -> tuple[float, float]:
    """Place labels on a deterministic ring so they remain legible."""
    angle = math.pi / 4 + 2 * math.pi * asset_index / max(1, asset_count)
    radius_km = 2.4 + 0.5 * (asset_index % 2)
    return (
        latitude + (radius_km / 110.57) * math.cos(angle),
        longitude + (radius_km / (111.32 * math.cos(math.radians(latitude)))) * math.sin(angle),
    )


def _phase_for_frame(sim: dict, frame: int) -> dict:
    t = frame / max(1, sim["n_frames"] - 1) * sim["ooda_total"]
    return next((phase for phase in sim["ooda_phases"] if phase["start"] <= t <= phase["end"]), sim["ooda_phases"][-1])


def render_tactical_map(sim: dict, airport: dict, frame: int):
    traj = sim["traj"]
    n_uavs = sim["n_uavs"]
    frame = int(np.clip(frame, 0, sim["n_frames"] - 1))
    engaged_mask = np.array([ef is not None and ef <= frame for ef in sim["eng_frames"]])
    engaged_so_far = int(engaged_mask.sum())
    current_phase = _phase_for_frame(sim, frame)

    fig = go.Figure()

    # Asset locations (around centroid)
    cent_lat, cent_lon = sim["centroid"]
    fig.add_trace(go.Scatter(
        x=[cent_lon], y=[cent_lat], mode="markers+text",
        text=[f"{airport['id']}/{airport['icao']}"], textposition="bottom center",
        marker=dict(size=18, color="#111827", symbol="star"),
        name=f"机场中心 {airport['id']}", showlegend=False,
    ))
    for asset_index, asset in enumerate(airport["assets"]):
        asset_lat, asset_lon = _stable_asset_position(
            asset_index, len(airport["assets"]), cent_lat, cent_lon
        )
        label_positions = ("top center", "middle right", "bottom center", "middle left")
        fig.add_trace(go.Scatter(
            x=[asset_lon],
            y=[asset_lat],
            mode="markers+text",
            text=[asset["name"]],
            textposition=label_positions[asset_index % len(label_positions)],
            marker=dict(size=14, color="#1F4E79", symbol="circle"),
            name=f"资产 {asset['name']}",
            hovertext=f"{asset['id']} · {asset['name']} · {asset['criticality']}",
        ))

    # Equipment
    for eq in airport["equipment_deployed"]:
        fig.add_trace(go.Scatter(
            x=[eq["pos"][1]],
            y=[eq["pos"][0]],
            mode="markers",
            marker=dict(size=11, color="#2E7D32", symbol="circle"),
            name=eq["type"],
            text=[eq["type"]],
        ))

    # Drone trajectories up to current frame
    for i in range(n_uavs):
        xs = traj[i, :frame + 1, 1].tolist()
        ys = traj[i, :frame + 1, 0].tolist()
        engaged = engaged_mask[i]
        wave_id = sim["wave"][i]
        path_color = WAVE_COLORS[wave_id]
        marker_color = "#7F7F7F" if engaged else path_color
        hover_text = f"UAV {i+1} · {WAVE_NAMES[wave_id]} · {'已拦截' if engaged else '飞行中'}"
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers",
            line=dict(width=3, color=path_color),
            marker=dict(
                size=[0] * max(0, len(xs) - 1) + [9],
                color=[path_color] * max(0, len(xs) - 1) + [marker_color],
                symbol=["circle"] * max(0, len(xs) - 1) + (["x"] if engaged else ["circle"]),
            ),
            name=f"UAV {i+1}" + (" ⛔" if engaged else " ⚠️"),
            text=[hover_text] * len(ys),
            showlegend=False,
            hoverinfo="text",
        ))

    # Anisotropic, airport-specific defense envelopes (outer first).
    for envelope in reversed(airport["defense_envelopes"]):
        boundary_lat, boundary_lon = envelope_boundary_latlon(
            envelope,
            cent_lat,
            cent_lon,
        )
        fig.add_trace(go.Scatter(
            x=boundary_lon,
            y=boundary_lat,
            mode="lines",
            line=dict(width=2.5, color=envelope["color"]),
            fill="toself",
            fillcolor=hex_to_rgba(envelope["color"], float(envelope["opacity"])),
            name=envelope["name_zh"],
            text=(
                f"{envelope['name_zh']}<br>长/短半轴 "
                f"{envelope['semi_major_km']:.1f}/{envelope['semi_minor_km']:.1f} km"
                f"<br>垂直包络 {envelope['height_km']:.2f} km"
            ),
            hovertemplate="%{text}<extra></extra>",
            showlegend=True,
        ))

    longitude_scale = math.cos(math.radians(cent_lat))
    x_range = [cent_lon - 0.24, cent_lon + 0.24]
    y_range = [cent_lat - 0.12, cent_lat + 0.12]
    layout_images = []
    offline_map = _load_offline_map(airport["id"])
    if offline_map:
        map_info, image_payload = offline_map
        x_range = [map_info["west"], map_info["east"]]
        y_range = [map_info["south"], map_info["north"]]
        layout_images = [dict(
            source=image_payload,
            xref="x",
            yref="y",
            x=map_info["west"],
            y=map_info["north"],
            sizex=map_info["east"] - map_info["west"],
            sizey=map_info["north"] - map_info["south"],
            xanchor="left",
            yanchor="top",
            sizing="stretch",
            opacity=0.88,
            layer="below",
        )]

    fig.update_layout(
        images=layout_images,
        xaxis=dict(range=x_range, visible=False, fixedrange=False),
        yaxis=dict(
            range=y_range,
            visible=False,
            fixedrange=False,
            scaleanchor="x",
            scaleratio=1 / longitude_scale,
            constrain="domain",
        ),
        dragmode="pan",
        hovermode="closest",
        plot_bgcolor="#E8EEF2",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=0, r=0, t=30, b=0),
        height=620,
        title=(f"{airport['name_zh']} ({airport['id']}/{airport['icao']}) · {current_phase['name_zh']}阶段 · "
               f"帧 {frame+1}/{traj.shape[1]} · 已拦截 {engaged_so_far}/{n_uavs}"),
        annotations=[dict(
            x=0.995, y=0.005, xref="paper", yref="paper",
            text="© OpenStreetMap contributors" if offline_map else "离线底图缺失",
            showarrow=False, xanchor="right", yanchor="bottom",
            font=dict(size=10, color="#34495E"),
            bgcolor="rgba(255,255,255,0.72)",
        )],
    )
    return fig


def render_3d_tactical_view(sim: dict, airport: dict, frame: int):
    """Render the same deterministic swarm state in an interactive 3-D view."""
    frame = int(np.clip(frame, 0, sim["n_frames"] - 1))
    cent_lat, cent_lon = sim["centroid"]
    longitude_km_per_degree = 111.32 * math.cos(math.radians(cent_lat))
    current_phase = _phase_for_frame(sim, frame)

    def to_xy(latitude, longitude):
        x = (np.asarray(longitude) - cent_lon) * longitude_km_per_degree
        y = (np.asarray(latitude) - cent_lat) * 110.57
        return x, y

    fig = go.Figure()
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[0.02], mode="markers+text",
        marker=dict(size=8, color="#111827", symbol="diamond"),
        text=[f"{airport['id']}/{airport['icao']}"], textposition="bottom center",
        name=f"机场中心 {airport['id']}", showlegend=False,
    ))
    for wave_id in (1, 2, 3):
        fig.add_trace(go.Scatter3d(
            x=[None], y=[None], z=[None], mode="markers",
            marker=dict(size=7, color=WAVE_COLORS[wave_id]),
            name=f"第{wave_id}波 · {WAVE_NAMES[wave_id]}",
        ))

    # Final-package 3-D concept upgraded from flattened hemispheres/rings to
    # airport-specific rotated half-ellipsoid directional envelopes.
    for envelope in reversed(airport["defense_envelopes"]):
        surface_x, surface_y, surface_z = envelope_surface_xyz(envelope)
        boundary_x, boundary_y = envelope_boundary_xy(envelope)
        color = envelope["color"]
        fig.add_trace(go.Surface(
            x=surface_x,
            y=surface_y,
            z=surface_z,
            surfacecolor=np.zeros_like(surface_z),
            colorscale=[[0.0, color], [1.0, color]],
            cmin=0,
            cmax=1,
            opacity=float(envelope["opacity"]),
            showscale=False,
            hovertemplate=(
                f"{envelope['name_zh']}<br>长/短半轴 "
                f"{envelope['semi_major_km']:.1f}/{envelope['semi_minor_km']:.1f} km"
                f"<br>垂直包络 {envelope['height_km']:.2f} km<extra></extra>"
            ),
            name=envelope["name_zh"],
            showlegend=False,
        ))
        fig.add_trace(go.Scatter3d(
            x=boundary_x,
            y=boundary_y,
            z=np.zeros_like(boundary_x),
            mode="lines",
            line=dict(color=color, width=5),
            name=envelope["name_zh"],
            showlegend=True,
        ))

    for asset_index, asset in enumerate(airport["assets"]):
        asset_lat, asset_lon = _stable_asset_position(
            asset_index, len(airport["assets"]), cent_lat, cent_lon
        )
        x, y = to_xy(asset_lat, asset_lon)
        fig.add_trace(go.Scatter3d(
            x=[float(x)], y=[float(y)], z=[0.02], mode="markers",
            marker=dict(size=7, color="#1F4E79", symbol="diamond"),
            text=[f"{asset['id']} · {asset['name']} · {asset['criticality']}"],
            hoverinfo="text",
            name=f"资产 {asset['name']}", showlegend=False,
        ))

    equipment_lon = [item["pos"][1] for item in airport["equipment_deployed"]]
    equipment_lat = [item["pos"][0] for item in airport["equipment_deployed"]]
    equipment_x, equipment_y = to_xy(equipment_lat, equipment_lon)
    fig.add_trace(go.Scatter3d(
        x=equipment_x, y=equipment_y, z=[0.04] * len(equipment_x), mode="markers",
        marker=dict(size=6, color="#2E7D32", symbol="square"),
        text=[item["type"] for item in airport["equipment_deployed"]],
        hoverinfo="text", name="防御装备",
    ))

    trajectory = sim["traj"]
    for index in range(sim["n_uavs"]):
        path = trajectory[index, :frame + 1]
        path_x, path_y = to_xy(path[:, 0], path[:, 1])
        wave_id = sim["wave"][index]
        intercept_frame = sim["eng_frames"][index]
        engaged = intercept_frame is not None and intercept_frame <= frame
        fig.add_trace(go.Scatter3d(
            x=path_x, y=path_y, z=path[:, 2], mode="lines",
            line=dict(width=3, color=WAVE_COLORS[wave_id]),
            hoverinfo="skip", showlegend=False,
        ))
        fig.add_trace(go.Scatter3d(
            x=[path_x[-1]], y=[path_y[-1]], z=[path[-1, 2]], mode="markers",
            marker=dict(size=5, color="#7F7F7F" if engaged else WAVE_COLORS[wave_id],
                        symbol="x" if engaged else "circle"),
            text=[f"UAV {index+1} · {WAVE_NAMES[wave_id]} · {'已拦截' if engaged else '飞行中'}"],
            hoverinfo="text", showlegend=False,
        ))

    fig.update_layout(
        title=(f"{airport['name_zh']} ({airport['id']}/{airport['icao']}) · 三维攻防态势 · {current_phase['name_zh']}阶段 · "
               f"帧 {frame+1}/{sim['n_frames']}"),
        height=650,
        margin=dict(l=0, r=0, t=45, b=0),
        legend=dict(orientation="h", y=1.02, x=0),
        scene=dict(
            xaxis=dict(title="东西距离 (km)", range=[-13, 13], backgroundcolor="#EAF2F8", gridcolor="#AAB7B8"),
            yaxis=dict(title="南北距离 (km)", range=[-13, 13], backgroundcolor="#EAF2F8", gridcolor="#AAB7B8"),
            zaxis=dict(title="高度 (km，视觉放大)", range=[0, 2.0], backgroundcolor="#F8F9F9", gridcolor="#D5D8DC"),
            aspectmode="manual",
            aspectratio=dict(x=1, y=1, z=0.45),
            camera=dict(eye=dict(x=1.45, y=-1.45, z=0.9)),
        ),
        uirevision=f"{airport['id']}-3d",
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
    engaged = min(n_uavs, max(0, int(round(sim["mean_neutralized"]))))
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
        title=(
            f"🎯 单次期望失效数（使命 Pk={sim['pk']*100:.1f}%）"
        ),
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

    if "selected_airport_id" not in st.session_state:
        st.session_state["selected_airport_id"] = airports_list[0]["id"]
    scen_cols = st.columns([1, 1, 1])
    for i, ap in enumerate(airports_list):
        with scen_cols[i]:
            if st.button(
                f"{ap['name_zh']}\n({ap['id']}/{ap['icao']})",
                key=f"ap_{ap['id']}",
                width="stretch",
                type="primary" if ap["id"] == st.session_state["selected_airport_id"] else "secondary",
            ):
                st.session_state["selected_airport_id"] = ap["id"]

    airport = next(
        (item for item in airports_list if item["id"] == st.session_state["selected_airport_id"]),
        airports_list[0],
    )

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

        degradation_labels = {
            "nominal": "标称资源",
            "sensor_degraded": "传感器退化",
            "contested": "通信/电磁对抗",
            "hpm_offline": "HPM 离线",
        }
        degradation_profile = st.selectbox(
            "链路与资源工况",
            options=list(degradation_labels),
            format_func=degradation_labels.get,
            key="degradation_profile",
        )
        resource_package_count = st.slider(
            "同构资源包数量",
            min_value=1,
            max_value=3,
            value=1,
            step=1,
            key="resource_package_count",
            help=(
                "每增加一包复制效应器并行动作容量，不提高单次作用 Pk；"
                "协调感知口径会加入跨包同步、去冲突和指令编组时延。"
            ),
        )

    with cp2:
        st.markdown("**💥 效应器组合**")
        eff_options = [e["id"] for e in effectors_meta]
        eff_labels = {e["id"]: f"{e['name']}" for e in effectors_meta}
        effectors = st.multiselect(
            "可选效应器（多选）",
            options=eff_options,
            default=["EW", "HPM", "HEL", "Kinetic"],
            format_func=eff_labels.get,
            key="eff_choice",
        )

        authorization_labels = {
            "preauthorized": "预授权规则",
            "batch": "单批次人工授权",
            "per_target": "逐目标人工授权",
        }
        authorization_mode = st.selectbox(
            "授权模式",
            options=list(authorization_labels),
            index=1,
            format_func=authorization_labels.get,
            key="authorization_mode",
        )

        st.markdown("**🎬 演示场景预设**")
        scen_index = st.selectbox(
            "可选预设（默认使用上方自定义参数）",
            options=[None, *range(len(demo_scenarios))],
            format_func=lambda i: "自定义参数" if i is None else demo_scenarios[i]["name"],
            key="scen_pick",
        )

    with cp3:
        st.markdown("**▶ 启动仿真**")
        run_sim = st.button("🚀 启动 OODA 仿真", type="primary", width="stretch")
        st.markdown("**🎞 帧控制**")
        frame_max = int(st.session_state.get("sim_result", {}).get("n_frames", 60)) - 1
        if "anim_frame" not in st.session_state or st.session_state["anim_frame"] > frame_max:
            st.session_state["anim_frame"] = 0
        st.session_state["frame"] = st.slider(
            f"动画帧 (0-{frame_max})", 0, frame_max, key="anim_frame",
        )

        def reset_animation() -> None:
            st.session_state["anim_frame"] = 0
            st.session_state["frame"] = 0

        st.button("🔄 重置动画", width="stretch", on_click=reset_animation)

    if scen_index is not None and demo_scenarios:
        # apply preset
        preset = demo_scenarios[scen_index]
        n_uavs = preset["uav_count"]
        st.session_state["selected_airport_id"] = preset["airport"]
        airport = next((a for a in airports_list if a["id"] == preset["airport"]), airport)
        st.info(
            f"🎯 当前演示场景：{preset['name']} — "
            f"{preset['uav_type']} @ {preset['speed_mps']} m/s · "
            "下方数值由当前全链路与资源容量模型即时重算。"
        )

    # ------------------------------------------------------------------
    # Run sim button OR auto-run when defaults load
    # ------------------------------------------------------------------
    sim_signature = (
        airport["id"],
        int(n_uavs),
        int(threat_level),
        tuple(sorted(effectors)),
        degradation_profile,
        authorization_mode,
        int(resource_package_count),
    )
    if (
        "sim_result" not in st.session_state
        or run_sim
        or st.session_state.get("sim_signature") != sim_signature
    ):
        with st.spinner("正在运行 OODA 仿真..."):
            sim = simulate(
                n_uavs=n_uavs,
                threat_level=threat_level,
                effectors=effectors,
                airport_data=airport,
                degradation_profile=degradation_profile,
                authorization_mode=authorization_mode,
                resource_package_count=resource_package_count,
            )
            st.session_state["sim_result"] = sim
            st.session_state["sim_signature"] = sim_signature

    sim = st.session_state["sim_result"]

    # ------------------------------------------------------------------
    # Results row
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📊 仿真结果")

    r1, r2, r3, r4, r5, r6 = st.columns(6)
    r1.metric("完整 OODA 均值", f"{sim['ooda_total']:.2f} s", f"P90 {sim['ooda_p90']:.2f} s")
    r2.metric("闭环使命 Pk", f"{sim['pk']*100:.1f}%", "内部门槛 75%")
    r3.metric(
        "平均失效目标",
        f"{sim['mean_neutralized']:.1f}/{sim['n_uavs']}",
        f"使命至少 {sim['mission_required']} 架",
    )
    r4.metric("P(完整闭环<5s)", f"{sim['ooda_under_5s']*100:.1f}%")
    r5.metric("同构资源包", f"{sim['resource_package_count']} 包", "并行容量")
    r6.metric("平均行动成本", f"{sim['resource_cost']:.2f}", "合成单位")
    st.caption(
        f"辅助合成指标：Pd={sim['pd']:.1%}，FAR={sim['far']:.2%}；"
        f"工况={sim['degradation_profile']}，授权={sim['authorization_mode']}，"
        f"资源包={sim['resource_package_count']}，交互蒙特卡洛 {sim['n_model_runs']:,} 次；"
        "20 机单包正式值来自 20,000 次主实验，20–100 机扩容网格来自每格 3,000 次实验；"
        "多包结果采用协调感知时延，全部结果非现场测试。"
    )

    # ------------------------------------------------------------------
    # Visualisations
    # ------------------------------------------------------------------
    view_2d, view_3d = st.tabs(["🗺 二维战术地图", "🌐 三维攻防态势"])
    with view_2d:
        map_fig = render_tactical_map(sim, airport, st.session_state["frame"])
        st.plotly_chart(map_fig, width="stretch")
        if _load_offline_map(airport["id"]):
            st.caption("离线底图已随项目打包，可在无网络环境展示。底图 © OpenStreetMap contributors。")
        else:
            st.caption("未找到离线底图，当前回退到在线 OpenStreetMap。")
    with view_3d:
        st.plotly_chart(
            render_3d_tactical_view(sim, airport, st.session_state["frame"]),
            width="stretch",
        )
        st.caption("二维与三维使用同一仿真状态、同一随机种子、同一拦截事件和同一组三维防御包络；可拖动旋转、滚轮缩放。")

    # Animation control hint
    st.info(
        "💡 **操作提示**：拖动 `动画帧` 滑块可视化不同时间点的态势，"
        "三波次采用固定连续曲线；已拦截无人机变为灰色。彩色边界/曲面是按机场方向、"
        "长短轴、垂直高度和方向偏置共同构成机场专属的各向异性防御包络。"
    )

    # Two side-by-side charts
    cw1, cw2 = st.columns(2)
    with cw1:
        st.markdown("### ⏱ OODA 闭环时延瀑布")
        st.plotly_chart(render_ooda_waterfall(sim), width="stretch")
    with cw2:
        st.markdown("### 🎯 处置效果饼图")
        st.plotly_chart(render_pd_pie(sim), width="stretch")

    with st.expander("🔎 查询 OODA 全链路分量参数", expanded=False):
        timing_rows = pd.DataFrame(sim["timing_component_rows"])
        timing_columns = [
            "phase", "name_zh", "scaled_low_s", "scaled_mode_s",
            "scaled_high_s", "occurrence_probability", "notes",
        ]
        for column in timing_columns:
            if column not in timing_rows:
                timing_rows[column] = 1.0 if column == "occurrence_probability" else ""
        timing_rows["occurrence_probability"] = (
            pd.to_numeric(timing_rows["occurrence_probability"], errors="coerce")
            .fillna(1.0)
        )
        st.dataframe(
            timing_rows[timing_columns],
            width="stretch",
            hide_index=True,
            column_config={
                "scaled_low_s": st.column_config.NumberColumn("low (s)", format="%.3f"),
                "scaled_mode_s": st.column_config.NumberColumn("mode (s)", format="%.3f"),
                "scaled_high_s": st.column_config.NumberColumn("high (s)", format="%.3f"),
                "occurrence_probability": st.column_config.NumberColumn("触发概率", format="%.3f"),
            },
        )

    with st.expander("🔎 查询蜂群资源容量与本次平均用量", expanded=False):
        capacity_rows = pd.DataFrame(sim["resource_capacity_rows"])
        usage_rows = pd.DataFrame(sim["resource_usage_rows"])
        if capacity_rows.empty:
            st.info("未选择效应器，因此没有可分配资源。")
        else:
            st.markdown("**容量上限**")
            st.dataframe(capacity_rows, width="stretch", hide_index=True)
            st.markdown("**动态反馈策略平均用量**")
            st.dataframe(usage_rows, width="stretch", hide_index=True)

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
                name="单次作用基础 Pk",
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
                yaxis=dict(title="单次作用基础 Pk", range=[0, 1]),
                yaxis2=dict(title="射程 (归一化)", overlaying="y", side="right", range=[0, 1]),
                height=380,
                plot_bgcolor="#F8F9FB",
                legend=dict(x=0.55, y=1.0),
            )
            st.plotly_chart(fig_eff, width="stretch")

    # ------------------------------------------------------------------
    # Kill web — which OT chain is being exercised in this scenario
    # ------------------------------------------------------------------
    st.markdown("### 🧬 本体驱动的闭环处置链（本场景触发的 OT 序列）")
    chain_text = (
        "Scenario → Threat → Threat_targets_Asset → Asset → Mission →"
        " Mission_requires_Capability → Capability → Equipment → Operator"
    )
    st.code(chain_text, language="text")
    st.markdown(
        f"""
        - **场景**: {airport['name_zh']} ({airport['id']}/{airport['icao']})
        - **威胁等级**: **{threat_level} / 5**
        - **目标资产**: {', '.join(a['name'] for a in airport['assets'][:3])}
        - **响应效应器**: {', '.join(effectors) if effectors else '(无)'}
        - **同构资源包**: **{sim['resource_package_count']} 包**（只复制并行动作容量）
        - **完整 OODA 闭环均值 / P90**: **{sim['ooda_total']:.2f}s / {sim['ooda_p90']:.2f}s**
        - **闭环使命 Pk**: **{sim['pk']:.1%}**（至少失效 {sim['mission_required']} / {sim['n_uavs']} 架且完整闭环小于 5 s）
        - **资源约束**: 按效应器并发通道、作用窗口、弹药/脉冲库存和平均行动成本显式裁决；资源包数不是采购报价
        - **可视化事件**: {sim['displayed_intercepts']} 架在进入交战包络后、Act 窗口内显示处置事件
        - **结果性质**: 固定种子蒙特卡洛仿真结果，非现场实测
        """
    )

    st.markdown("---")
    st.caption("页 5 · Airport Counter-UAS · Plotly Tactical Map")


if __name__ == "__main__":
    show()
