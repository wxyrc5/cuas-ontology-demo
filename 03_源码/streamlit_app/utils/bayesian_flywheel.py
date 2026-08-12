"""Five-channel Beta-Binomial feedback flywheel and fair fixed-rule baseline.

All numbers are synthetic engineering assumptions.  The module is designed so
the Notebook and Streamlit page execute exactly the same model.

Fair-comparison rule
--------------------
For AUC evaluation, both classifiers receive the same mission cases, the same
five channel observations and the same observation budget.  The Bayesian score
uses Beta posterior compliance probabilities.  The fixed baseline applies
predeclared hard thresholds to the very same empirical channel rates.  No
future observation, unequal sample count or tuned test label is available to
either model.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy.stats import beta as beta_distribution
from scipy.stats import norm
from sklearn.metrics import roc_auc_score, roc_curve
from rdflib import Graph, Namespace


@dataclass(frozen=True)
class ChannelSpec:
    key: str
    label_zh: str
    label_en: str
    true_satisfaction_probability: float
    requirement_probability: float
    weight: float
    source_metric: str


CHANNELS: tuple[ChannelSpec, ...] = (
    ChannelSpec(
        "detection",
        "探测覆盖",
        "Detection Coverage",
        0.972,
        0.950,
        0.24,
        "DetectionCoverage >= 0.95",
    ),
    ChannelSpec(
        "identification",
        "识别准确",
        "Identification Accuracy",
        0.948,
        0.920,
        0.20,
        "IdentificationAccuracy >= 0.92",
    ),
    ChannelSpec(
        "interception",
        "拦截成功",
        "Interception Success",
        0.895,
        0.850,
        0.24,
        "InterceptionSuccessRate >= 0.85",
    ),
    ChannelSpec(
        "ooda_closure",
        "OODA 闭环",
        "OODA Closure",
        0.935,
        0.900,
        0.22,
        "P(full-loop latency < 5 s) >= 0.90",
    ),
    ChannelSpec(
        "false_alarm_compliance",
        "低虚警合规（1-FAR）",
        "False Alarm Compliance (1-FAR)",
        0.986,
        0.980,
        0.10,
        "1 - FalseAlarmRate >= 0.98",
    ),
)

COMPOSITE_THRESHOLD = 0.90
CUAS = Namespace("http://cuas-ontology.org/cuas#")


@dataclass
class FlywheelResult:
    seed: int
    n_observations: int
    prior_alpha: float
    prior_beta: float
    steps: np.ndarray
    observations: dict[str, np.ndarray]
    posterior_alpha: dict[str, np.ndarray]
    posterior_beta: dict[str, np.ndarray]
    posterior_mean: dict[str, np.ndarray]
    credible_low: dict[str, np.ndarray]
    credible_high: dict[str, np.ndarray]
    combined_mean: np.ndarray
    combined_low: np.ndarray
    combined_high: np.ndarray
    first_threshold_crossing: int | None
    sustained_threshold_crossing: int | None

    @property
    def final_composite(self) -> float:
        return float(self.combined_mean[-1])

    @property
    def final_composite_interval(self) -> tuple[float, float]:
        return float(self.combined_low[-1]), float(self.combined_high[-1])


@dataclass
class AUCComparison:
    seed: int
    n_seeds: int
    n_cases_per_seed: int
    observations_per_channel: int
    labels: np.ndarray
    bayesian_scores: np.ndarray
    fixed_rule_scores: np.ndarray
    bayesian_auc: float
    fixed_rule_auc: float
    auc_delta: float
    paired_seed_auc_delta_mean: float
    paired_seed_auc_delta_ci95: tuple[float, float]
    bayesian_roc: dict[str, np.ndarray]
    fixed_rule_roc: dict[str, np.ndarray]
    bayesian_threshold: float
    bayesian_fpr: float
    bayesian_fnr: float
    fixed_rule_threshold: float
    fixed_rule_fpr: float
    fixed_rule_fnr: float


@dataclass
class FlywheelAudit:
    seed: int
    n_runs: int
    n_observations: int
    true_composite: float
    convergence_mean_cycles: float
    convergence_std_cycles: float
    convergence_p95_cycles: float
    non_convergence_rate: float
    final_composite_mean: float
    final_composite_std: float
    credible_interval_coverage_95: float
    posterior_rmse: float


def _normalise_weights(channels: Iterable[ChannelSpec]) -> np.ndarray:
    weights = np.asarray([channel.weight for channel in channels], dtype=float)
    if np.any(weights <= 0):
        raise ValueError("All channel weights must be positive")
    if not np.isclose(weights.sum(), 1.0, atol=1e-12):
        raise ValueError(f"Channel weights must sum to 1.0, got {weights.sum():.12f}")
    return weights


def _first_sustained(values: np.ndarray, threshold: float, window: int) -> int | None:
    flags = np.asarray(values >= threshold, dtype=int)
    if len(flags) < window:
        return None
    run = np.convolve(flags, np.ones(window, dtype=int), mode="valid")
    matches = np.flatnonzero(run == window)
    return int(matches[0] + 1) if len(matches) else None


def simulate_flywheel(
    n_observations: int = 200,
    seed: int = 42,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
    credible_level: float = 0.95,
    composite_draws: int = 4000,
) -> FlywheelResult:
    """Simulate the requested five-channel Beta-Binomial convergence plot."""
    if n_observations < 2:
        raise ValueError("n_observations must be >= 2")
    if prior_alpha <= 0 or prior_beta <= 0:
        raise ValueError("Beta prior parameters must be positive")
    if composite_draws < 200:
        raise ValueError("composite_draws must be >= 200")

    channels = CHANNELS
    weights = _normalise_weights(channels)
    rng = np.random.default_rng(seed)
    steps = np.arange(1, n_observations + 1)
    tail = (1.0 - credible_level) / 2.0

    observations: dict[str, np.ndarray] = {}
    posterior_alpha: dict[str, np.ndarray] = {}
    posterior_beta: dict[str, np.ndarray] = {}
    posterior_mean: dict[str, np.ndarray] = {}
    credible_low: dict[str, np.ndarray] = {}
    credible_high: dict[str, np.ndarray] = {}

    for channel in channels:
        obs = rng.binomial(
            1,
            channel.true_satisfaction_probability,
            size=n_observations,
        ).astype(int)
        successes = np.cumsum(obs)
        alpha = prior_alpha + successes
        beta_value = prior_beta + steps - successes
        observations[channel.key] = obs
        posterior_alpha[channel.key] = alpha
        posterior_beta[channel.key] = beta_value
        posterior_mean[channel.key] = alpha / (alpha + beta_value)
        credible_low[channel.key] = beta_distribution.ppf(tail, alpha, beta_value)
        credible_high[channel.key] = beta_distribution.ppf(
            1.0 - tail,
            alpha,
            beta_value,
        )

    mean_matrix = np.vstack([posterior_mean[channel.key] for channel in channels])
    combined_mean = weights @ mean_matrix

    # Draw the full composite posterior at every step.  A separate RNG keeps
    # observation sequences identical if only the plotting draw count changes.
    posterior_rng = np.random.default_rng(seed + 100_003)
    channel_draws = []
    for channel in channels:
        alpha = posterior_alpha[channel.key][:, None]
        beta_value = posterior_beta[channel.key][:, None]
        channel_draws.append(
            posterior_rng.beta(alpha, beta_value, size=(n_observations, composite_draws))
        )
    draw_cube = np.stack(channel_draws, axis=0)
    combined_draws = np.tensordot(weights, draw_cube, axes=(0, 0))
    combined_low = np.quantile(combined_draws, tail, axis=1)
    combined_high = np.quantile(combined_draws, 1.0 - tail, axis=1)

    crossing_indices = np.flatnonzero(combined_mean >= COMPOSITE_THRESHOLD)
    first_crossing = int(crossing_indices[0] + 1) if len(crossing_indices) else None
    sustained_crossing = _first_sustained(combined_mean, COMPOSITE_THRESHOLD, window=10)

    return FlywheelResult(
        seed=seed,
        n_observations=n_observations,
        prior_alpha=prior_alpha,
        prior_beta=prior_beta,
        steps=steps,
        observations=observations,
        posterior_alpha=posterior_alpha,
        posterior_beta=posterior_beta,
        posterior_mean=posterior_mean,
        credible_low=credible_low,
        credible_high=credible_high,
        combined_mean=combined_mean,
        combined_low=combined_low,
        combined_high=combined_high,
        first_threshold_crossing=first_crossing,
        sustained_threshold_crossing=sustained_crossing,
    )


def flywheel_channel_rows(result: FlywheelResult) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for channel in CHANNELS:
        rows.append(
            {
                "通道": channel.label_zh,
                "指标映射": channel.source_metric,
                "权重": channel.weight,
                "合成真值": channel.true_satisfaction_probability,
                "工程门槛": channel.requirement_probability,
                "成功观测": int(result.observations[channel.key].sum()),
                "总观测": result.n_observations,
                "终态后验均值": float(result.posterior_mean[channel.key][-1]),
                "95%下界": float(result.credible_low[channel.key][-1]),
                "95%上界": float(result.credible_high[channel.key][-1]),
            }
        )
    return rows


def audit_flywheel_reproducibility(
    n_runs: int = 1000,
    n_observations: int = 200,
    seed: int = 20260811,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
) -> FlywheelAudit:
    """Audit convergence and final composite calibration across many seeds.

    The final composite interval uses the exact mean/variance of independent
    Beta posteriors with a normal approximation for their weighted sum.  The
    canonical seed=42 chart still uses Monte Carlo quantiles.
    """
    if n_runs < 20:
        raise ValueError("n_runs must be >= 20")
    if n_observations < 10:
        raise ValueError("n_observations must be >= 10")

    rng = np.random.default_rng(seed)
    weights = _normalise_weights(CHANNELS)
    true_probabilities = np.asarray(
        [channel.true_satisfaction_probability for channel in CHANNELS],
        dtype=float,
    )
    true_composite = float(weights @ true_probabilities)
    steps = np.arange(1, n_observations + 1, dtype=float)

    convergence: list[int] = []
    non_converged = 0
    final_means: list[float] = []
    final_lows: list[float] = []
    final_highs: list[float] = []

    for _ in range(n_runs):
        observations = rng.binomial(
            1,
            true_probabilities[None, :],
            size=(n_observations, len(CHANNELS)),
        )
        cumulative = np.cumsum(observations, axis=0)
        alpha = prior_alpha + cumulative
        beta_value = prior_beta + steps[:, None] - cumulative
        posterior_means = alpha / (alpha + beta_value)
        composite_trace = posterior_means @ weights
        crossing = _first_sustained(composite_trace, COMPOSITE_THRESHOLD, window=10)
        if crossing is None:
            non_converged += 1
            convergence.append(n_observations)
        else:
            convergence.append(crossing)

        final_alpha = alpha[-1]
        final_beta = beta_value[-1]
        final_channel_means = final_alpha / (final_alpha + final_beta)
        final_channel_variances = (
            final_alpha
            * final_beta
            / ((final_alpha + final_beta) ** 2 * (final_alpha + final_beta + 1.0))
        )
        composite_mean = float(weights @ final_channel_means)
        composite_sd = float(np.sqrt(np.sum((weights**2) * final_channel_variances)))
        final_means.append(composite_mean)
        final_lows.append(max(0.0, composite_mean - norm.ppf(0.975) * composite_sd))
        final_highs.append(min(1.0, composite_mean + norm.ppf(0.975) * composite_sd))

    convergence_array = np.asarray(convergence, dtype=float)
    final_means_array = np.asarray(final_means, dtype=float)
    final_lows_array = np.asarray(final_lows, dtype=float)
    final_highs_array = np.asarray(final_highs, dtype=float)
    coverage = np.mean(
        (final_lows_array <= true_composite) & (true_composite <= final_highs_array)
    )
    rmse = np.sqrt(np.mean((final_means_array - true_composite) ** 2))

    return FlywheelAudit(
        seed=seed,
        n_runs=n_runs,
        n_observations=n_observations,
        true_composite=true_composite,
        convergence_mean_cycles=float(convergence_array.mean()),
        convergence_std_cycles=float(convergence_array.std(ddof=0)),
        convergence_p95_cycles=float(np.quantile(convergence_array, 0.95)),
        non_convergence_rate=float(non_converged / n_runs),
        final_composite_mean=float(final_means_array.mean()),
        final_composite_std=float(final_means_array.std(ddof=0)),
        credible_interval_coverage_95=float(coverage),
        posterior_rmse=float(rmse),
    )


def _balanced_error_threshold(
    labels: np.ndarray,
    scores: np.ndarray,
) -> tuple[float, float, float]:
    fpr, tpr, thresholds = roc_curve(labels, scores)
    finite = np.isfinite(thresholds)
    candidates = np.flatnonzero(finite)
    if not len(candidates):
        return 0.5, 1.0, 1.0
    balanced = (fpr[candidates] + (1.0 - tpr[candidates])) / 2.0
    index = int(candidates[np.argmin(balanced)])
    return float(thresholds[index]), float(fpr[index]), float(1.0 - tpr[index])


def _generate_mission_cases(
    rng: np.random.Generator,
    n_cases: int,
    observations_per_channel: int,
    prior_alpha: float,
    prior_beta: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n_channels = len(CHANNELS)
    labels = np.tile(np.array([0, 1], dtype=int), int(np.ceil(n_cases / 2)))[:n_cases]
    rng.shuffle(labels)
    requirements = np.asarray(
        [channel.requirement_probability for channel in CHANNELS],
        dtype=float,
    )
    weights = _normalise_weights(CHANNELS)

    # Positive cases sit above every declared engineering requirement, while
    # negative cases violate one to three randomly selected requirements.
    upper = np.full(n_channels, 0.998)
    positive_fraction = rng.beta(2.2, 1.8, size=(n_cases, n_channels))
    latent = requirements + positive_fraction * (upper - requirements)

    negative_indices = np.flatnonzero(labels == 0)
    max_deficits = np.asarray([0.22, 0.24, 0.30, 0.26, 0.16])
    for case_index in negative_indices:
        deficiency_count = int(rng.choice([1, 2, 3], p=[0.52, 0.36, 0.12]))
        deficient_channels = rng.choice(n_channels, size=deficiency_count, replace=False)
        for channel_index in deficient_channels:
            # Four percentage points is the declared synthetic grey-zone
            # exclusion margin; cases closer to a requirement are labelled
            # indeterminate instead of being forced into either ROC class.
            deficit = 0.040 + rng.beta(2.0, 2.0) * max_deficits[channel_index]
            latent[case_index, channel_index] = max(
                0.20,
                requirements[channel_index] - deficit,
            )

    successes = rng.binomial(observations_per_channel, latent)
    empirical = successes / observations_per_channel

    posterior_alpha = prior_alpha + successes
    posterior_beta = prior_beta + observations_per_channel - successes
    compliance_probability = beta_distribution.sf(
        requirements[None, :],
        posterior_alpha,
        posterior_beta,
    )
    bayesian_scores = np.exp(
        np.sum(weights[None, :] * np.log(np.clip(compliance_probability, 1e-12, 1.0)), axis=1)
    )

    # Fixed rule from the earlier project family: each channel either passes
    # its declared threshold or it does not; the weighted count is the score.
    hard_pass = empirical >= requirements[None, :]
    fixed_scores = hard_pass @ weights
    return labels, bayesian_scores, fixed_scores


def evaluate_fixed_rule_baseline(
    n_cases_per_seed: int = 800,
    observations_per_channel: int = 30,
    n_seeds: int = 20,
    seed: int = 20260810,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
) -> AUCComparison:
    """Compare Bayesian and fixed-rule scores with an equal evidence budget."""
    if n_cases_per_seed < 100 or n_cases_per_seed % 2:
        raise ValueError("n_cases_per_seed must be an even integer >= 100")
    if observations_per_channel < 5:
        raise ValueError("observations_per_channel must be >= 5")
    if n_seeds < 2:
        raise ValueError("n_seeds must be >= 2")

    master_rng = np.random.default_rng(seed)
    all_labels: list[np.ndarray] = []
    all_bayesian: list[np.ndarray] = []
    all_fixed: list[np.ndarray] = []
    bayesian_aucs: list[float] = []
    fixed_aucs: list[float] = []

    for _ in range(n_seeds):
        local_rng = np.random.default_rng(master_rng.integers(0, 2**32 - 1))
        labels, bayesian_scores, fixed_scores = _generate_mission_cases(
            local_rng,
            n_cases_per_seed,
            observations_per_channel,
            prior_alpha,
            prior_beta,
        )
        all_labels.append(labels)
        all_bayesian.append(bayesian_scores)
        all_fixed.append(fixed_scores)
        bayesian_aucs.append(float(roc_auc_score(labels, bayesian_scores)))
        fixed_aucs.append(float(roc_auc_score(labels, fixed_scores)))

    labels = np.concatenate(all_labels)
    bayesian_scores = np.concatenate(all_bayesian)
    fixed_scores = np.concatenate(all_fixed)
    bayesian_auc = float(roc_auc_score(labels, bayesian_scores))
    fixed_auc = float(roc_auc_score(labels, fixed_scores))

    paired_delta = np.asarray(bayesian_aucs) - np.asarray(fixed_aucs)
    delta_mean = float(paired_delta.mean())
    if len(paired_delta) > 1:
        standard_error = paired_delta.std(ddof=1) / np.sqrt(len(paired_delta))
        margin = float(norm.ppf(0.975) * standard_error)
    else:
        margin = 0.0

    bayes_fpr_curve, bayes_tpr_curve, _ = roc_curve(labels, bayesian_scores)
    fixed_fpr_curve, fixed_tpr_curve, _ = roc_curve(labels, fixed_scores)
    bayes_threshold, bayes_fpr, bayes_fnr = _balanced_error_threshold(
        labels,
        bayesian_scores,
    )
    fixed_threshold, fixed_fpr, fixed_fnr = _balanced_error_threshold(
        labels,
        fixed_scores,
    )

    return AUCComparison(
        seed=seed,
        n_seeds=n_seeds,
        n_cases_per_seed=n_cases_per_seed,
        observations_per_channel=observations_per_channel,
        labels=labels,
        bayesian_scores=bayesian_scores,
        fixed_rule_scores=fixed_scores,
        bayesian_auc=bayesian_auc,
        fixed_rule_auc=fixed_auc,
        auc_delta=bayesian_auc - fixed_auc,
        paired_seed_auc_delta_mean=delta_mean,
        paired_seed_auc_delta_ci95=(delta_mean - margin, delta_mean + margin),
        bayesian_roc={"fpr": bayes_fpr_curve, "tpr": bayes_tpr_curve},
        fixed_rule_roc={"fpr": fixed_fpr_curve, "tpr": fixed_tpr_curve},
        bayesian_threshold=bayes_threshold,
        bayesian_fpr=bayes_fpr,
        bayesian_fnr=bayes_fnr,
        fixed_rule_threshold=fixed_threshold,
        fixed_rule_fpr=fixed_fpr,
        fixed_rule_fnr=fixed_fnr,
    )


def evaluate_ontology_conditioned_counterfactual(
    ontology_path: str | Path,
    data_path: str | Path,
    *,
    n_observations: int = 12,
    seed: int = 20260812,
    prior_strength: float = 12.0,
    health_sensitivity: float = 0.70,
) -> dict:
    """Sensitivity test where ontology topology and health condition the priors.

    The same synthetic observations are reused for nominal, radar-failure and
    reconfigured cases.  Only the selected Equipment->Capability->EffectMetric
    path and equipment health alter the prior.  This is a counterfactual
    engineering demonstration, not a calibrated physical probability of kill.
    """
    if n_observations < 5:
        raise ValueError("n_observations must be >= 5")
    if prior_strength <= 0 or not 0 <= health_sensitivity <= 1:
        raise ValueError("invalid prior parameters")

    graph = Graph()
    graph.parse(Path(ontology_path), format="turtle")
    graph.parse(Path(data_path), format="turtle")

    metric_ids = {
        "detection": "EM_DetectionCoverage",
        "identification": "EM_IdentificationAccuracy",
        "interception": "EM_InterceptionSuccess",
        "ooda_closure": "EM_OODAClosureTime",
        "false_alarm_compliance": "EM_FalseAlarmRate",
    }
    nominal_equipment = {
        "detection": "Eq_RadarUnit_007",
        "identification": "Eq_FusionNode_001",
        "interception": "Eq_EW_HPM_001",
        "ooda_closure": "Eq_CommandPost_001",
        "false_alarm_compliance": "Eq_FusionNode_001",
    }
    scenario_equipment = {
        "名义状态": nominal_equipment,
        "主雷达失效": nominal_equipment,
        "本体重构至射频/光电备份": {
            **nominal_equipment,
            "detection": "Eq_RFEO_Backup_002",
        },
    }
    health_override = {("主雷达失效", "Eq_RadarUnit_007"): 0.05}

    rng = np.random.default_rng(seed)
    shared_successes = {
        channel.key: int(
            rng.binomial(n_observations, channel.true_satisfaction_probability)
        )
        for channel in CHANNELS
    }
    weights = _normalise_weights(CHANNELS)
    results = []

    for scenario_name, equipment_by_channel in scenario_equipment.items():
        channel_rows = []
        compliance_probabilities = []
        graph_paths = []
        for channel in CHANNELS:
            equipment_id = equipment_by_channel[channel.key]
            equipment = CUAS[equipment_id]
            metric = CUAS[metric_ids[channel.key]]
            paths = [
                (str(capability).split("#")[-1])
                for capability in graph.objects(equipment, CUAS.implements)
                if (capability, CUAS.produces, metric) in graph
            ]
            if not paths:
                raise ValueError(
                    f"missing Equipment->Capability->EffectMetric path: "
                    f"{equipment_id}/{metric_ids[channel.key]}"
                )
            health_literal = next(graph.objects(equipment, CUAS.healthScore), None)
            if health_literal is None:
                raise ValueError(f"missing healthScore: {equipment_id}")
            health = health_override.get(
                (scenario_name, equipment_id), float(health_literal)
            )
            base_prior_mean = min(channel.requirement_probability + 0.025, 0.995)
            prior_mean = np.clip(
                base_prior_mean * (1.0 - health_sensitivity * (1.0 - health)),
                0.01,
                0.995,
            )
            alpha = prior_mean * prior_strength + shared_successes[channel.key]
            beta_value = (
                (1.0 - prior_mean) * prior_strength
                + n_observations
                - shared_successes[channel.key]
            )
            compliance = float(
                beta_distribution.sf(
                    channel.requirement_probability,
                    alpha,
                    beta_value,
                )
            )
            compliance_probabilities.append(compliance)
            path = f"{equipment_id}->{paths[0]}->{metric_ids[channel.key]}"
            graph_paths.append(path)
            channel_rows.append(
                {
                    "channel": channel.key,
                    "channel_zh": channel.label_zh,
                    "equipment": equipment_id,
                    "capability": paths[0],
                    "health": float(health),
                    "prior_mean": float(prior_mean),
                    "shared_successes": shared_successes[channel.key],
                    "posterior_compliance_probability": compliance,
                }
            )
        score = float(
            np.exp(
                np.sum(
                    weights
                    * np.log(np.clip(compliance_probabilities, 1e-12, 1.0))
                )
            )
        )
        results.append(
            {
                "scenario": scenario_name,
                "mission_compliance_score": score,
                "channels": channel_rows,
                "graph_paths": graph_paths,
            }
        )

    scores = {item["scenario"]: item["mission_compliance_score"] for item in results}
    return {
        "scope": "synthetic_ontology_conditioned_prior_sensitivity",
        "not_field_test": True,
        "seed": seed,
        "n_observations_per_channel": n_observations,
        "prior_strength": prior_strength,
        "health_sensitivity": health_sensitivity,
        "shared_successes": shared_successes,
        "scenarios": results,
        "checks": {
            "radar_failure_reduces_score": scores["主雷达失效"] < scores["名义状态"],
            "reconfiguration_recovers_score": scores["本体重构至射频/光电备份"] > scores["主雷达失效"],
            "paths_derived_from_graph": all(
                len(item["graph_paths"]) == len(CHANNELS) for item in results
            ),
        },
    }


__all__ = [
    "AUCComparison",
    "CHANNELS",
    "COMPOSITE_THRESHOLD",
    "ChannelSpec",
    "FlywheelAudit",
    "FlywheelResult",
    "audit_flywheel_reproducibility",
    "evaluate_fixed_rule_baseline",
    "evaluate_ontology_conditioned_counterfactual",
    "flywheel_channel_rows",
    "simulate_flywheel",
]
