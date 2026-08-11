"""Run non-interactive acceptance checks for every canonical Streamlit page."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from streamlit.testing.v1 import AppTest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PACKAGE_ROOT / "03_源码" / "streamlit_app"
VALIDATION_DIR = PACKAGE_ROOT / "05_Notebook与数据" / "验证输出"
OUTPUT_PATH = VALIDATION_DIR / "streamlit_acceptance.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_app_test(path: Path) -> dict:
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
    app = AppTest.from_file(str(path), default_timeout=90)
    app.run(timeout=90)
    exceptions = [str(item.value) for item in app.exception]
    return {
        "file": str(path.relative_to(APP_DIR)),
        "syntax": "passed",
        "exceptions": exceptions,
        "titles": len(app.title),
        "headers": len(app.header),
        "subheaders": len(app.subheader),
        "metrics": len(app.metric),
        "buttons": len(app.button),
        "sliders": len(app.slider),
        "selectboxes": len(app.selectbox),
        "plotly_charts": len(app.get("plotly_chart")),
        "status": "passed" if not exceptions else "failed",
    }


def validate_airport_resource_control() -> dict:
    path = APP_DIR / "pages" / "5_🗺_机场反无.py"
    app = AppTest.from_file(str(path), default_timeout=90)
    app.run(timeout=90)
    app.slider(key="n_uavs").set_value(50)
    app.slider(key="resource_package_count").set_value(3)
    app.run(timeout=90)
    exceptions = [str(item.value) for item in app.exception]
    metrics = {item.label: item.value for item in app.metric}
    from utils.swarm_adjudication import evaluate_closed_loop_swarm

    expected_result = evaluate_closed_loop_swarm(
        threat_count=50,
        policy="adaptive",
        degradation_profile="nominal",
        resource_package_count=3,
        authorization_mode="batch",
        coordination_mode="coordination_aware",
        n_runs=3_000,
        seed=20260812,
    )
    expected = {
        "闭环使命 Pk": f"{expected_result.closed_loop_mission_probability * 100:.1f}%",
        "平均失效目标": f"{expected_result.swarm.mean_neutralized:.1f}/50",
        "同构资源包": "3 包",
        "平均行动成本": f"{expected_result.swarm.mean_resource_cost:.2f}",
    }
    if expected_result.closed_loop_mission_probability < 0.75:
        raise ValueError(
            "50-threat/3-package coordination-aware model fell below 0.75: "
            f"{expected_result.closed_loop_mission_probability}"
        )
    if exceptions or any(metrics.get(key) != value for key, value in expected.items()):
        raise ValueError(
            f"50-threat/3-package interaction failed: exceptions={exceptions}, "
            f"metrics={metrics}"
        )
    return {
        "threat_count": 50,
        "resource_package_count": 3,
        "metrics": {key: metrics[key] for key in expected},
        "exceptions": exceptions,
        "status": "passed",
    }


def validate_airport_assets() -> dict:
    data_path = APP_DIR / "data" / "airports.json"
    map_index_path = APP_DIR / "static" / "maps" / "index.json"
    airport_data = json.loads(data_path.read_text(encoding="utf-8"))
    map_index = json.loads(map_index_path.read_text(encoding="utf-8"))
    airport_ids = [item["id"] for item in airport_data["airports"]]
    if len(airport_ids) != len(set(airport_ids)):
        raise ValueError("airports.json contains duplicate airport ids")
    daxing = next((item for item in airport_data["airports"] if item["id"] == "PKX"), None)
    if daxing is None or daxing["icao"] != "ZBAD" or "大兴" not in daxing["name_zh"]:
        raise ValueError("Beijing Daxing must use PKX/ZBAD")
    if "PEK" in airport_ids or "PEK" in map_index.get("airports", {}):
        raise ValueError("legacy PEK identifier remains in canonical airport data")
    missing_maps = []
    for airport_id in airport_ids:
        entry = map_index.get("airports", {}).get(airport_id)
        if entry is None or not (APP_DIR / "static" / "maps" / entry["file"]).is_file():
            missing_maps.append(airport_id)
    if missing_maps:
        raise FileNotFoundError(f"missing offline maps: {missing_maps}")
    from utils.defense_envelope import validate_envelopes

    envelope_counts = {}
    for airport in airport_data["airports"]:
        validate_envelopes(airport["defense_envelopes"])
        if any(
            item["semi_major_km"] == item["semi_minor_km"]
            for item in airport["defense_envelopes"]
        ):
            raise ValueError(f"{airport['id']} contains a circular defense layer")
        envelope_counts[airport["id"]] = len(airport["defense_envelopes"])
    return {
        "airport_ids": airport_ids,
        "daxing_codes": {"iata": daxing["id"], "icao": daxing["icao"]},
        "offline_maps_present": True,
        "legacy_pek_absent": True,
        "non_circular_defense_envelopes": envelope_counts,
    }


def validate_trajectory_and_rendering() -> dict:
    """Prove deterministic continuous trajectories and shared 2-D/3-D state."""
    page_path = APP_DIR / "pages" / "5_🗺_机场反无.py"
    spec = importlib.util.spec_from_file_location("cuas_airport_kernel", page_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load airport page kernel: {page_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    airport_data = json.loads(
        (APP_DIR / "data" / "airports.json").read_text(encoding="utf-8")
    )
    airport = next(item for item in airport_data["airports"] if item["id"] == "PKX")
    kwargs = {
        "n_uavs": 20,
        "threat_level": 5,
        "effectors": ["EW", "HPM", "HEL", "Kinetic"],
        "airport_data": airport,
        "n_model_runs": 250,
        "seed": 20260812,
        "n_frames": 60,
    }
    first = module.simulate(**kwargs)
    second = module.simulate(**kwargs)
    third = module.simulate(**{**kwargs, "seed": 20260813})
    trajectory = np.asarray(first["traj"], dtype=float)
    if (
        trajectory.shape != (20, 60, 3)
        or not np.array_equal(trajectory, np.asarray(second["traj"]))
        or np.array_equal(trajectory, np.asarray(third["traj"]))
        or not np.isfinite(trajectory).all()
        or set(first["wave"]) != {1, 2, 3}
    ):
        raise ValueError("trajectory seed, shape, finiteness, or wave partition failed")

    centroid_lat, centroid_lon = first["centroid"]
    lon_scale = 111.32 * math.cos(math.radians(centroid_lat))
    x_km = (trajectory[:, :, 1] - centroid_lon) * lon_scale
    y_km = (trajectory[:, :, 0] - centroid_lat) * 110.57
    z_km = trajectory[:, :, 2]
    step_km = np.sqrt(
        np.diff(x_km, axis=1) ** 2
        + np.diff(y_km, axis=1) ** 2
        + np.diff(z_km, axis=1) ** 2
    )
    radial_km = np.sqrt(x_km**2 + y_km**2)
    max_step_km = float(step_km.max())
    max_outward_step_km = float(np.diff(radial_km, axis=1).max())
    if max_step_km > 0.5 or max_outward_step_km > 1e-9:
        raise ValueError(
            f"trajectory discontinuity: max_step={max_step_km}, "
            f"max_outward_step={max_outward_step_km}"
        )

    for index, intercept_frame in enumerate(first["eng_frames"]):
        if intercept_frame is None:
            continue
        if not (
            first["envelope_entry_frames"][index]
            <= intercept_frame
            <= first["act_end_frame"]
            and intercept_frame >= first["act_start_frame"]
        ):
            raise ValueError(f"UAV {index + 1} intercepted outside envelope/Act window")

    frame = 30
    figure_2d = module.render_tactical_map(first, airport, frame)
    figure_3d = module.render_3d_tactical_view(first, airport, frame)
    if len(figure_2d.layout.images) != 1:
        raise ValueError("PKX 2-D view did not embed its offline map")
    envelope_names = {item["name_zh"] for item in airport["defense_envelopes"]}
    envelope_2d_count = sum(trace.name in envelope_names for trace in figure_2d.data)
    envelope_3d_surface_count = sum(trace.type == "surface" for trace in figure_3d.data)
    if envelope_2d_count != 3 or envelope_3d_surface_count != 3:
        raise ValueError("2-D/3-D defense envelope rendering is incomplete")

    traces_2d = {
        index: next(
            trace
            for trace in figure_2d.data
            if str(getattr(trace, "name", "")).startswith(f"UAV {index + 1}")
        )
        for index in range(20)
    }
    marker_traces_3d = [
        trace
        for trace in figure_3d.data
        if getattr(trace, "text", None)
        and str(trace.text[0]).startswith("UAV ")
    ]
    if len(marker_traces_3d) != 20:
        raise ValueError(f"expected 20 3-D UAV markers, got {len(marker_traces_3d)}")
    markers_3d = {
        int(str(trace.text[0]).split()[1]) - 1: trace for trace in marker_traces_3d
    }
    for index in range(20):
        trace_2d = traces_2d[index]
        trace_3d = markers_3d[index]
        expected_x = float(x_km[index, frame])
        expected_y = float(y_km[index, frame])
        expected_z = float(z_km[index, frame])
        if not (
            math.isclose(float(trace_2d.x[-1]), float(trajectory[index, frame, 1]), abs_tol=1e-12)
            and math.isclose(float(trace_2d.y[-1]), float(trajectory[index, frame, 0]), abs_tol=1e-12)
            and math.isclose(float(trace_3d.x[-1]), expected_x, abs_tol=1e-12)
            and math.isclose(float(trace_3d.y[-1]), expected_y, abs_tol=1e-12)
            and math.isclose(float(trace_3d.z[-1]), expected_z, abs_tol=1e-12)
        ):
            raise ValueError(f"2-D/3-D state mismatch for UAV {index + 1}")

    return {
        "status": "passed",
        "airport": "PKX/ZBAD",
        "threat_count": 20,
        "frames": 60,
        "deterministic_same_seed": True,
        "different_seed_changes_trajectory": True,
        "three_altitude_waves": True,
        "max_frame_step_km": max_step_km,
        "max_outward_frame_step_km": max_outward_step_km,
        "intercepts_after_envelope_entry_and_in_act": True,
        "offline_map_embedded": True,
        "defense_envelopes_2d": envelope_2d_count,
        "defense_envelopes_3d": envelope_3d_surface_count,
        "shared_2d_3d_uav_states": 20,
    }


def validate_ontology_assets() -> dict:
    from rdflib import Graph, Namespace, RDF, OWL
    from utils.sparql_runner import list_templates, template_dataframe

    browser_path = APP_DIR / "data" / "ontology.json"
    browser = json.loads(browser_path.read_text(encoding="utf-8"))
    expected_links = [
        "governs", "allocates", "measuredBy", "implements", "covers",
        "produces", "protects", "confronts", "validates", "operates",
    ]
    if len(browser["object_types"]) != 8:
        raise ValueError("ontology.json must contain exactly 8 Object Types")
    if [item["name"] for item in browser["link_types"]] != expected_links:
        raise ValueError("ontology.json Link Types do not match the manuscript/TBox")
    actual_instances = sum(
        len(item.get("sample_instances", [])) for item in browser["object_types"]
    )
    actual_edges = len(browser["edge_instances"])
    if actual_instances != browser["summary_stats"]["total_object_instances"]:
        raise ValueError("ontology.json instance summary is stale")
    if actual_edges != browser["summary_stats"]["total_edge_instances"]:
        raise ValueError("ontology.json edge summary is stale")

    model_dir = PACKAGE_ROOT / "03_源码" / "本体模型"
    graph = Graph()
    graph.parse(model_dir / "cuas-ontology.ttl", format="turtle")
    graph.parse(model_dir / "cuas-data-valid.ttl", format="turtle")
    cuas = Namespace("http://cuas-ontology.org/cuas#")
    if len(graph) != 463:
        raise ValueError(f"canonical TBox+ABox triple count changed: {len(graph)}")
    missing_links = [
        name for name in expected_links
        if (cuas[name], RDF.type, OWL.ObjectProperty) not in graph
    ]
    if missing_links:
        raise ValueError(f"canonical TBox missing Link Types: {missing_links}")

    template_rows = {
        template["key"]: len(template_dataframe(template["key"]))
        for template in list_templates()
    }
    if not all(count > 0 for count in template_rows.values()):
        raise ValueError(f"one or more SPARQL templates returned no rows: {template_rows}")
    return {
        "object_types": 8,
        "link_types": 10,
        "positive_abox_instances": actual_instances,
        "positive_abox_edges": actual_edges,
        "canonical_graph_triples": len(graph),
        "sparql_template_rows": template_rows,
    }


def validate_action_feedback() -> dict:
    """Exercise the manuscript Effect->Action->Mission write-back prototype."""
    from rdflib import Graph, Literal, Namespace, XSD
    from utils.ontology_action_engine import (
        action_result_to_turtle,
        evaluate_action_feedback,
        load_baseline_operational_state,
    )

    model_dir = PACKAGE_ROOT / "03_源码" / "本体模型"
    canonical_paths = [
        model_dir / "cuas-ontology.ttl",
        model_dir / "cuas-data-valid.ttl",
    ]
    before_hashes = {path.name: sha256(path) for path in canonical_paths}
    state = load_baseline_operational_state()
    state["priority"] = 3
    caller_state_snapshot = copy.deepcopy(state)
    metrics = {
        "detection_coverage": 0.88,
        "identification_accuracy": 0.83,
        "ooda_closure_time_s": 5.4,
        "interception_success_rate": 0.82,
        "false_alarm_rate": 0.025,
    }
    context = {
        "threat_level_previous": 3,
        "threat_level_current": 5,
        "failed_equipment_ids": ["Eq_EW_HPM_001"],
    }
    generated_at = "2026-08-10T00:00:00+00:00"
    first = evaluate_action_feedback(
        metrics, context, state, generated_at_utc=generated_at
    )
    second = evaluate_action_feedback(
        metrics, context, state, generated_at_utc=generated_at
    )
    if first != second or state != caller_state_snapshot:
        raise ValueError("Action decision is not deterministic or mutated caller state")

    expected_auto = 5
    expected_pending = 3
    summary = first["summary"]
    after = first["after_state"]
    expected_pending_actions = {
        "AUTHORIZE_RESOURCE_REALLOCATION",
        "AUTHORIZE_BATCH_DECISION_MODE",
        "AUTHORIZE_EFFECTOR_REINFORCEMENT",
    }
    if (
        first.get("canonical_model_mutated") is not False
        or first.get("not_palantir_foundry_deployment") is not True
        or summary != {
            "triggered_rules": 8,
            "auto_applied": expected_auto,
            "pending_human_authorization": expected_pending,
        }
        or after["priority"] != 5
        or after["equipment_status"]["Eq_EW_HPM_001"] != "Failed"
        or after["controls"]["scan_mode"] != "HIGH_REFRESH"
        or after["controls"]["fusion_model"] != "multi_sensor_high_confidence_v2"
        or after["controls"]["fusion_confirmation"] != "TWO_SOURCE_CONFIRMATION"
        or after["controls"]["wta_recompute_requested"] is not True
        or set(after["pending_human_actions"]) != expected_pending_actions
        or len({item["action_id"] for item in first["actions"]}) != 8
    ):
        raise ValueError(f"Action feedback state transition is invalid: {first}")

    turtle = action_result_to_turtle(first)
    action_graph = Graph().parse(data=turtle, format="turtle")
    cuas = Namespace("http://cuas-ontology.org/cuas#")
    if (
        len(action_graph) < 50
        or (
            cuas[first["after_state"]["mission_id"]],
            cuas.priority,
            Literal(5, datatype=XSD.integer),
        )
        not in action_graph
    ):
        raise ValueError("Action RDF write-back preview is incomplete")
    after_hashes = {path.name: sha256(path) for path in canonical_paths}
    if before_hashes != after_hashes:
        raise ValueError("Action feedback mutated a canonical ontology file")
    return {
        "decision_id": first["decision_id"],
        "triggered_rules": summary["triggered_rules"],
        "auto_applied": summary["auto_applied"],
        "pending_human_authorization": summary["pending_human_authorization"],
        "rdf_triples": len(action_graph),
        "deterministic": True,
        "caller_state_immutable": True,
        "canonical_model_unchanged": True,
        "not_palantir_foundry_deployment": True,
        "status": "passed",
    }


def validate_metric_snapshot() -> dict:
    path = APP_DIR / "data" / "current_metrics.json"
    metrics = json.loads(path.read_text(encoding="utf-8"))
    if metrics.get("schema_version") != 2 or metrics.get("not_field_test") is not True:
        raise ValueError("current_metrics.json is not audited schema 2")
    if metrics["ontology"]["verdict"] != "PASS":
        raise ValueError("formal ontology verdict is not PASS")
    adaptive = float(metrics["ooda"]["swarm_20"]["closed_loop_pk"])
    static = float(metrics["ooda"]["swarm_20"]["static_closed_loop_pk"])
    if adaptive < 0.75 or not adaptive > static:
        raise ValueError("20-swarm metric snapshot is stale or inconsistent")
    if metrics["ooda"]["capacity_frontier_n_at_pk_0_75"] != 20:
        raise ValueError("capacity frontier snapshot is stale")
    scaling = metrics["ooda"].get("resource_scaling", {})
    minimum_rows = scaling.get("minimum_packages", [])
    adaptive_packages = {
        int(item["threat_count"]): item["adaptive_minimum_resource_packages"]
        for item in minimum_rows
    }
    static_packages = {
        int(item["threat_count"]): item["static_minimum_resource_packages"]
        for item in minimum_rows
    }
    expected_threats = {20, 25, 30, 40, 50, 60, 75, 100}
    if set(adaptive_packages) != expected_threats:
        raise ValueError(f"resource scaling threat grid is stale: {adaptive_packages}")
    if any(value is None or not 1 <= int(value) <= 6 for value in adaptive_packages.values()):
        raise ValueError(f"adaptive scaling does not restore all threats within six packages: {adaptive_packages}")
    if set(static_packages) != expected_threats:
        raise ValueError(f"static resource scaling threat grid is stale: {static_packages}")
    if len(scaling.get("grid", [])) != 48:
        raise ValueError("resource scaling grid must contain 8 x 6 = 48 cells")
    if scaling.get("primary_timing_mode") != "coordination_aware":
        raise ValueError("resource scaling primary timing mode is not coordination-aware")
    if scaling.get("upper_bound_timing_mode") != "ideal_parallel":
        raise ValueError("resource scaling upper-bound timing mode is not ideal_parallel")
    if not all(
        float(item["adaptive_pk_at_minimum"]) >= float(scaling["success_threshold"])
        and float(item["same_package_pk_advantage"]) > 0.0
        for item in minimum_rows
    ):
        raise ValueError("resource scaling threshold or same-package advantage is invalid")
    if not metrics["bayesian"]["auc"] > metrics["bayesian"]["fixed_rule_auc"]:
        raise ValueError("Bayesian/fixed-rule AUC snapshot is inconsistent")
    return {
        "ontology_verdict": metrics["ontology"]["verdict"],
        "adaptive_20_pk": adaptive,
        "static_20_pk": static,
        "capacity_frontier_n": metrics["ooda"]["capacity_frontier_n_at_pk_0_75"],
        "adaptive_minimum_resource_packages": adaptive_packages,
        "static_minimum_resource_packages": static_packages,
        "bayesian_auc": metrics["bayesian"]["auc"],
        "fixed_rule_auc": metrics["bayesian"]["fixed_rule_auc"],
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    os.chdir(APP_DIR)
    if str(APP_DIR) not in sys.path:
        sys.path.insert(0, str(APP_DIR))
    targets = [
        APP_DIR / "app.py",
        APP_DIR / "demo_mode.py",
        *sorted((APP_DIR / "pages").glob("*.py")),
    ]
    results = []
    for target in targets:
        print(f"Testing {target.name} ...", flush=True)
        result = run_app_test(target)
        results.append(result)
        print(
            f"  {result['status']}: exceptions={len(result['exceptions'])}, "
            f"plotly={result['plotly_charts']}",
            flush=True,
        )

    trajectory_rendering = validate_trajectory_and_rendering()
    action_feedback = validate_action_feedback()
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "app_dir": str(APP_DIR),
        "pages": results,
        "airport_assets": validate_airport_assets(),
        "airport_resource_control": validate_airport_resource_control(),
        "trajectory_rendering": trajectory_rendering,
        "ontology_assets": validate_ontology_assets(),
        "action_feedback": action_feedback,
        "metric_snapshot": validate_metric_snapshot(),
        "status": "passed"
        if all(item["status"] == "passed" for item in results)
        and trajectory_rendering["status"] == "passed"
        and action_feedback["status"] == "passed"
        else "failed",
    }
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Acceptance report: {OUTPUT_PATH}")
    if payload["status"] != "passed":
        raise RuntimeError("One or more Streamlit pages failed AppTest.")


if __name__ == "__main__":
    main()
