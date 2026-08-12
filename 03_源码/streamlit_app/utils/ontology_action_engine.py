"""Deterministic local prototype for ontology-driven effect feedback actions.

The canonical OWL/SHACL files are immutable inputs.  This module evaluates the
threshold rules described in the project manuscript, produces an operational
state revision, and serializes a separate RDF write-back preview with
provenance.  It is a software prototype, not a Palantir Foundry deployment or
an interface to field equipment.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL, XSD


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "ontology.json"
CUAS = Namespace("http://cuas-ontology.org/cuas#")
ACTION = Namespace("http://cuas-ontology.org/action#")
PROV = Namespace("http://www.w3.org/ns/prov#")

RATIO_KEYS = {
    "detection_coverage",
    "identification_accuracy",
    "interception_success_rate",
    "false_alarm_rate",
}
REQUIRED_METRICS = RATIO_KEYS | {"ooda_closure_time_s"}
REQUIRED_CONTEXT = {
    "threat_level_previous",
    "threat_level_current",
    "failed_equipment_ids",
}

ACTION_DEFINITIONS = {
    "ADJUST_SENSOR_SCAN_MODE": ("controls.scan_mode=HIGH_REFRESH", "after.controls.scan_mode == HIGH_REFRESH"),
    "SWITCH_FUSION_MODEL": ("controls.fusion_model=multi_sensor_high_confidence_v2", "after.controls.fusion_model == multi_sensor_high_confidence_v2"),
    "RAISE_MISSION_PRIORITY": ("priority=max(priority, threat_level_current)", "after.priority >= context.threat_level_current"),
    "AUTHORIZE_RESOURCE_REALLOCATION": ("none_before_human_authorization", "pending_human_actions contains AUTHORIZE_RESOURCE_REALLOCATION"),
    "QUARANTINE_AND_RERUN_WTA": ("equipment_status=Failed; controls.wta_recompute_requested=true", "failed equipment excluded and WTA recompute requested"),
    "AUTHORIZE_BATCH_DECISION_MODE": ("none_before_human_authorization", "pending_human_actions contains AUTHORIZE_BATCH_DECISION_MODE"),
    "AUTHORIZE_EFFECTOR_REINFORCEMENT": ("none_before_human_authorization", "pending_human_actions contains AUTHORIZE_EFFECTOR_REINFORCEMENT"),
    "RAISE_FUSION_CONFIRMATION": ("controls.fusion_confirmation=TWO_SOURCE_CONFIRMATION", "after.controls.fusion_confirmation == TWO_SOURCE_CONFIRMATION"),
}


def _load_browser_ontology(path: Path = DATA_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def load_baseline_operational_state(path: Path = DATA_PATH) -> dict[str, Any]:
    """Build the live-state fixture from the same ontology.json used by the UI."""
    ontology = _load_browser_ontology(path)
    object_types = {item["id"]: item for item in ontology["object_types"]}
    mission = object_types["Mission"]["sample_instances"][0]
    equipment = object_types["Equipment"]["sample_instances"]
    mission_id = mission["id"]
    allocations = sorted(
        edge["to"]
        for edge in ontology["edge_instances"]
        if edge["link"] == "L02" and edge["from"] == mission_id
    )
    return {
        "mission_id": mission_id,
        "operator_id": "Operator_Commander_01",
        "revision": 0,
        "priority": int(mission["priority"]),
        "allocated_capabilities": allocations,
        "equipment_status": {
            item["id"]: item.get("status", "Unknown") for item in equipment
        },
        "controls": {
            "scan_mode": "NORMAL",
            "fusion_model": "baseline_fusion_v1",
            "fusion_confirmation": "STANDARD",
            "authorization_mode": "per_target",
            "resource_package_count": 1,
            "wta_recompute_requested": False,
        },
        "pending_human_actions": [],
    }


def _validate_inputs(
    metrics: Mapping[str, Any],
    context: Mapping[str, Any],
    state: Mapping[str, Any],
) -> None:
    missing_metrics = REQUIRED_METRICS - set(metrics)
    missing_context = REQUIRED_CONTEXT - set(context)
    if missing_metrics:
        raise ValueError(f"missing effect metrics: {sorted(missing_metrics)}")
    if missing_context:
        raise ValueError(f"missing action context: {sorted(missing_context)}")
    for key in RATIO_KEYS:
        value = float(metrics[key])
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{key} must be within [0, 1], got {value}")
    if float(metrics["ooda_closure_time_s"]) <= 0.0:
        raise ValueError("ooda_closure_time_s must be positive")
    for key in ("threat_level_previous", "threat_level_current"):
        value = int(context[key])
        if not 1 <= value <= 5:
            raise ValueError(f"{key} must be within [1, 5], got {value}")
    if not 1 <= int(state["priority"]) <= 5:
        raise ValueError("mission priority must be within [1, 5]")
    known_equipment = set(state["equipment_status"])
    unknown_failed = set(context["failed_equipment_ids"]) - known_equipment
    if unknown_failed:
        raise ValueError(f"unknown failed equipment: {sorted(unknown_failed)}")


def evaluate_action_feedback(
    metrics: Mapping[str, Any],
    context: Mapping[str, Any],
    state: Mapping[str, Any] | None = None,
    *,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    """Evaluate manuscript rules and return a non-destructive write-back preview.

    Automatic actions update only the returned state copy.  Resource additions
    and batch authorization remain explicit human-gated requests.  The caller's
    state and the canonical ontology files are never modified.
    """
    baseline = copy.deepcopy(state if state is not None else load_baseline_operational_state())
    _validate_inputs(metrics, context, baseline)
    updated = copy.deepcopy(baseline)
    actions: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []

    def evaluate(
        *,
        rule_id: str,
        trigger: bool,
        observed: Any,
        threshold: str,
        action_code: str,
        description: str,
        execution_status: str,
        target_capabilities: Sequence[str] = (),
        target_equipment: Sequence[str] = (),
    ) -> None:
        evaluations.append(
            {
                "rule_id": rule_id,
                "triggered": bool(trigger),
                "observed": observed,
                "threshold": threshold,
            }
        )
        if not trigger:
            return
        actions.append(
            {
                "rule_id": rule_id,
                "action_code": action_code,
                "description": description,
                "execution_status": execution_status,
                "target_capabilities": list(target_capabilities),
                "target_equipment": list(target_equipment),
                "target_mission": baseline["mission_id"],
                "preconditions": {
                    "observed": observed,
                    "predicate": threshold,
                    "rule_id": rule_id,
                },
                "side_effects": [ACTION_DEFINITIONS[action_code][0]],
                "validation_function": ACTION_DEFINITIONS[action_code][1],
                "expected_revision": int(baseline.get("revision", 0)) + 1,
                "evidence_refs": [
                    f"metric_or_context:{rule_id}",
                    "runtime-trigger-queries.sparql",
                ],
            }
        )

    detection_low = float(metrics["detection_coverage"]) < 0.90
    if detection_low:
        updated["controls"]["scan_mode"] = "HIGH_REFRESH"
    evaluate(
        rule_id="R01_DETECTION_COVERAGE_LOW",
        trigger=detection_low,
        observed=float(metrics["detection_coverage"]),
        threshold="< 0.90",
        action_code="ADJUST_SENSOR_SCAN_MODE",
        description="提高雷达刷新并保持备用传感与数据融合能力分配。",
        execution_status="AUTO_APPLIED",
        target_capabilities=("Cap_Radar_GaN_AESA", "Cap_Data_Integration"),
    )

    identification_low = float(metrics["identification_accuracy"]) < 0.85
    if identification_low:
        updated["controls"]["fusion_model"] = "multi_sensor_high_confidence_v2"
    evaluate(
        rule_id="R02_IDENTIFICATION_ACCURACY_LOW",
        trigger=identification_low,
        observed=float(metrics["identification_accuracy"]),
        threshold="< 0.85",
        action_code="SWITCH_FUSION_MODEL",
        description="切换到高置信多传感融合并请求高分辨率复核。",
        execution_status="AUTO_APPLIED",
        target_capabilities=("Cap_Fusion_MultiSensor", "Cap_Data_Integration"),
    )

    threat_rising = int(context["threat_level_current"]) > int(
        context["threat_level_previous"]
    )
    if threat_rising:
        updated["priority"] = max(
            int(updated["priority"]), int(context["threat_level_current"])
        )
    evaluate(
        rule_id="R03_THREAT_LEVEL_RISING",
        trigger=threat_rising,
        observed={
            "previous": int(context["threat_level_previous"]),
            "current": int(context["threat_level_current"]),
        },
        threshold="current > previous",
        action_code="RAISE_MISSION_PRIORITY",
        description="将使命优先级提升到当前威胁等级。",
        execution_status="AUTO_APPLIED",
        target_capabilities=("Cap_C2_Semantic",),
    )
    if threat_rising:
        updated["pending_human_actions"].append("AUTHORIZE_RESOURCE_REALLOCATION")
    evaluate(
        rule_id="R04_THREAT_RESOURCE_REALLOCATION",
        trigger=threat_rising,
        observed=int(context["threat_level_current"]),
        threshold="threat level rising",
        action_code="AUTHORIZE_RESOURCE_REALLOCATION",
        description="请求从低优先级任务调入一个同构资源包；等待人工授权。",
        execution_status="PENDING_HUMAN_AUTHORIZATION",
        target_capabilities=("Cap_C2_Semantic", "Cap_HPM_Group"),
    )

    failed_equipment = sorted(set(context["failed_equipment_ids"]))
    if failed_equipment:
        for equipment_id in failed_equipment:
            updated["equipment_status"][equipment_id] = "Failed"
        updated["controls"]["wta_recompute_requested"] = True
    evaluate(
        rule_id="R05_EQUIPMENT_FAILURE",
        trigger=bool(failed_equipment),
        observed=failed_equipment,
        threshold="one or more equipment failures",
        action_code="QUARANTINE_AND_RERUN_WTA",
        description="将故障装备移出能力池并重新计算武器目标分配。",
        execution_status="AUTO_APPLIED",
        target_equipment=failed_equipment,
    )

    ooda_late = float(metrics["ooda_closure_time_s"]) >= 5.0
    if ooda_late:
        updated["pending_human_actions"].append("AUTHORIZE_BATCH_DECISION_MODE")
    evaluate(
        rule_id="R06_OODA_DEADLINE_BREACH",
        trigger=ooda_late,
        observed=float(metrics["ooda_closure_time_s"]),
        threshold=">= 5.0 s",
        action_code="AUTHORIZE_BATCH_DECISION_MODE",
        description="请求批量授权与指控通道重编组；等待人工授权。",
        execution_status="PENDING_HUMAN_AUTHORIZATION",
        target_capabilities=("Cap_C2_Semantic", "Cap_Data_Integration"),
    )

    interception_low = float(metrics["interception_success_rate"]) < 0.85
    if interception_low:
        updated["pending_human_actions"].append("AUTHORIZE_EFFECTOR_REINFORCEMENT")
    evaluate(
        rule_id="R07_INTERCEPTION_SUCCESS_LOW",
        trigger=interception_low,
        observed=float(metrics["interception_success_rate"]),
        threshold="< 0.85",
        action_code="AUTHORIZE_EFFECTOR_REINFORCEMENT",
        description="请求软硬杀伤资源重分配与补充交战；等待人工授权。",
        execution_status="PENDING_HUMAN_AUTHORIZATION",
        target_capabilities=("Cap_EW_Directional", "Cap_HPM_Group"),
    )

    false_alarm_high = float(metrics["false_alarm_rate"]) >= 0.02
    if false_alarm_high:
        updated["controls"]["fusion_confirmation"] = "TWO_SOURCE_CONFIRMATION"
    evaluate(
        rule_id="R08_FALSE_ALARM_HIGH",
        trigger=false_alarm_high,
        observed=float(metrics["false_alarm_rate"]),
        threshold=">= 0.02",
        action_code="RAISE_FUSION_CONFIRMATION",
        description="将告警确认切换为双源一致性门限。",
        execution_status="AUTO_APPLIED",
        target_capabilities=("Cap_Fusion_MultiSensor", "Cap_Data_Integration"),
    )

    updated["revision"] = int(baseline.get("revision", 0)) + 1
    updated["pending_human_actions"] = sorted(set(updated["pending_human_actions"]))
    decision_seed = {
        "metrics": {key: metrics[key] for key in sorted(REQUIRED_METRICS)},
        "context": {
            "threat_level_previous": int(context["threat_level_previous"]),
            "threat_level_current": int(context["threat_level_current"]),
            "failed_equipment_ids": failed_equipment,
        },
        "baseline_state": baseline,
        "updated_state": updated,
        "actions": actions,
    }
    digest = hashlib.sha256(
        json.dumps(decision_seed, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest().upper()
    decision_id = f"ACT-{digest[:12]}"
    for action in actions:
        action["action_id"] = f"{decision_id}-{action['rule_id']}"

    if generated_at_utc is None:
        generated_at_utc = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": 1,
        "decision_id": decision_id,
        "generated_at_utc": generated_at_utc,
        "scope": "local_ontology_action_feedback_prototype",
        "not_field_test": True,
        "not_palantir_foundry_deployment": True,
        "canonical_model_mutated": False,
        "metrics": {key: metrics[key] for key in sorted(REQUIRED_METRICS)},
        "context": decision_seed["context"],
        "before_state": baseline,
        "after_state": updated,
        "rule_evaluations": evaluations,
        "actions": actions,
        "summary": {
            "triggered_rules": len(actions),
            "auto_applied": sum(
                item["execution_status"] == "AUTO_APPLIED" for item in actions
            ),
            "pending_human_authorization": sum(
                item["execution_status"] == "PENDING_HUMAN_AUTHORIZATION"
                for item in actions
            ),
        },
    }


def action_result_to_turtle(result: Mapping[str, Any]) -> str:
    """Serialize the decision and proposed state revision as a standalone RDF graph."""
    graph = Graph()
    graph.bind("cuas", CUAS)
    graph.bind("action", ACTION)
    graph.bind("prov", PROV)
    graph.bind("owl", OWL)

    graph.add((ACTION.ActionEvent, RDF.type, OWL.Class))
    graph.add((ACTION.ActionEvent, RDFS.subClassOf, PROV.Activity))
    graph.add((ACTION.DecisionBundle, RDF.type, OWL.Class))

    safe_decision_id = str(result["decision_id"]).replace("-", "_")
    bundle = ACTION[safe_decision_id]
    after = result["after_state"]
    mission = CUAS[after["mission_id"]]
    graph.add((bundle, RDF.type, ACTION.DecisionBundle))
    graph.add((bundle, ACTION.decisionId, Literal(result["decision_id"])))
    graph.add(
        (
            bundle,
            PROV.generatedAtTime,
            Literal(result["generated_at_utc"], datatype=XSD.dateTime),
        )
    )
    graph.add((bundle, ACTION.targetsMission, mission))
    graph.add((bundle, ACTION.canonicalModelMutated, Literal(False)))
    graph.add((bundle, ACTION.notFieldTest, Literal(True)))

    graph.add((mission, CUAS.priority, Literal(int(after["priority"]), datatype=XSD.integer)))
    for capability_id in sorted(after["allocated_capabilities"]):
        graph.add((mission, CUAS.allocates, CUAS[capability_id]))
    for equipment_id, status in sorted(after["equipment_status"].items()):
        graph.add((CUAS[equipment_id], CUAS.operationalStatus, Literal(status)))

    for key, value in sorted(after["controls"].items()):
        graph.add((bundle, ACTION[key], Literal(value)))
    for pending in sorted(after["pending_human_actions"]):
        graph.add((bundle, ACTION.pendingHumanAction, Literal(pending)))

    for key, value in sorted(result["metrics"].items()):
        observation = ACTION[f"{safe_decision_id}_{key}"]
        graph.add((observation, RDF.type, ACTION.EffectObservation))
        graph.add((observation, ACTION.metricKey, Literal(key)))
        graph.add((observation, ACTION.metricValue, Literal(value)))
        graph.add((bundle, ACTION.hasObservation, observation))

    for item in result["actions"]:
        event = ACTION[str(item["action_id"]).replace("-", "_")]
        graph.add((event, RDF.type, ACTION.ActionEvent))
        graph.add((event, ACTION.ruleId, Literal(item["rule_id"])))
        graph.add((event, ACTION.actionCode, Literal(item["action_code"])))
        graph.add((event, ACTION.executionStatus, Literal(item["execution_status"])))
        graph.add((event, RDFS.comment, Literal(item["description"], lang="zh")))
        graph.add((event, ACTION.targetsMission, mission))
        graph.add((event, PROV.wasAssociatedWith, CUAS[after["operator_id"]]))
        graph.add((bundle, ACTION.hasAction, event))
        for capability_id in item["target_capabilities"]:
            graph.add((event, ACTION.targetsCapability, CUAS[capability_id]))
        for equipment_id in item["target_equipment"]:
            graph.add((event, ACTION.targetsEquipment, CUAS[equipment_id]))

    serialized = graph.serialize(format="turtle")
    return serialized.decode("utf-8") if isinstance(serialized, bytes) else serialized


def action_result_to_json(result: Mapping[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2) + "\n"
