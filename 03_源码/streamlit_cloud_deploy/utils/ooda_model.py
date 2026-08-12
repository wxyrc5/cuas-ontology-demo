"""Configurable end-to-end OODA timing model in seconds.

The parameter file is intentionally data-driven and queryable.  Values are
synthetic engineering assumptions pending field calibration; they are not
measurements of a deployed counter-UAS system.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
from typing import Any

import numpy as np


CONFIG_PATH = Path(__file__).resolve().parents[1] / "data" / "ooda_timing_params.json"
PHASE_ORDER = ("Observe", "Orient", "Decide", "Act", "Feedback")


@dataclass
class OODAResult:
    effector_id: str
    effector_name_zh: str
    threat_count: int
    authorization_mode: str
    degradation_profile: str
    resource_package_count: int
    coordination_mode: str
    n_runs: int
    seed: int
    deadline_s: float
    component_samples: dict[str, np.ndarray]
    component_rows: list[dict[str, Any]]
    phase_samples: dict[str, np.ndarray]
    decision_loop_samples: np.ndarray
    time_to_first_effect_samples: np.ndarray
    full_closed_loop_samples: np.ndarray

    @staticmethod
    def _summary(values: np.ndarray) -> dict[str, float]:
        return {
            "mean_s": float(np.mean(values)),
            "p50_s": float(np.quantile(values, 0.50)),
            "p90_s": float(np.quantile(values, 0.90)),
            "p95_s": float(np.quantile(values, 0.95)),
        }

    @property
    def decision_summary(self) -> dict[str, float]:
        return self._summary(self.decision_loop_samples)

    @property
    def first_effect_summary(self) -> dict[str, float]:
        return self._summary(self.time_to_first_effect_samples)

    @property
    def full_loop_summary(self) -> dict[str, float]:
        summary = self._summary(self.full_closed_loop_samples)
        summary["probability_under_deadline"] = float(
            np.mean(self.full_closed_loop_samples < self.deadline_s)
        )
        return summary

    @property
    def phase_rows(self) -> list[dict[str, float | str]]:
        rows: list[dict[str, float | str]] = []
        for phase in PHASE_ORDER:
            values = self.phase_samples[phase]
            rows.append({"phase": phase, **self._summary(values)})
        return rows


@lru_cache(maxsize=1)
def load_ooda_config() -> dict[str, Any]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if config.get("schema_version") != 2:
        raise ValueError("Unsupported OODA timing schema")
    return config


def _degradation_factor(component: dict[str, Any], profile: dict[str, Any]) -> float:
    group = component.get("degradation_group", "decision")
    key = f"{group}_factor"
    if key not in profile:
        raise KeyError(f"Missing degradation factor {key}")
    return float(profile[key])


def _scaled_component_rows(
    effector_id: str,
    threat_count: int,
    authorization_mode: str,
    degradation_profile: str,
    resource_package_count: int,
    coordination_mode: str,
) -> list[dict[str, Any]]:
    config = load_ooda_config()
    if threat_count < 1:
        raise ValueError("threat_count must be >= 1")
    if (
        isinstance(resource_package_count, bool)
        or resource_package_count < 1
        or int(resource_package_count) != resource_package_count
    ):
        raise ValueError("resource_package_count must be an integer >= 1")
    resource_package_count = int(resource_package_count)
    if effector_id not in config["effector_profiles"]:
        raise KeyError(f"Unknown effector {effector_id}")
    if authorization_mode not in config["authorization_modes"]:
        raise KeyError(f"Unknown authorization mode {authorization_mode}")
    if degradation_profile not in config["degradation_profiles"]:
        raise KeyError(f"Unknown degradation profile {degradation_profile}")
    if coordination_mode not in config["coordination_modes"]:
        raise KeyError(f"Unknown coordination mode {coordination_mode}")

    profile = config["degradation_profiles"][degradation_profile]
    auth = config["authorization_modes"][authorization_mode]
    log_count = float(np.log2(max(threat_count, 1)))
    rows: list[dict[str, Any]] = []

    for raw_component in config["common_components"]:
        component = dict(raw_component)
        count_factor = 1.0 + float(component.get("count_log2_scale", 0.0)) * log_count
        factor = count_factor * _degradation_factor(component, profile)
        if component["id"] == "human_authorization":
            auth_factor = float(auth["base_factor"]) + float(
                auth["per_extra_target_factor"]
            ) * max(0, threat_count - 1)
            factor *= auth_factor
        component["scale_factor"] = factor
        component["scaled_low_s"] = float(component["low_s"]) * factor
        component["scaled_mode_s"] = float(component["mode_s"]) * factor
        component["scaled_high_s"] = float(component["high_s"]) * factor
        rows.append(component)

    effector = config["effector_profiles"][effector_id]
    effect_factor = float(profile["effect_factor"])
    cue = effector["cue_and_aim"]
    delivery = effector["effect_delivery"]
    effector_rows = [
        {
            "id": "cue_and_aim",
            "phase": "Act",
            "name_zh": f"{effector['name_zh']}提示、瞄准与稳定",
            "low_s": cue["low_s"],
            "mode_s": cue["mode_s"],
            "high_s": cue["high_s"],
            "count_log2_scale": 0.0,
            "degradation_group": "effect",
            "notes": "效应器专属提示/瞄准过程",
            "scale_factor": effect_factor,
            "scaled_low_s": float(cue["low_s"]) * effect_factor,
            "scaled_mode_s": float(cue["mode_s"]) * effect_factor,
            "scaled_high_s": float(cue["high_s"]) * effect_factor,
        },
        {
            "id": "effect_delivery",
            "phase": "Act",
            "name_zh": f"{effector['name_zh']}首个效应到达",
            "low_s": delivery["low_s"],
            "mode_s": delivery["mode_s"],
            "high_s": delivery["high_s"],
            "count_log2_scale": 0.0,
            "degradation_group": "effect",
            "notes": effector["delivery_note"],
            "scale_factor": effect_factor,
            "scaled_low_s": float(delivery["low_s"]) * effect_factor,
            "scaled_mode_s": float(delivery["mode_s"]) * effect_factor,
            "scaled_high_s": float(delivery["high_s"]) * effect_factor,
        },
    ]

    # Insert effector-specific steps after command downlink and before BDA.
    bda_index = next(i for i, row in enumerate(rows) if row["id"] == "battle_damage_assessment")
    rows[bda_index:bda_index] = effector_rows

    coordination = config["coordination_modes"][coordination_mode]
    if bool(coordination["enabled"]) and resource_package_count > 1:
        component = dict(coordination["component"])
        reference_count = int(coordination["reference_threat_count"])
        threat_ratio = max(float(threat_count) / reference_count, 1.0)
        threat_factor = 1.0 + float(coordination["threat_ratio_log2_scale"]) * float(
            np.log2(threat_ratio)
        )
        factor = (
            (resource_package_count - 1)
            * threat_factor
            * _degradation_factor(component, profile)
        )
        component["resource_package_count"] = resource_package_count
        component["reference_threat_count"] = reference_count
        component["threat_factor"] = threat_factor
        component["scale_factor"] = factor
        component["scaled_low_s"] = float(component["low_s"]) * factor
        component["scaled_mode_s"] = float(component["mode_s"]) * factor
        component["scaled_high_s"] = float(component["high_s"]) * factor
        # Appending preserves identical random draws for every pre-existing
        # component when ideal and coordination-aware counterfactuals share a seed.
        rows.append(component)
    return rows


def timing_parameter_rows(
    effector_id: str = "HPM",
    threat_count: int = 20,
    authorization_mode: str = "batch",
    degradation_profile: str = "nominal",
    resource_package_count: int = 1,
    coordination_mode: str = "coordination_aware",
) -> list[dict[str, Any]]:
    """Return the queryable, scenario-scaled timing table."""
    return _scaled_component_rows(
        effector_id,
        threat_count,
        authorization_mode,
        degradation_profile,
        resource_package_count,
        coordination_mode,
    )


def simulate_ooda_timing(
    effector_id: str = "HPM",
    threat_count: int = 20,
    authorization_mode: str = "batch",
    degradation_profile: str = "nominal",
    resource_package_count: int = 1,
    coordination_mode: str = "coordination_aware",
    n_runs: int = 20_000,
    seed: int = 20260812,
) -> OODAResult:
    if threat_count < 1:
        raise ValueError("threat_count must be >= 1")
    if n_runs < 100:
        raise ValueError("n_runs must be >= 100")

    config = load_ooda_config()
    rows = _scaled_component_rows(
        effector_id,
        threat_count,
        authorization_mode,
        degradation_profile,
        resource_package_count,
        coordination_mode,
    )
    rng = np.random.default_rng(seed)
    component_samples: dict[str, np.ndarray] = {}
    phase_samples = {phase: np.zeros(n_runs, dtype=float) for phase in PHASE_ORDER}

    for row in rows:
        low = float(row["scaled_low_s"])
        mode = float(row["scaled_mode_s"])
        high = float(row["scaled_high_s"])
        if not (0.0 <= low <= mode <= high):
            raise ValueError(f"Invalid triangular parameters for {row['id']}: {low}, {mode}, {high}")
        samples = (
            np.full(n_runs, low, dtype=float)
            if high == low
            else rng.triangular(low, mode, high, size=n_runs)
        )
        occurrence_probability = float(row.get("occurrence_probability", 1.0))
        if not 0.0 <= occurrence_probability <= 1.0:
            raise ValueError(
                f"Invalid occurrence_probability for {row['id']}: "
                f"{occurrence_probability}"
            )
        if occurrence_probability < 1.0:
            samples *= rng.random(n_runs) < occurrence_probability
        component_samples[row["id"]] = samples
        phase_samples[row["phase"]] += samples

    decision_loop = (
        phase_samples["Observe"]
        + phase_samples["Orient"]
        + phase_samples["Decide"]
    )
    time_to_first_effect = decision_loop + phase_samples["Act"]
    full_closed_loop = time_to_first_effect + phase_samples["Feedback"]

    return OODAResult(
        effector_id=effector_id,
        effector_name_zh=config["effector_profiles"][effector_id]["name_zh"],
        threat_count=threat_count,
        authorization_mode=authorization_mode,
        degradation_profile=degradation_profile,
        resource_package_count=int(resource_package_count),
        coordination_mode=coordination_mode,
        n_runs=n_runs,
        seed=seed,
        deadline_s=float(config["full_loop_deadline_s"]),
        component_samples=component_samples,
        component_rows=rows,
        phase_samples=phase_samples,
        decision_loop_samples=decision_loop,
        time_to_first_effect_samples=time_to_first_effect,
        full_closed_loop_samples=full_closed_loop,
    )


def compare_effectors(
    threat_count: int = 20,
    authorization_mode: str = "batch",
    degradation_profile: str = "nominal",
    resource_package_count: int = 1,
    coordination_mode: str = "coordination_aware",
    n_runs: int = 20_000,
    seed: int = 20260812,
) -> list[dict[str, Any]]:
    config = load_ooda_config()
    rows: list[dict[str, Any]] = []
    for effector_id in config["effector_profiles"]:
        result = simulate_ooda_timing(
            effector_id=effector_id,
            threat_count=threat_count,
            authorization_mode=authorization_mode,
            degradation_profile=degradation_profile,
            resource_package_count=resource_package_count,
            coordination_mode=coordination_mode,
            n_runs=n_runs,
            seed=seed,
        )
        rows.append(
            {
                "effector_id": effector_id,
                "effector_name_zh": result.effector_name_zh,
                "decision_mean_s": result.decision_summary["mean_s"],
                "first_effect_mean_s": result.first_effect_summary["mean_s"],
                "full_loop_mean_s": result.full_loop_summary["mean_s"],
                "full_loop_p90_s": result.full_loop_summary["p90_s"],
                "full_loop_p95_s": result.full_loop_summary["p95_s"],
                "probability_under_5s": result.full_loop_summary[
                    "probability_under_deadline"
                ],
            }
        )
    return rows


__all__ = [
    "CONFIG_PATH",
    "OODAResult",
    "compare_effectors",
    "load_ooda_config",
    "simulate_ooda_timing",
    "timing_parameter_rows",
]
