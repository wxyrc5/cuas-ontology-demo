"""Capacity-constrained layered adjudication for counter-swarm scenarios.

This replaces the legacy threat-count sigmoid, which had no representation of
channels, cycle time, inventory, group capacity or feedback reallocation.
All resource and effectiveness values come from ``swarm_resources.json`` and
are synthetic engineering assumptions pending field calibration.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np


CONFIG_PATH = Path(__file__).resolve().parents[1] / "data" / "swarm_resources.json"
DEFAULT_EFFECTORS = ("EW", "HPM", "HEL", "Kinetic")


@dataclass
class SwarmResult:
    policy: str
    threat_count: int
    resource_package_count: int
    success_fraction_required: float
    neutralizations_required: int
    enabled_effectors: tuple[str, ...]
    degradation_profile: str
    n_runs: int
    seed: int
    mission_success_flags: np.ndarray
    neutralized_counts: np.ndarray
    resource_costs: np.ndarray
    actions_by_effector: dict[str, np.ndarray]
    kills_by_effector: dict[str, np.ndarray]

    @property
    def mission_success_probability(self) -> float:
        return float(np.mean(self.mission_success_flags))

    @property
    def mean_neutralized(self) -> float:
        return float(np.mean(self.neutralized_counts))

    @property
    def mean_neutralized_fraction(self) -> float:
        return float(np.mean(self.neutralized_counts / self.threat_count))

    @property
    def p10_neutralized(self) -> float:
        return float(np.quantile(self.neutralized_counts, 0.10))

    @property
    def mean_resource_cost(self) -> float:
        return float(np.mean(self.resource_costs))

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "policy": self.policy,
            "threat_count": self.threat_count,
            "resource_package_count": self.resource_package_count,
            "neutralizations_required": self.neutralizations_required,
            "mission_success_probability": self.mission_success_probability,
            "mean_neutralized": self.mean_neutralized,
            "mean_neutralized_fraction": self.mean_neutralized_fraction,
            "p10_neutralized": self.p10_neutralized,
            "mean_resource_cost": self.mean_resource_cost,
        }

    @property
    def resource_usage_rows(self) -> list[dict[str, Any]]:
        config = load_swarm_config()
        rows: list[dict[str, Any]] = []
        for effector_id in self.enabled_effectors:
            actions = self.actions_by_effector[effector_id]
            kills = self.kills_by_effector[effector_id]
            rows.append(
                {
                    "effector_id": effector_id,
                    "name_zh": config["effectors"][effector_id]["name_zh"],
                    "mean_actions": float(actions.mean()),
                    "mean_neutralizations": float(kills.mean()),
                    "mean_cost": float(
                        actions.mean()
                        * config["effectors"][effector_id]["cost_per_action"]
                    ),
                }
            )
        return rows


@dataclass
class ClosedLoopSwarmResult:
    swarm: SwarmResult
    ooda_effector_id: str
    ooda_probability_under_deadline: float
    joint_success_flags: np.ndarray

    @property
    def closed_loop_mission_probability(self) -> float:
        return float(np.mean(self.joint_success_flags))


@lru_cache(maxsize=1)
def load_swarm_config() -> dict[str, Any]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if config.get("schema_version") != 2:
        raise ValueError("Unsupported swarm resource schema")
    return config


def legacy_sigmoid_score(
    threat_count: int,
    ontology_coverage: float = 1.0,
    gps_denied: bool = True,
    communications_denied: bool = True,
) -> float:
    """Exact obsolete Notebook-02 equation, retained only as a diagnostic."""
    z = (
        2.5 * ontology_coverage
        - 4.0 * (threat_count / 25.0)
        - 0.5 * int(gps_denied)
        - 0.3 * int(communications_denied)
    )
    return float(1.0 / (1.0 + np.exp(-z)))


def _action_capacity(effector: dict[str, Any], capacity_factor: float) -> int:
    time_cycles = int(
        math.floor(float(effector["allocated_window_s"]) / float(effector["cycle_time_s"]))
    )
    time_actions = int(effector["channels"]) * max(0, time_cycles)
    raw = min(
        time_actions,
        int(effector["max_actions"]),
        int(effector["inventory"]),
    )
    if raw == 0 or capacity_factor <= 0.0:
        return 0
    # Capacity is discrete.  A fractional degradation reduces multi-action
    # resources but must not silently erase the only available area channel.
    return max(1, min(raw, int(round(raw * capacity_factor))))


def resource_capacity_rows(
    enabled_effectors: Iterable[str] = DEFAULT_EFFECTORS,
    degradation_profile: str = "nominal",
    resource_package_count: int = 1,
) -> list[dict[str, Any]]:
    if isinstance(resource_package_count, bool) or resource_package_count < 1:
        raise ValueError("resource_package_count must be an integer >= 1")
    if int(resource_package_count) != resource_package_count:
        raise ValueError("resource_package_count must be an integer >= 1")
    resource_package_count = int(resource_package_count)
    config = load_swarm_config()
    if degradation_profile not in config["degradation_profiles"]:
        raise KeyError(degradation_profile)
    profile = config["degradation_profiles"][degradation_profile]
    disabled = set(profile["disabled_effectors"])
    rows: list[dict[str, Any]] = []
    for effector_id in enabled_effectors:
        if effector_id not in config["effectors"]:
            raise KeyError(effector_id)
        effector = config["effectors"][effector_id]
        actions_per_package = 0 if effector_id in disabled else _action_capacity(
            effector, float(profile["capacity_factor"])
        )
        actions = actions_per_package * resource_package_count
        rows.append(
            {
                "effector_id": effector_id,
                "name_zh": effector["name_zh"],
                "engagement_type": effector["engagement_type"],
                "base_single_target_pk": effector["base_single_target_pk"],
                "channels": effector["channels"],
                "cycle_time_s": effector["cycle_time_s"],
                "allocated_window_s": effector["allocated_window_s"],
                "inventory": effector["inventory"],
                "resource_package_count": resource_package_count,
                "actions_per_package": actions_per_package,
                "available_actions": actions,
                "targets_per_action": effector["targets_per_action"],
                "max_target_engagements": actions * int(effector["targets_per_action"]),
                "cost_per_action": effector["cost_per_action"],
                "disabled": effector_id in disabled,
                "notes": effector["notes"],
            }
        )
    return rows


def _static_plans(
    priority_order: np.ndarray,
    tracked: np.ndarray,
    order: tuple[str, ...],
    effectors: dict[str, Any],
    actions_per_package: dict[str, int],
    resource_package_count: int,
) -> dict[str, list[np.ndarray]]:
    """Freeze a competent coverage-first target table before effects occur.

    Area actions cover their configured priority sector.  Group/precision
    actions are coordinated across effectors so the fixed baseline first gives
    every eligible target one non-area engagement before scheduling repeats.
    It therefore shares the same resources and priority information as the
    adaptive policy without being an intentionally wasteful straw man.  Its
    remaining disadvantage is precisely the absence of post-action feedback:
    later frozen shots can still land on targets neutralized by earlier layers.
    """
    scheduled_non_area: set[int] = set()
    plans: dict[str, list[np.ndarray]] = {effector_id: [] for effector_id in order}
    # Build one complete frozen package plan before adding the next package.
    # Thus package k+1 only appends engagements and can never displace the
    # higher-effectiveness actions already allocated in packages 1..k.
    for _package_index in range(resource_package_count):
        for effector_id in order:
            effector = effectors[effector_id]
            candidates = priority_order
            if bool(effector["requires_precision_track"]):
                candidates = np.asarray(
                    [target for target in priority_order if tracked[target]],
                    dtype=int,
                )
            for _ in range(actions_per_package[effector_id]):
                targets_per_action = int(effector["targets_per_action"])
                if effector["engagement_type"] == "area":
                    selected = np.asarray(candidates[:targets_per_action], dtype=int)
                else:
                    fresh = [
                        int(target) for target in candidates
                        if int(target) not in scheduled_non_area
                    ]
                    repeat = [
                        int(target) for target in candidates
                        if int(target) in scheduled_non_area
                    ]
                    selected = np.asarray((fresh + repeat)[:targets_per_action], dtype=int)
                    scheduled_non_area.update(int(target) for target in selected)
                plans[effector_id].append(selected)
    return plans


def _dynamic_selection(
    priority_order: np.ndarray,
    neutralized: np.ndarray,
    tracked: np.ndarray,
    requires_precision_track: bool,
    targets_per_action: int,
    already_engaged: set[int],
) -> np.ndarray:
    candidates = [
        int(target)
        for target in priority_order
        if not neutralized[target]
        and (not requires_precision_track or tracked[target])
    ]
    fresh = [target for target in candidates if target not in already_engaged]
    retry = [target for target in candidates if target in already_engaged]
    return np.asarray((fresh + retry)[:targets_per_action], dtype=int)


def simulate_swarm_engagement(
    threat_count: int = 20,
    enabled_effectors: Iterable[str] = DEFAULT_EFFECTORS,
    policy: str = "adaptive",
    degradation_profile: str = "nominal",
    resource_package_count: int = 1,
    common_random_package_ceiling: int | None = None,
    n_runs: int = 20_000,
    seed: int = 20260813,
    mission_success_fraction: float | None = None,
) -> SwarmResult:
    """Simulate layered engagements under explicit resource constraints.

    ``adaptive`` reallocates after every layer/action. ``static`` first builds
    a coordinated coverage-first schedule and then freezes it before any
    effect result is known; feedback-induced wasted shots remain possible.
    Both policies use the same priorities, capacities, costs and random draws.
    """
    if threat_count < 1:
        raise ValueError("threat_count must be >= 1")
    if n_runs < 100:
        raise ValueError("n_runs must be >= 100")
    if policy not in {"adaptive", "static"}:
        raise ValueError("policy must be 'adaptive' or 'static'")
    if isinstance(resource_package_count, bool) or resource_package_count < 1:
        raise ValueError("resource_package_count must be an integer >= 1")
    if int(resource_package_count) != resource_package_count:
        raise ValueError("resource_package_count must be an integer >= 1")
    resource_package_count = int(resource_package_count)
    if common_random_package_ceiling is None:
        common_random_package_ceiling = resource_package_count
    if (
        isinstance(common_random_package_ceiling, bool)
        or common_random_package_ceiling < resource_package_count
        or int(common_random_package_ceiling) != common_random_package_ceiling
    ):
        raise ValueError(
            "common_random_package_ceiling must be an integer >= resource_package_count"
        )
    common_random_package_ceiling = int(common_random_package_ceiling)

    config = load_swarm_config()
    if degradation_profile not in config["degradation_profiles"]:
        raise KeyError(degradation_profile)
    profile = config["degradation_profiles"][degradation_profile]
    success_fraction = float(
        config["mission_success_fraction"]
        if mission_success_fraction is None
        else mission_success_fraction
    )
    if not 0.0 < success_fraction <= 1.0:
        raise ValueError("mission_success_fraction must be in (0, 1]")
    required = int(math.ceil(success_fraction * threat_count))

    requested = tuple(dict.fromkeys(enabled_effectors))
    for effector_id in requested:
        if effector_id not in config["effectors"]:
            raise KeyError(effector_id)
    order = tuple(
        effector_id
        for effector_id in config["default_effector_order"]
        if effector_id in requested
    )
    disabled = set(profile["disabled_effectors"])
    capacity_factor = float(profile["capacity_factor"])
    actions_per_package = {
        effector_id: (
            0
            if effector_id in disabled
            else _action_capacity(config["effectors"][effector_id], capacity_factor)
        )
        for effector_id in order
    }
    action_capacities = {
        effector_id: actions_per_package[effector_id] * resource_package_count
        for effector_id in order
    }
    random_action_capacities = {
        effector_id: (
            0
            if effector_id in disabled
            else _action_capacity(config["effectors"][effector_id], capacity_factor)
            * common_random_package_ceiling
        )
        for effector_id in order
    }
    max_action_slots = max(max(random_action_capacities.values(), default=0), 1)

    mission_success_flags = np.zeros(n_runs, dtype=bool)
    neutralized_counts = np.zeros(n_runs, dtype=int)
    resource_costs = np.zeros(n_runs, dtype=float)
    actions_by_effector = {
        effector_id: np.zeros(n_runs, dtype=int) for effector_id in order
    }
    kills_by_effector = {
        effector_id: np.zeros(n_runs, dtype=int) for effector_id in order
    }

    environment = config["environment"]
    rng = np.random.default_rng(seed)
    effector_index = {effector_id: i for i, effector_id in enumerate(order)}

    for run_index in range(n_runs):
        # Fixed-size random tensors make adaptive/static counterfactuals use
        # identical environment, target traits and Bernoulli uniforms.
        common_effectiveness = rng.triangular(
            environment["common_effectiveness_low"],
            environment["common_effectiveness_mode"],
            environment["common_effectiveness_high"],
        )
        target_resilience = rng.triangular(
            environment["target_resilience_low"],
            environment["target_resilience_mode"],
            environment["target_resilience_high"],
            size=(len(order), threat_count),
        )
        tracked = rng.random(threat_count) < float(profile["precision_track_probability"])
        time_to_impact = rng.uniform(25.0, 90.0, size=threat_count)
        priority_order = np.argsort(time_to_impact)
        success_uniforms = rng.random(
            (len(order), max_action_slots, threat_count)
        )

        neutralized = np.zeros(threat_count, dtype=bool)
        static_plans = _static_plans(
            priority_order,
            tracked,
            order,
            config["effectors"],
            actions_per_package,
            resource_package_count,
        )

        for effector_id in order:
            effector = config["effectors"][effector_id]
            action_count = action_capacities[effector_id]
            engaged_by_effector: set[int] = set()
            for action_index in range(action_count):
                if policy == "adaptive":
                    selected = _dynamic_selection(
                        priority_order,
                        neutralized,
                        tracked,
                        bool(effector["requires_precision_track"]),
                        int(effector["targets_per_action"]),
                        engaged_by_effector,
                    )
                    if len(selected) == 0:
                        break
                else:
                    selected = static_plans[effector_id][action_index]

                actions_by_effector[effector_id][run_index] += 1
                resource_costs[run_index] += float(effector["cost_per_action"])
                engaged_by_effector.update(int(target) for target in selected)

                alive_selected = selected[~neutralized[selected]] if len(selected) else selected
                if len(alive_selected) == 0:
                    continue
                e_index = effector_index[effector_id]
                effective_pk = (
                    float(effector["base_single_target_pk"])
                    * float(profile["pk_factor"])
                    * common_effectiveness
                    * target_resilience[e_index, alive_selected]
                )
                effective_pk = np.clip(effective_pk, 0.01, 0.98)
                successes = success_uniforms[
                    e_index,
                    action_index,
                    alive_selected,
                ] < effective_pk
                newly_neutralized = alive_selected[successes]
                neutralized[newly_neutralized] = True
                kills_by_effector[effector_id][run_index] += len(newly_neutralized)

        neutralized_count = int(neutralized.sum())
        neutralized_counts[run_index] = neutralized_count
        mission_success_flags[run_index] = neutralized_count >= required

    return SwarmResult(
        policy=policy,
        threat_count=threat_count,
        resource_package_count=resource_package_count,
        success_fraction_required=success_fraction,
        neutralizations_required=required,
        enabled_effectors=order,
        degradation_profile=degradation_profile,
        n_runs=n_runs,
        seed=seed,
        mission_success_flags=mission_success_flags,
        neutralized_counts=neutralized_counts,
        resource_costs=resource_costs,
        actions_by_effector=actions_by_effector,
        kills_by_effector=kills_by_effector,
    )


def evaluate_closed_loop_swarm(
    threat_count: int = 20,
    enabled_effectors: Iterable[str] = DEFAULT_EFFECTORS,
    policy: str = "adaptive",
    degradation_profile: str = "nominal",
    resource_package_count: int = 1,
    authorization_mode: str = "batch",
    coordination_mode: str = "coordination_aware",
    n_runs: int = 20_000,
    seed: int = 20260813,
    mission_success_fraction: float | None = None,
) -> ClosedLoopSwarmResult:
    from .ooda_model import simulate_ooda_timing

    swarm = simulate_swarm_engagement(
        threat_count=threat_count,
        enabled_effectors=enabled_effectors,
        policy=policy,
        degradation_profile=degradation_profile,
        resource_package_count=resource_package_count,
        n_runs=n_runs,
        seed=seed,
        mission_success_fraction=mission_success_fraction,
    )
    active_effectors = [
        item
        for item in swarm.enabled_effectors
        if np.mean(swarm.actions_by_effector[item]) > 0
    ]
    ooda_effector = "HPM" if "HPM" in active_effectors else (
        active_effectors[0] if active_effectors else "EW"
    )
    ooda_degradation = "contested" if degradation_profile == "contested" else "nominal"
    timing = simulate_ooda_timing(
        effector_id=ooda_effector,
        threat_count=threat_count,
        authorization_mode=authorization_mode,
        degradation_profile=ooda_degradation,
        resource_package_count=resource_package_count,
        coordination_mode=coordination_mode,
        n_runs=n_runs,
        seed=seed + 1,
    )
    timing_success = timing.full_closed_loop_samples < timing.deadline_s
    joint_flags = swarm.mission_success_flags & timing_success
    return ClosedLoopSwarmResult(
        swarm=swarm,
        ooda_effector_id=ooda_effector,
        ooda_probability_under_deadline=float(np.mean(timing_success)),
        joint_success_flags=joint_flags,
    )


def stress_test_20_swarm(
    n_runs: int = 20_000,
    seed: int = 20260813,
) -> list[dict[str, Any]]:
    cases = [
        ("nominal_80pct", "nominal", 0.80, "batch"),
        ("sensor_degraded", "sensor_degraded", 0.80, "batch"),
        ("contested", "contested", 0.80, "batch"),
        ("hpm_offline", "hpm_offline", 0.80, "batch"),
        ("nominal_90pct", "nominal", 0.90, "batch"),
        ("per_target_authorization", "nominal", 0.80, "per_target"),
    ]
    rows: list[dict[str, Any]] = []
    for name, profile, success_fraction, authorization in cases:
        result = evaluate_closed_loop_swarm(
            threat_count=20,
            policy="adaptive",
            degradation_profile=profile,
            authorization_mode=authorization,
            n_runs=n_runs,
            seed=seed,
            mission_success_fraction=success_fraction,
        )
        rows.append(
            {
                "case": name,
                "degradation_profile": profile,
                "authorization_mode": authorization,
                "required_fraction": success_fraction,
                "required_neutralizations": result.swarm.neutralizations_required,
                "engagement_success_probability": result.swarm.mission_success_probability,
                "ooda_under_5s_probability": result.ooda_probability_under_deadline,
                "closed_loop_mission_probability": result.closed_loop_mission_probability,
                "mean_neutralized": result.swarm.mean_neutralized,
                "mean_resource_cost": result.swarm.mean_resource_cost,
            }
        )
    return rows


def _wilson_interval(successes: int, n_runs: int) -> tuple[float, float]:
    """Two-sided 95% Wilson interval without an extra statistics dependency."""
    z = 1.959963984540054
    p = successes / n_runs
    denominator = 1.0 + z * z / n_runs
    center = (p + z * z / (2.0 * n_runs)) / denominator
    half_width = (
        z
        * math.sqrt(p * (1.0 - p) / n_runs + z * z / (4.0 * n_runs * n_runs))
        / denominator
    )
    return center - half_width, center + half_width


def resource_scaling_study(
    n_runs: int = 3_000,
    seed: int = 20260813,
) -> list[dict[str, Any]]:
    """Evaluate configured resource packages with common random numbers.

    The study grid and interpretation live in ``swarm_resources.json``.  All
    package counts share the same environment, target traits, Bernoulli draws
    and OODA timing samples for a given threat count.  Package replication
    does not improve per-action effectiveness or shorten any base OODA
    component.  The primary timing mode adds an explicit coordination penalty;
    the ideal-parallel timing mode is retained only as an upper bound.
    """
    if n_runs < 100:
        raise ValueError("n_runs must be >= 100")
    config = load_swarm_config()
    study = config["resource_scaling_study"]
    package_counts = tuple(int(item) for item in study["package_counts"])
    threat_counts = tuple(int(item) for item in study["threat_counts"])
    if not package_counts or min(package_counts) < 1:
        raise ValueError("resource scaling package counts must be positive")
    common_ceiling = max(package_counts)
    primary_timing_mode = str(study["primary_timing_mode"])
    upper_bound_timing_mode = str(study["upper_bound_timing_mode"])

    from .ooda_model import simulate_ooda_timing

    rows: list[dict[str, Any]] = []
    for threat_count in threat_counts:
        ideal_timing = simulate_ooda_timing(
            effector_id="HPM",
            threat_count=threat_count,
            authorization_mode="batch",
            degradation_profile="nominal",
            resource_package_count=1,
            coordination_mode=upper_bound_timing_mode,
            n_runs=n_runs,
            seed=seed + 1,
        )
        ideal_timing_success = (
            ideal_timing.full_closed_loop_samples < ideal_timing.deadline_s
        )
        for package_count in package_counts:
            coordinated_timing = simulate_ooda_timing(
                effector_id="HPM",
                threat_count=threat_count,
                authorization_mode="batch",
                degradation_profile="nominal",
                resource_package_count=package_count,
                coordination_mode=primary_timing_mode,
                n_runs=n_runs,
                seed=seed + 1,
            )
            coordinated_timing_success = (
                coordinated_timing.full_closed_loop_samples
                < coordinated_timing.deadline_s
            )
            policy_results: dict[str, dict[str, Any]] = {}
            for policy in ("adaptive", "static"):
                swarm = simulate_swarm_engagement(
                    threat_count=threat_count,
                    policy=policy,
                    degradation_profile="nominal",
                    resource_package_count=package_count,
                    common_random_package_ceiling=common_ceiling,
                    n_runs=n_runs,
                    seed=seed,
                )
                coordinated_joint = (
                    swarm.mission_success_flags & coordinated_timing_success
                )
                ideal_joint = swarm.mission_success_flags & ideal_timing_success
                coordinated_successes = int(coordinated_joint.sum())
                ideal_successes = int(ideal_joint.sum())
                coordinated_interval = _wilson_interval(
                    coordinated_successes, n_runs
                )
                ideal_interval = _wilson_interval(ideal_successes, n_runs)
                policy_results[policy] = {
                    "engagement_success_probability": float(
                        swarm.mission_success_probability
                    ),
                    "closed_loop_pk": float(coordinated_joint.mean()),
                    "wilson_ci95_low": float(coordinated_interval[0]),
                    "wilson_ci95_high": float(coordinated_interval[1]),
                    "ideal_parallel_closed_loop_pk": float(ideal_joint.mean()),
                    "ideal_parallel_wilson_ci95_low": float(ideal_interval[0]),
                    "ideal_parallel_wilson_ci95_high": float(ideal_interval[1]),
                    "mean_neutralized": swarm.mean_neutralized,
                    "mean_action_cost": swarm.mean_resource_cost,
                }
            coordination_samples = coordinated_timing.component_samples.get(
                "multi_package_coordination",
                np.zeros(n_runs, dtype=float),
            )
            rows.append(
                {
                    "threat_count": threat_count,
                    "resource_package_count": package_count,
                    "ideal_parallel_ooda_under_deadline_probability": float(
                        ideal_timing_success.mean()
                    ),
                    "coordination_aware_ooda_under_deadline_probability": float(
                        coordinated_timing_success.mean()
                    ),
                    "coordination_delay_mean_s": float(coordination_samples.mean()),
                    "coordination_delay_p90_s": float(
                        np.quantile(coordination_samples, 0.90)
                    ),
                    "adaptive": policy_results["adaptive"],
                    "static": policy_results["static"],
                }
            )
    return rows


__all__ = [
    "ClosedLoopSwarmResult",
    "CONFIG_PATH",
    "DEFAULT_EFFECTORS",
    "SwarmResult",
    "evaluate_closed_loop_swarm",
    "legacy_sigmoid_score",
    "load_swarm_config",
    "resource_capacity_rows",
    "resource_scaling_study",
    "simulate_swarm_engagement",
    "stress_test_20_swarm",
]
