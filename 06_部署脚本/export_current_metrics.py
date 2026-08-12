"""Export the audited Notebook and Streamlit results into the deployable app."""
from __future__ import annotations

import json
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_DIR = PACKAGE_ROOT / "05_Notebook与数据" / "验证输出"
DECISION_PATH = VALIDATION_DIR / "指标裁决.json"
EXECUTION_PATH = VALIDATION_DIR / "最新执行" / "execution_manifest.json"
APP_ACCEPTANCE_PATH = VALIDATION_DIR / "streamlit_acceptance.json"
OUTPUT_PATH = PACKAGE_ROOT / "03_源码" / "streamlit_app" / "data" / "current_metrics.json"


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    decision = load_json(DECISION_PATH)
    execution = load_json(EXECUTION_PATH)
    acceptance = load_json(APP_ACCEPTANCE_PATH)
    ontology = load_json(VALIDATION_DIR / "metrics_notebook_01.json")
    ooda = load_json(VALIDATION_DIR / "metrics_notebook_02.json")
    bayes = load_json(VALIDATION_DIR / "metrics_notebook_03.json")

    if decision.get("schema_version") != 2 or decision.get("not_field_test") is not True:
        raise ValueError("指标裁决不是当前 schema 2 或未标记 not_field_test=true")
    if execution.get("status") != "passed":
        raise ValueError("Notebook execution manifest is not passed")
    if acceptance.get("status") != "passed":
        raise ValueError("Streamlit acceptance report is not passed")
    if any(item.get("schema_version") != 2 for item in (ontology, ooda, bayes)):
        raise ValueError("Notebook metric schemas are not all version 2")

    notebook_cells = sum(item["code_cells"] for item in execution["notebooks"])
    executed_cells = sum(item["executed_code_cells"] for item in execution["notebooks"])
    page_count = len(acceptance["pages"])
    passed_pages = sum(item["status"] == "passed" for item in acceptance["pages"])

    hpm_timing = ooda["hpm_20_swarm_timing"]
    primary = ooda["primary_20_swarm"]
    payload = {
        "schema_version": 2,
        "generated_at_utc": decision["generated_at_utc"],
        "scope": "current_reproducible_formal_and_synthetic_results_not_field_test",
        "not_field_test": True,
        "bayesian": {
            "auc": bayes["auc"],
            "auc_status": "PASS" if bayes["auc"] >= 0.85 else "FAIL",
            "fixed_rule_auc": bayes["fixed_rule_auc"],
            "auc_delta": bayes["auc_delta"],
            "paired_auc_delta_ci95": bayes["paired_auc_delta_ci95"],
            "final_composite": bayes["seed42_final_composite"],
            "final_composite_ci95": bayes["seed42_final_ci95"],
            "convergence_mean_cycles": bayes["convergence_mean_cycles"],
            "convergence_p95_cycles": bayes["convergence_p95_cycles"],
            "credible_interval_coverage_95": bayes["credible_interval_coverage_95"],
            "posterior_rmse": bayes["posterior_rmse"],
            "decision_threshold": bayes["decision_threshold"],
            "fpr": bayes["fpr"],
            "fnr": bayes["fnr"],
            "observations_per_channel_for_auc": bayes["observations_per_channel_for_auc"],
            "auc_cases_total": bayes["auc_cases_total"],
            "ontology_conditioned_counterfactual": bayes["ontology_conditioned_counterfactual"],
        },
        "ooda": {
            "scope": "synthetic_full_chain_with_sensor_comms_human_aim_effect_and_bda",
            "hpm_20": {
                "decision_mean_s": hpm_timing["decision_loop"]["mean_s"],
                "first_effect_mean_s": hpm_timing["time_to_first_effect"]["mean_s"],
                "full_loop_mean_s": hpm_timing["full_closed_loop"]["mean_s"],
                "full_loop_p90_s": hpm_timing["full_closed_loop"]["p90_s"],
                "probability_under_5s": hpm_timing["full_closed_loop"]["probability_under_deadline"],
            },
            "swarm_20": {
                "mission_definition": primary["mission_definition"],
                "closed_loop_pk": primary["closed_loop_mission_probability"],
                "wilson_ci95": primary["closed_loop_wilson_ci95"],
                "static_closed_loop_pk": primary["static_closed_loop_mission_probability"],
                "mean_neutralized": primary["mean_neutralized"],
                "mean_resource_cost": primary["mean_resource_cost"],
            },
            "capacity_frontier_n_at_pk_0_75": ooda["capacity_frontier_threat_count_at_pk_0_75"],
            "scenario_summary": ooda["scenario_summary"],
            "resource_scaling": ooda["resource_scaling_study"],
            "stress_tests": ooda["stress_tests"],
        },
        "ontology": {
            "formal_owl_consistency_test_completed": ontology["formal_owl_consistency_test_completed"],
            "verdict": ontology["verdict"],
            "core_ot_declared": ontology["core_ot_declared"],
            "core_lt_declared": ontology["core_lt_declared"],
            "extension_ot_declared": ontology.get("extension_ot_declared", 3),
            "extension_lt_declared": ontology.get("extension_lt_declared", 6),
            "tbox_triples": ontology["input_triples"]["cuas-ontology.ttl"],
            "valid_abox_triples": ontology["input_triples"]["cuas-data-valid.ttl"],
            "combined_triples": ontology["combined_tbox_valid_abox_triples"],
            "shacl_negative_violation_count": ontology["shacl_negative_violation_count"],
            "checks": ontology["checks"],
            "swrl_execution_in_scope": ontology["swrl_execution_in_scope"],
        },
        "acceptance": {
            "notebook_code_cells": notebook_cells,
            "notebook_executed_code_cells": executed_cells,
            "streamlit_pages": page_count,
            "streamlit_pages_passed": passed_pages,
            "offline_maps_present": acceptance["airport_assets"]["offline_maps_present"],
            "daxing_codes": acceptance["airport_assets"]["daxing_codes"],
        },
        "known_gaps": [
            "OODA 分量、资源容量和单次作用 Pk 为可查询的工程假设，尚未由机场现场试验或第三方标定。",
            f"当前固定资源包的 Pk≥0.75 扫描前沿为 {ooda['capacity_frontier_threat_count_at_pk_0_75']} 机；25 机及以上不达标，失败结果已保留。",
            "1–6 个同构资源包扩容实验假设共享融合航迹、批量授权和独立并行容量；协调感知主口径加入跨包同步、去冲突与指令编组时延，理想并行结果只作为上界。",
            "20–100 机容量前沿仍是固定种子参数化仿真；协调时延、资源容量和效应器参数尚未由跨阵地台架或机场现场数据标定。",
            "逐目标人工授权、竞争链路、传感退化和 HPM 离线等压力工况会显著降低闭环使命成功率。",
            "SWRL 规则执行、真实专家标注一致性和机场现场试验不在本轮证据范围内。",
        ],
        "sources": {
            "metric_decision": str(DECISION_PATH.relative_to(PACKAGE_ROOT)),
            "notebook_execution": str(EXECUTION_PATH.relative_to(PACKAGE_ROOT)),
            "streamlit_acceptance": str(APP_ACCEPTANCE_PATH.relative_to(PACKAGE_ROOT)),
            "ontology_formal_report": "05_Notebook与数据/验证输出/ontology_consistency_report.md",
        },
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported audited app metrics: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
