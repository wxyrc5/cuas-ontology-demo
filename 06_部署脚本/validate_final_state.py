#!/usr/bin/env python3
"""Cross-check the final C-UAS technical state after notebooks and AppTest.

This is deliberately independent of Notebook code.  It verifies hashes,
schemas and cross-file metric equality so a green notebook or page test cannot
hide a stale exported snapshot from another project version.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_DIR = PACKAGE_ROOT / "05_Notebook与数据" / "验证输出"
OUTPUT_JSON = VALIDATION_DIR / "technical_acceptance_summary.json"
OUTPUT_MD = VALIDATION_DIR / "technical_acceptance_summary.md"


@dataclass
class Check:
    name: str
    passed: bool
    evidence: str


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def same_number(left: Any, right: Any) -> bool:
    return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=1e-12)


def write_markdown(report: dict[str, Any]) -> None:
    lines = [
        "# C-UAS 技术主线最终验收摘要",
        "",
        f"- 总结论：**{'通过' if report['all_passed'] else '失败'}**",
        f"- 生成时间：{report['generated_at']}",
        f"- 项目根目录：`{report['package_root']}`",
        "",
        "| 检查 | 结果 | 证据 |",
        "|---|---:|---|",
    ]
    for item in report["checks"]:
        lines.append(
            f"| {item['name']} | {'通过' if item['passed'] else '失败'} | "
            f"{item['evidence'].replace('|', chr(92) + '|')} |"
        )
    lines.extend(
        [
            "",
            "## 范围",
            "",
            "本报告只证明当前技术主线的本体、Notebook、Streamlit、参数文件和指标快照彼此一致。",
            "申报书、PPT、视频、实名报名材料和最终提交压缩包属于用户明确暂缓的后续步骤。",
        ]
    )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    manifest_path = VALIDATION_DIR / "最新执行" / "execution_manifest.json"
    decision_path = VALIDATION_DIR / "指标裁决.json"
    acceptance_path = VALIDATION_DIR / "streamlit_acceptance.json"
    live_smoke_path = VALIDATION_DIR / "live_streamlit_smoke.json"
    current_path = PACKAGE_ROOT / "03_源码" / "streamlit_app" / "data" / "current_metrics.json"
    metric_paths = {
        "notebook_01": VALIDATION_DIR / "metrics_notebook_01.json",
        "notebook_02": VALIDATION_DIR / "metrics_notebook_02.json",
        "notebook_03": VALIDATION_DIR / "metrics_notebook_03.json",
    }

    manifest = load_json(manifest_path)
    decision = load_json(decision_path)
    acceptance = load_json(acceptance_path)
    live_smoke = load_json(live_smoke_path)
    current = load_json(current_path)
    metrics = {name: load_json(path) for name, path in metric_paths.items()}
    checks: list[Check] = []

    notebooks = manifest.get("notebooks", [])
    notebooks_ok = (
        manifest.get("status") == "passed"
        and len(notebooks) == 4
        and all(
            item.get("status") == "passed"
            and item.get("errors") == 0
            and item.get("executed_code_cells") == item.get("code_cells")
            for item in notebooks
        )
    )
    checks.append(
        Check(
            "4 个规范 Notebook 全量执行",
            notebooks_ok,
            f"notebooks={len(notebooks)}; code_cells="
            f"{sum(item.get('executed_code_cells', 0) for item in notebooks)}/"
            f"{sum(item.get('code_cells', 0) for item in notebooks)}; "
            f"errors={sum(item.get('errors', 0) for item in notebooks)}",
        )
    )

    source_hash_ok = True
    for item in notebooks:
        source = PACKAGE_ROOT / "05_Notebook与数据" / item["source"]
        source_hash_ok &= source.is_file() and sha256(source).upper() == item["source_sha256"].upper()
    checks.append(
        Check(
            "执行清单与当前 Notebook 源文件哈希一致",
            bool(source_hash_ok),
            "4/4 source SHA-256 checked" if source_hash_ok else "source hash mismatch",
        )
    )

    decision_hash_ok = decision.get("schema_version") == 2
    for name, path in metric_paths.items():
        decision_hash_ok &= (
            decision.get("inputs", {}).get(name, {}).get("sha256", "").lower()
            == sha256(path).lower()
        )
    decision_ok = (
        decision_hash_ok
        and decision.get("not_field_test") is True
        and decision.get("summary", {}).get("fail") == 0
    )
    checks.append(
        Check(
            "指标裁决引用当前 3 个上游指标文件",
            bool(decision_ok),
            f"pass={decision.get('summary', {}).get('pass')}; "
            f"fail={decision.get('summary', {}).get('fail')}; "
            f"report_only={decision.get('summary', {}).get('report_only')}",
        )
    )

    ontology = metrics["notebook_01"]
    ontology_ok = (
        ontology.get("schema_version") == 2
        and ontology.get("verdict") == "PASS"
        and ontology.get("core_ot_declared") == 8
        and ontology.get("core_lt_declared") == 10
        and ontology.get("extension_ot_declared") == 3
        and ontology.get("extension_lt_declared") == 6
        and all(ontology.get("checks", {}).values())
    )
    checks.append(
        Check(
            "本体形式一致性",
            bool(ontology_ok),
            "8 core OT / 10 core LT + 3/6 extensions; HermiT and SHACL controls passed",
        )
    )

    ooda = metrics["notebook_02"]
    primary = ooda["primary_20_swarm"]
    ooda_ok = (
        ooda.get("schema_version") == 2
        and primary["closed_loop_mission_probability"] >= 0.75
        and primary["closed_loop_wilson_ci95"][0] >= 0.75
        and primary["closed_loop_mission_probability"]
        > primary["static_closed_loop_mission_probability"]
        and ooda["capacity_frontier_threat_count_at_pk_0_75"] == 20
        and all(ooda.get("checks", {}).values())
    )
    checks.append(
        Check(
            "20 机闭环与容量前沿",
            bool(ooda_ok),
            f"adaptive_pk={primary['closed_loop_mission_probability']:.6f}; "
            f"wilson_low={primary['closed_loop_wilson_ci95'][0]:.6f}; "
            f"static_pk={primary['static_closed_loop_mission_probability']:.6f}; "
            f"frontier={ooda['capacity_frontier_threat_count_at_pk_0_75']}",
        )
    )

    scaling = ooda.get("resource_scaling_study", {})
    scaling_minimum = scaling.get("minimum_packages", [])
    adaptive_packages = {
        int(item["threat_count"]): item["adaptive_minimum_resource_packages"]
        for item in scaling_minimum
    }
    static_packages = {
        int(item["threat_count"]): item["static_minimum_resource_packages"]
        for item in scaling_minimum
    }
    expected_threats = {20, 25, 30, 40, 50, 60, 75, 100}
    high_reliability_minimum = scaling.get("high_reliability_minimum_packages", [])
    scaling_grid = scaling.get("grid", [])
    scaling_ok = (
        scaling.get("monte_carlo_runs_per_cell") == 3_000
        and scaling.get("common_random_numbers_within_threat_count") is True
        and scaling.get("primary_timing_mode") == "coordination_aware"
        and scaling.get("upper_bound_timing_mode") == "ideal_parallel"
        and set(adaptive_packages) == expected_threats
        and set(static_packages) == expected_threats
        and all(
            value is not None and 1 <= int(value) <= 6
            for value in adaptive_packages.values()
        )
        and len(scaling_grid) == 48
        and len(high_reliability_minimum) == 8
        and all(
            item["coordination_aware_ooda_under_deadline_probability"]
            <= item["ideal_parallel_ooda_under_deadline_probability"] + 1e-12
            for item in scaling_grid
        )
        and all(
            item["adaptive_pk_at_minimum"] >= scaling["success_threshold"]
            and item["same_package_pk_advantage"] > 0
            for item in scaling_minimum
        )
    )
    checks.append(
        Check(
            "20–100 机协调感知资源增配与同资源策略优势",
            bool(scaling_ok),
            f"adaptive_min_packages={adaptive_packages}; "
            f"static_min_packages={static_packages}; grid=48 x 3000 runs",
        )
    )

    bayes = metrics["notebook_03"]
    bayes_ok = (
        bayes.get("schema_version") == 2
        and bayes["auc"] > bayes["fixed_rule_auc"]
        and bayes["paired_auc_delta_ci95"][0] > 0
        and all(bayes.get("checks", {}).values())
    )
    checks.append(
        Check(
            "五通道贝叶斯与固定规则公平对照",
            bool(bayes_ok),
            f"bayesian_auc={bayes['auc']:.6f}; fixed_auc={bayes['fixed_rule_auc']:.6f}; "
            f"delta_ci95=[{bayes['paired_auc_delta_ci95'][0]:.6f}, "
            f"{bayes['paired_auc_delta_ci95'][1]:.6f}]",
        )
    )

    pages = acceptance.get("pages", [])
    interactive_pk_text = (
        acceptance.get("airport_resource_control", {})
        .get("metrics", {})
        .get("闭环使命 Pk", "")
    )
    try:
        interactive_pk_ratio = float(interactive_pk_text.rstrip("%")) / 100.0
    except (TypeError, ValueError):
        interactive_pk_ratio = -1.0
    acceptance_ok = (
        acceptance.get("status") == "passed"
        and len(pages) == 8
        and all(item.get("status") == "passed" and not item.get("exceptions") for item in pages)
        and acceptance.get("ontology_assets", {}).get("canonical_graph_triples") == 620
        and all(
            count > 0
            for count in acceptance.get("ontology_assets", {}).get("sparql_template_rows", {}).values()
        )
        and acceptance.get("airport_assets", {}).get("non_circular_defense_envelopes")
        == {"PKX": 3, "BRU": 3, "MUC": 3}
        and acceptance.get("airport_resource_control", {}).get("status") == "passed"
        and acceptance.get("airport_resource_control", {}).get("threat_count") == 50
        and acceptance.get("airport_resource_control", {}).get("resource_package_count") == 3
        and interactive_pk_ratio >= 0.75
    )
    checks.append(
        Check(
            "Streamlit、SPARQL、离线地图与防御包络验收",
            bool(acceptance_ok),
            f"pages={sum(item.get('status') == 'passed' for item in pages)}/{len(pages)}; "
            f"templates={acceptance.get('ontology_assets', {}).get('sparql_template_rows')}; "
            f"envelopes={acceptance.get('airport_assets', {}).get('non_circular_defense_envelopes')}; "
            f"interactive_50x3={acceptance.get('airport_resource_control', {}).get('metrics')}",
        )
    )

    trajectory = acceptance.get("trajectory_rendering", {})
    trajectory_ok = (
        trajectory.get("status") == "passed"
        and trajectory.get("airport") == "PKX/ZBAD"
        and trajectory.get("threat_count") == 20
        and trajectory.get("frames") == 60
        and trajectory.get("deterministic_same_seed") is True
        and trajectory.get("different_seed_changes_trajectory") is True
        and trajectory.get("three_altitude_waves") is True
        and 0.0 < float(trajectory.get("max_frame_step_km", math.inf)) <= 0.5
        and float(trajectory.get("max_outward_frame_step_km", math.inf)) <= 1e-9
        and trajectory.get("intercepts_after_envelope_entry_and_in_act") is True
        and trajectory.get("offline_map_embedded") is True
        and trajectory.get("defense_envelopes_2d") == 3
        and trajectory.get("defense_envelopes_3d") == 3
        and trajectory.get("shared_2d_3d_uav_states") == 20
    )
    checks.append(
        Check(
            "蜂群轨迹连续性与二维/三维同源状态",
            bool(trajectory_ok),
            f"PKX 20 UAV x 60 frames; max_step="
            f"{trajectory.get('max_frame_step_km')} km; max_outward="
            f"{trajectory.get('max_outward_frame_step_km')} km; "
            f"2D/3D states={trajectory.get('shared_2d_3d_uav_states')}",
        )
    )

    live_smoke_ok = (
        live_smoke.get("status") == "passed"
        and live_smoke.get("app") == "03_源码/streamlit_app/app.py"
        and live_smoke.get("health_status") == 200
        and live_smoke.get("health_body") == "ok"
        and live_smoke.get("root_status") == 200
        and live_smoke.get("root_contains_streamlit") is True
        and live_smoke.get("process_exited_early") is False
        and live_smoke.get("process_still_running_after_cleanup") is False
        and live_smoke.get("stderr_contains_traceback") is False
    )
    checks.append(
        Check(
            "本地 Streamlit 隔离端口真实启动",
            bool(live_smoke_ok),
            f"port={live_smoke.get('tested_port')}; startup="
            f"{live_smoke.get('startup_seconds')}s; health="
            f"{live_smoke.get('health_status')}/{live_smoke.get('health_body')}; "
            f"root={live_smoke.get('root_status')}; cleanup="
            f"{not live_smoke.get('process_still_running_after_cleanup', True)}",
        )
    )

    action_feedback = acceptance.get("action_feedback", {})
    action_feedback_ok = (
        action_feedback.get("status") == "passed"
        and action_feedback.get("triggered_rules") == 8
        and action_feedback.get("auto_applied") == 5
        and action_feedback.get("pending_human_authorization") == 3
        and action_feedback.get("rdf_triples", 0) >= 50
        and action_feedback.get("deterministic") is True
        and action_feedback.get("caller_state_immutable") is True
        and action_feedback.get("canonical_model_unchanged") is True
        and action_feedback.get("not_palantir_foundry_deployment") is True
    )
    checks.append(
        Check(
            "本体 Effect→Action→Mission 写回原型",
            bool(action_feedback_ok),
            f"decision={action_feedback.get('decision_id')}; "
            f"rules={action_feedback.get('triggered_rules')}; "
            f"auto={action_feedback.get('auto_applied')}; "
            f"human_gate={action_feedback.get('pending_human_authorization')}; "
            f"rdf_triples={action_feedback.get('rdf_triples')}; canonical unchanged",
        )
    )

    app_source = PACKAGE_ROOT / "03_源码" / "streamlit_app"
    deploy_mirror = PACKAGE_ROOT / "03_源码" / "streamlit_cloud_deploy"
    managed_roots = {
        "app.py", "demo_mode.py", "README.md", "requirements.txt",
        "pages", "utils", "data", "static", ".streamlit",
    }
    managed_source_files = [
        path
        for path in app_source.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
        and path.relative_to(app_source).parts[0] in managed_roots
    ]
    mirror_mismatches = []
    for source_file in managed_source_files:
        relative = source_file.relative_to(app_source)
        target_file = deploy_mirror / relative
        if not target_file.is_file() or sha256(source_file) != sha256(target_file):
            mirror_mismatches.append(str(relative))
    checks.append(
        Check(
            "Streamlit 唯一主线与部署镜像哈希一致",
            not mirror_mismatches,
            f"{len(managed_source_files)}/{len(managed_source_files)} managed files matched"
            if not mirror_mismatches else f"mismatches={mirror_mismatches}",
        )
    )

    current_ok = (
        current.get("schema_version") == 2
        and current.get("not_field_test") is True
        and current["ontology"]["verdict"] == ontology["verdict"]
        and same_number(current["ooda"]["swarm_20"]["closed_loop_pk"], primary["closed_loop_mission_probability"])
        and same_number(current["ooda"]["swarm_20"]["static_closed_loop_pk"], primary["static_closed_loop_mission_probability"])
        and current["ooda"]["capacity_frontier_n_at_pk_0_75"]
        == ooda["capacity_frontier_threat_count_at_pk_0_75"]
        and current["ooda"]["resource_scaling"]["minimum_packages"]
        == scaling_minimum
        and same_number(current["bayesian"]["auc"], bayes["auc"])
        and same_number(current["bayesian"]["fixed_rule_auc"], bayes["fixed_rule_auc"])
        and current["acceptance"]["streamlit_pages_passed"] == 8
        and current["acceptance"]["notebook_executed_code_cells"]
        == sum(item["executed_code_cells"] for item in notebooks)
    )
    checks.append(
        Check(
            "网页指标快照与 Notebook/验收结果完全一致",
            bool(current_ok),
            f"notebook_cells={current['acceptance']['notebook_executed_code_cells']}; "
            f"pages={current['acceptance']['streamlit_pages_passed']}; "
            f"pk20={current['ooda']['swarm_20']['closed_loop_pk']}; "
            f"auc={current['bayesian']['auc']}",
        )
    )

    required_files = [
        PACKAGE_ROOT / "03_源码" / "本体模型" / "cuas-ontology.ttl",
        PACKAGE_ROOT / "03_源码" / "本体模型" / "cuas-data-valid.ttl",
        PACKAGE_ROOT / "03_源码" / "本体模型" / "cuas-data-test.ttl",
        PACKAGE_ROOT / "03_源码" / "本体模型" / "cuas-shapes.ttl",
        PACKAGE_ROOT / "03_源码" / "streamlit_app" / "data" / "ooda_timing_params.json",
        PACKAGE_ROOT / "03_源码" / "streamlit_app" / "data" / "swarm_resources.json",
        PACKAGE_ROOT / "03_源码" / "streamlit_app" / "data" / "airports.json",
        PACKAGE_ROOT / "05_Notebook与数据" / "验证输出" / "swarm_resource_scaling_grid.csv",
        PACKAGE_ROOT / "05_Notebook与数据" / "验证输出" / "swarm_resource_scaling_minimum.csv",
        PACKAGE_ROOT / "05_Notebook与数据" / "验证输出" / "swarm_resource_scaling_thresholds.csv",
        PACKAGE_ROOT / "05_Notebook与数据" / "验证输出" / "ooda_coordination_parameters_100_swarm_6_packages.csv",
        PACKAGE_ROOT / "05_Notebook与数据" / "验证输出" / "fig2_5_resource_scaling.png",
        PACKAGE_ROOT / "05_Notebook与数据" / "验证输出" / "action_feedback_demo.json",
        PACKAGE_ROOT / "05_Notebook与数据" / "验证输出" / "action_feedback_writeback.ttl",
        live_smoke_path,
    ]
    missing = [str(path.relative_to(PACKAGE_ROOT)) for path in required_files if not path.is_file()]
    checks.append(
        Check(
            "形式模型、OODA、蜂群资源与机场参数文件齐备",
            not missing,
            f"{len(required_files)}/{len(required_files)} required files present"
            if not missing else f"missing={missing}",
        )
    )

    report = {
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "package_root": str(PACKAGE_ROOT),
        "all_passed": all(item.passed for item in checks),
        "checks": [asdict(item) for item in checks],
        "sources": {
            "execution_manifest": str(manifest_path.relative_to(PACKAGE_ROOT)),
            "metric_decision": str(decision_path.relative_to(PACKAGE_ROOT)),
            "streamlit_acceptance": str(acceptance_path.relative_to(PACKAGE_ROOT)),
            "live_streamlit_smoke": str(live_smoke_path.relative_to(PACKAGE_ROOT)),
            "current_metrics": str(current_path.relative_to(PACKAGE_ROOT)),
        },
        "deferred_scope": [
            "official application forms with identity, signatures, and seal",
            "competition presentation deck and final recorded video",
            "official submission archives",
        ],
    }
    OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"JSON_REPORT={OUTPUT_JSON}")
    print(f"MARKDOWN_REPORT={OUTPUT_MD}")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
