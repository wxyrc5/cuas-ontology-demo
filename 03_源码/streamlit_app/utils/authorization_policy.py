"""Transparent workload-aware authorization policy for the demo."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np


POLICY_PATH = Path(__file__).resolve().parents[1] / "data" / "authorization_policy.json"
HIGH_RISK_EFFECTS = {"HPM", "HEL", "KINETIC"}
L1_ACTIONS = {
    "ADJUST_SENSOR_SCAN_MODE",
    "SWITCH_FUSION_MODEL",
    "QUARANTINE_AND_RERUN_WTA",
    "RAISE_FUSION_CONFIRMATION",
}


@lru_cache(maxsize=1)
def load_authorization_policy() -> dict[str, Any]:
    payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or len(payload.get("levels", [])) != 3:
        raise ValueError("unsupported authorization policy")
    return payload


def workload_index(
    target_count: int,
    pending_actions: int,
    contested_link: bool,
    geofence_conflict: bool,
) -> float:
    weights = load_authorization_policy()["workload_model"]["weights"]
    value = (
        weights["target_count_over_20"] * min(max(target_count, 0) / 20.0, 2.0)
        + weights["pending_actions_over_5"] * min(max(pending_actions, 0) / 5.0, 2.0)
        + weights["contested_link"] * int(contested_link)
        + weights["geofence_conflict"] * int(geofence_conflict)
    )
    return float(np.clip(value, 0.0, 1.0))


def decide_authorization(
    *,
    action_code: str,
    effect_type: str,
    posterior_confidence: float,
    target_count: int,
    pending_actions: int = 0,
    contested_link: bool = False,
    geofence_conflict: bool = False,
    preauthorized_plan: bool = True,
) -> dict[str, Any]:
    """Select L1/L2/L3 without allowing workload to lower safety authority."""
    if not 0.0 <= posterior_confidence <= 1.0:
        raise ValueError("posterior_confidence must be within [0, 1]")
    policy = load_authorization_policy()
    workload = workload_index(
        target_count, pending_actions, contested_link, geofence_conflict
    )
    effect = effect_type.upper()

    if action_code in L1_ACTIONS and effect in {"NONE", "SENSOR", "FUSION"}:
        level, status = "L1", "AUTO_ALLOWED"
        reason = "动作可逆且不产生外部效应；通过数据、坐标和安全门后自动执行。"
    elif (
        effect not in HIGH_RISK_EFFECTS
        and preauthorized_plan
        and posterior_confidence >= float(policy["confidence_gate"])
        and not geofence_conflict
    ):
        level, status = "L2", "PENDING_OPERATOR_APPROVAL"
        reason = "置信度达到预案门限且无禁射界冲突；合并为一次批次批准，不自动越权。"
    else:
        level, status = "L3", "PENDING_COMMANDER_APPROVAL"
        reason = "高风险效应、低置信度或空间冲突触发默认拒绝，必须由指挥员明确批准。"

    level_row = next(row for row in policy["levels"] if row["level"] == level)
    return {
        "authorization_level": level,
        "decision_status": status,
        "workload_index": workload,
        "workload_band": "高" if workload >= 0.75 else "中" if workload >= 0.45 else "低",
        "response_budget_s": float(level_row["response_budget_s"]),
        "authority": level_row["authority"],
        "reason": reason,
        "one_sentence_rationale": (
            f"建议等级 {level}：后验置信度 {posterior_confidence:.1%}，"
            f"认知负荷 {workload:.2f}，效应类型 {effect}；{reason}"
        ),
        "not_operational_roe": True,
    }
