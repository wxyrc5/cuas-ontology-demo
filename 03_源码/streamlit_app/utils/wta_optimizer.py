"""Small, explicit 0-1 WTA demonstrator using SciPy MILP."""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp


def solve_binary_wta(
    probability: np.ndarray,
    capacities: np.ndarray,
    allowed: np.ndarray | None = None,
) -> dict[str, Any]:
    """Maximize sum(P_ij x_ij) with effector capacity and one-assignment gates."""
    p = np.asarray(probability, dtype=float)
    caps = np.asarray(capacities, dtype=float)
    if p.ndim != 2 or caps.shape != (p.shape[0],):
        raise ValueError("probability must be m×n and capacities must have length m")
    if np.any((p < 0.0) | (p > 1.0)) or np.any(caps < 0.0):
        raise ValueError("probabilities and capacities are outside valid bounds")
    mask = np.ones_like(p, dtype=bool) if allowed is None else np.asarray(allowed, dtype=bool)
    if mask.shape != p.shape:
        raise ValueError("allowed mask must match probability matrix")

    m, n = p.shape
    variables = m * n
    a_rows: list[np.ndarray] = []
    upper: list[float] = []
    for i in range(m):
        row = np.zeros(variables)
        row[i * n:(i + 1) * n] = 1.0
        a_rows.append(row)
        upper.append(float(caps[i]))
    for j in range(n):
        row = np.zeros(variables)
        row[j::n] = 1.0
        a_rows.append(row)
        upper.append(1.0)

    result = milp(
        c=-p.reshape(-1),
        integrality=np.ones(variables),
        bounds=Bounds(np.zeros(variables), mask.reshape(-1).astype(float)),
        constraints=LinearConstraint(
            np.vstack(a_rows),
            lb=np.full(len(a_rows), -np.inf),
            ub=np.asarray(upper),
        ),
        options={"time_limit": 2.0},
    )
    if not result.success or result.x is None:
        raise RuntimeError(f"WTA MILP failed: {result.message}")
    x = np.rint(result.x).astype(int).reshape(m, n)
    assignments = [
        {"effector_index": int(i), "target_index": int(j), "p_ij": float(p[i, j])}
        for i, j in np.argwhere(x == 1)
    ]
    return {
        "objective": float(np.sum(p * x)),
        "assignment_matrix": x.tolist(),
        "assignments": assignments,
        "solver_status": str(result.message),
        "constraint_checks": {
            "capacity": bool(np.all(x.sum(axis=1) <= caps + 1e-9)),
            "single_assignment": bool(np.all(x.sum(axis=0) <= 1)),
            "forbidden_pairs": bool(np.all(x[~mask] == 0)),
        },
    }


def demonstration_wta(threat_count: int = 20) -> dict[str, Any]:
    if threat_count < 1:
        raise ValueError("threat_count must be positive")
    effectors = ["EW", "HPM", "HEL", "Kinetic"]
    base = np.asarray([0.25, 0.62, 0.88, 0.84])[:, None]
    target_difficulty = np.linspace(0.92, 1.08, threat_count)[None, :]
    probability = np.clip(base / target_difficulty, 0.01, 0.99)
    capacities = np.asarray([20, 6, 2, 4])
    result = solve_binary_wta(probability, capacities)
    for item in result["assignments"]:
        item["effector"] = effectors[item.pop("effector_index")]
        item["target"] = f"Threat_{item.pop('target_index') + 1:02d}"
    result["effectors"] = effectors
    result["capacities"] = capacities.tolist()
    result["threat_count"] = threat_count
    result["scheduling_mode"] = (
        "容量约束分配；分组/波束驻留是否启用由效应器 engagement_type 决定，"
        "不采用未经标定的‘目标数>5’硬切换阈值"
    )
    result["not_field_optimizer"] = True
    return result
