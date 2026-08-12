"""Export a reproducible 20-target synthetic OODA event ledger.

The timestamps are deterministic mode-path outputs from ooda_timing_params.json,
not measured equipment telemetry.  The explicit evidence_scope column prevents
the CSV from being presented as field-test data.
"""
from __future__ import annotations

import csv
from pathlib import Path
import sys

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PACKAGE_ROOT / "03_源码" / "streamlit_app"
OUTPUT_PATH = PACKAGE_ROOT / "05_Notebook与数据" / "验证输出" / "ooda_20drone_latency_detail.csv"
sys.path.insert(0, str(APP_ROOT))

from utils.ooda_model import simulate_ooda_timing  # noqa: E402
from utils.wta_optimizer import demonstration_wta  # noqa: E402


STAGES = [
    ("sensor_revisit_confirmation", "observed_ms"),
    ("track_initiation", "track_stable_ms"),
    ("sensor_data_uplink", "ingress_and_crs_gate_ms"),
    ("multisensor_correlation_id", "fused_ms"),
    ("semantic_threat_assessment", "threat_classified_ms"),
    ("c2_data_transport", "c2_available_ms"),
    ("weapon_target_allocation", "wta_assigned_ms"),
    ("human_authorization", "authorization_decided_ms"),
    ("effector_command_downlink", "command_delivered_ms"),
    ("cue_and_aim", "aim_complete_ms"),
    ("effect_delivery", "effect_arrived_ms"),
    ("battle_damage_assessment", "feedback_recorded_ms"),
]


def build_rows() -> list[dict[str, object]]:
    timing = simulate_ooda_timing(
        effector_id="HPM",
        threat_count=20,
        authorization_mode="batch",
        degradation_profile="nominal",
        resource_package_count=1,
        coordination_mode="coordination_aware",
        n_runs=2_000,
        seed=20260812,
    )
    components = {row["id"]: row for row in timing.component_rows}
    offsets_ms: dict[str, int] = {}
    cursor_s = 0.0
    for component_id, column in STAGES:
        cursor_s += float(components[component_id]["scaled_mode_s"])
        offsets_ms[column] = round(cursor_s * 1000.0)

    assignments = {row["target"]: row for row in demonstration_wta(20)["assignments"]}
    rng = np.random.default_rng(20260812)
    rows: list[dict[str, object]] = []
    for index in range(20):
        target_id = f"Threat_{index + 1:02d}"
        assignment = assignments[target_id]
        start_ms = index * 5
        p_ij = float(assignment["p_ij"])
        row: dict[str, object] = {
            "target_id": target_id,
            "synthetic_trace": True,
            "batch_id": "BATCH-ZX2026-20-001",
            "source_event_id": f"SYN-RADAR-007-{index + 1:03d}",
            "source_crs": "OGC:CRS84",
            "target_crs": "EPSG:32651",
            "ingress_gate_status": "ACCEPT",
            "assigned_effector": assignment["effector"],
            "authorization_level": "L3" if assignment["effector"] in {"HPM", "HEL", "Kinetic"} else "L2",
            "assignment_probability": round(p_ij, 6),
            "simulated_outcome": "SUCCESS" if rng.random() < p_ij else "FAILED",
            "seed": 20260812,
            "time_path": "scaled_mode_without_exception_rework",
            "evidence_scope": "参数化合成毫秒流水账；非实装遥测、非现场测试、非性能承诺",
        }
        row.update({column: start_ms + offset for column, offset in offsets_ms.items()})
        row["full_loop_ms"] = row["feedback_recorded_ms"] - start_ms
        rows.append(row)
    return rows


def main() -> None:
    rows = build_rows()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} synthetic target rows -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
