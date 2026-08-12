"""Rebuild Notebook 04 as the single-source metric adjudication notebook."""
from __future__ import annotations

from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = PACKAGE_ROOT / "05_Notebook与数据" / "notebook_04_demo_end_to_end.ipynb"


def main() -> None:
    old = nbformat.read(NOTEBOOK_PATH, as_version=4)
    metadata = old.metadata
    metadata.setdefault("cuas_reproducibility", {})["adjudication_rebuilt_on"] = "2026-08-10"

    cells = [
        new_markdown_cell(
            """# 5.4 实验 4：端到端指标裁决与引用边界

本 Notebook 不另造第四套实验值。它依次读取 Notebook 01–03 本次生成的机器可读指标，形成唯一的 `验证输出/指标裁决.json` 和 `指标裁决.md`。

裁决覆盖三条证据链：

- **本体正确性**：8 OT / 10 LT、SHACL 正/负向对照、HermiT OWL 2 DL 正/负向一致性；
- **闭环效能**：真实分量化 OODA 全链路时延、同资源 20 机蜂群容量约束裁决、规模容量边界；
- **自适应飞轮**：五通道 Beta-Binomial 后验收敛，以及同案例、同观测预算下相对固定规则的 AUC 对照。

所有结果都是固定种子、参数化工程仿真或形式验证结果；不是现场实测、实装武器鉴定或比赛官方评分。
"""
        ),
        new_code_cell(
            """import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# CUAS_PORTABLE_NOTEBOOK_BOOTSTRAP
_cwd = Path.cwd().resolve()
PACKAGE_ROOT = next(
    (candidate for candidate in (_cwd, *_cwd.parents) if (candidate / '03_源码').is_dir()),
    None,
)
if PACKAGE_ROOT is None:
    raise RuntimeError('请从完整项目包的 05_Notebook与数据 目录启动 JupyterLab。')
VALIDATION_DIR = PACKAGE_ROOT / '05_Notebook与数据' / '验证输出'
FIGURE_DIR = VALIDATION_DIR / 'figures'
FIGURE_DIR.mkdir(parents=True, exist_ok=True)
print('项目根目录:', PACKAGE_ROOT)
"""
        ),
        new_markdown_cell(
            """## 1. 锁定上游实验与哈希

任一指标文件缺失、结构版本不是 2，或没有明确标注 `not_field_test=true`，本 Notebook 立即失败，防止旧数值或展示占位值混入结论。
"""
        ),
        new_code_cell(
            """metric_paths = {
    'notebook_01': VALIDATION_DIR / 'metrics_notebook_01.json',
    'notebook_02': VALIDATION_DIR / 'metrics_notebook_02.json',
    'notebook_03': VALIDATION_DIR / 'metrics_notebook_03.json',
}
missing = [str(path) for path in metric_paths.values() if not path.is_file()]
if missing:
    raise FileNotFoundError('缺少上游本次执行指标文件: ' + '; '.join(missing))

metrics = {name: json.loads(path.read_text(encoding='utf-8')) for name, path in metric_paths.items()}
for name, payload in metrics.items():
    if payload.get('schema_version') != 2:
        raise ValueError(f'{name} schema_version 不是 2')
    if payload.get('not_field_test') is not True:
        raise ValueError(f'{name} 未明确标注 not_field_test=true')

input_hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in metric_paths.items()}
source_scope = pd.DataFrame([
    {'来源': name, '范围': payload['scope'], '现场实测': '否', 'SHA256': input_hashes[name][:16]}
    for name, payload in metrics.items()
])
source_scope
"""
        ),
        new_markdown_cell(
            """## 2. 工程门槛裁决

`PASS/FAIL` 仅表示是否达到项目内部预设门槛；`REPORT_ONLY` 表示只报告事实值。三者都不等于比赛官方评分。
"""
        ),
        new_code_cell(
            """ontology = metrics['notebook_01']
ooda = metrics['notebook_02']
bayes = metrics['notebook_03']

rows = []
def add_metric(metric_id, label, value, unit, threshold, passed, source, scope, report_only=False):
    rows.append({
        'metric_id': metric_id,
        '指标': label,
        'value': float(value),
        'unit': unit,
        '工程门槛': threshold,
        'status': 'REPORT_ONLY' if report_only else ('PASS' if bool(passed) else 'FAIL'),
        'source': source,
        'scope': scope,
    })

oc = ontology['checks']
add_metric('ontology.formal_all_pass', '形式一致性分层验证全部通过', int(oc['all_formal_checks_pass']), 'bool', '= 1', oc['all_formal_checks_pass'], 'notebook_01', ontology['scope'])
add_metric('ontology.core_ot', '核心 Object Type 声明数', ontology['core_ot_declared'], 'OT', '= 8', ontology['core_ot_declared'] == 8, 'notebook_01', ontology['scope'])
add_metric('ontology.core_lt', '核心 Link Type 声明数', ontology['core_lt_declared'], 'LT', '= 10', ontology['core_lt_declared'] == 10, 'notebook_01', ontology['scope'])
add_metric('ontology.shacl_negative_count', 'SHACL 受控负向违规检出数', ontology['shacl_negative_violation_count'], 'violations', '= 2', ontology['shacl_negative_violation_count'] == 2, 'notebook_01', ontology['scope'])
add_metric('ontology.hermit_positive', 'HermiT 正向 ABox 一致', int(oc['hermit_positive_consistent']), 'bool', '= 1', oc['hermit_positive_consistent'], 'notebook_01', ontology['scope'])
add_metric('ontology.hermit_negative', 'HermiT 互斥类型负向对照被拒绝', int(oc['hermit_disjointness_negative_control_rejected']), 'bool', '= 1', oc['hermit_disjointness_negative_control_rejected'], 'notebook_01', ontology['scope'])

hpm = ooda['hpm_20_swarm_timing']
primary = ooda['primary_20_swarm']
resource_scaling = ooda['resource_scaling_study']
scaling_minimum = resource_scaling['minimum_packages']
high_reliability_minimum = resource_scaling['high_reliability_minimum_packages']
scaling_all_restored = all(
    item['adaptive_minimum_resource_packages'] is not None
    and item['adaptive_pk_at_minimum'] >= resource_scaling['success_threshold']
    for item in scaling_minimum
)
scaling_max_packages = max(
    item['adaptive_minimum_resource_packages']
    for item in scaling_minimum
    if item['adaptive_minimum_resource_packages'] is not None
)
scaling_min_same_package_advantage = min(
    item['same_package_pk_advantage']
    for item in scaling_minimum
    if item['same_package_pk_advantage'] is not None
)
add_metric('ooda.hpm_full_p90_s', '20 机 HPM 完整闭环 P90', hpm['full_closed_loop']['p90_s'], 's', '< 5', hpm['full_closed_loop']['p90_s'] < 5, 'notebook_02', ooda['scope'])
add_metric('ooda.hpm_under_5_probability', '20 机 HPM P(完整闭环<5s)', hpm['full_closed_loop']['probability_under_deadline'], 'ratio', '≥ 0.90', hpm['full_closed_loop']['probability_under_deadline'] >= 0.90, 'notebook_02', ooda['scope'])
add_metric('swarm.20_closed_loop_pk', '20 机容量约束闭环使命 Pk', primary['closed_loop_mission_probability'], 'probability', '≥ 0.75', primary['closed_loop_mission_probability'] >= 0.75, 'notebook_02', ooda['scope'])
add_metric('swarm.20_wilson_lower', '20 机闭环使命 Pk 的 Wilson 95% 下界', primary['closed_loop_wilson_ci95'][0], 'probability', '≥ 0.75', primary['closed_loop_wilson_ci95'][0] >= 0.75, 'notebook_02', ooda['scope'])
add_metric('swarm.static_20_closed_loop_pk', '同资源静态覆盖表（无反馈）20 机闭环 Pk', primary['static_closed_loop_mission_probability'], 'probability', '仅报告', True, 'notebook_02', ooda['scope'], report_only=True)
add_metric('swarm.capacity_frontier_n', '固定资源包在 Pk≥0.75 下的规模前沿', ooda['capacity_frontier_threat_count_at_pk_0_75'], 'targets', '≥ 20', ooda['capacity_frontier_threat_count_at_pk_0_75'] >= 20, 'notebook_02', ooda['scope'])
add_metric('swarm.scaling_max_packages', '20–100 机达到协调感知 Pk≥0.75 所需最大同构资源包数', scaling_max_packages, 'packages', '≤ 6', scaling_all_restored and scaling_max_packages <= 6, 'notebook_02', ooda['scope'])
add_metric('swarm.scaling_min_pk_advantage', '达标资源包下动态反馈相对静态规则的最小 Pk 优势', scaling_min_same_package_advantage, 'probability', '> 0', scaling_min_same_package_advantage > 0, 'notebook_02', ooda['scope'])

add_metric('bayes.final_composite', '五通道终态合成后验', bayes['seed42_final_composite'], 'probability', '≥ 0.90', bayes['seed42_final_composite'] >= 0.90, 'notebook_03', bayes['scope'])
add_metric('bayes.convergence_mean_cycles', '持续达标收敛周期均值', bayes['convergence_mean_cycles'], 'cycles', '≤ 50', bayes['convergence_mean_cycles'] <= 50, 'notebook_03', bayes['scope'])
add_metric('bayes.ci_coverage_95', '95% 可信区间覆盖率', bayes['credible_interval_coverage_95'], 'ratio', '0.90–0.99', 0.90 <= bayes['credible_interval_coverage_95'] <= 0.99, 'notebook_03', bayes['scope'])
add_metric('bayes.posterior_rmse', '终态后验 RMSE', bayes['posterior_rmse'], '', '≤ 0.03', bayes['posterior_rmse'] <= 0.03, 'notebook_03', bayes['scope'])
add_metric('bayes.auc', '贝叶斯同预算 AUC', bayes['auc'], '', '≥ 0.85', bayes['auc'] >= 0.85, 'notebook_03', bayes['scope'])
add_metric('bayes.fixed_rule_auc', '固定规则同预算 AUC', bayes['fixed_rule_auc'], '', '仅报告', True, 'notebook_03', bayes['scope'], report_only=True)
add_metric('bayes.auc_delta', '贝叶斯相对固定规则 AUC 增量', bayes['auc_delta'], '', '95% CI 下界 > 0', bayes['paired_auc_delta_ci95'][0] > 0, 'notebook_03', bayes['scope'])
add_metric('bayes.fpr', '贝叶斯阈值 FPR', bayes['fpr'], 'ratio', '≤ 0.10', bayes['fpr'] <= 0.10, 'notebook_03', bayes['scope'])
add_metric('bayes.fnr', '贝叶斯阈值 FNR', bayes['fnr'], 'ratio', '≤ 0.10', bayes['fnr'] <= 0.10, 'notebook_03', bayes['scope'])

df_adjudication = pd.DataFrame(rows)
df_adjudication[['指标', 'value', 'unit', '工程门槛', 'status', 'source']]
"""
        ),
        new_markdown_cell("""## 3. 三条证据链的可视化裁决"""),
        new_code_cell(
            """fig, axes = plt.subplots(1, 3, figsize=(17, 5.0))

formal_labels = ['8 OT/10 LT', 'SHACL 正向', 'SHACL 负向', 'HermiT 正向', 'HermiT 负向']
formal_values = [
    int(oc['core_8_ot_10_lt_pass']), int(oc['shacl_positive_conforms']),
    int(oc['shacl_negative_control_detected_exactly_two']),
    int(oc['hermit_positive_consistent']), int(oc['hermit_disjointness_negative_control_rejected']),
]
axes[0].bar(np.arange(len(formal_labels)), formal_values, color='#2CA02C')
axes[0].set_xticks(np.arange(len(formal_labels)), formal_labels, rotation=25)
axes[0].set_ylim(0, 1.08)
axes[0].set_title('本体形式验证')

pk_values = [primary['closed_loop_mission_probability'], primary['static_closed_loop_mission_probability']]
axes[1].bar(['动态反馈', '静态覆盖表\\n（无反馈）'], pk_values, color=['#4C78A8', '#9D9D9D'])
axes[1].axhline(0.75, color='#D62728', linestyle='--', label='工程门槛 0.75')
axes[1].set_ylim(0, 1.0)
axes[1].set_ylabel('闭环使命 Pk')
axes[1].set_title('20 机同资源裁决')
axes[1].legend()

auc_values = [bayes['auc'], bayes['fixed_rule_auc']]
axes[2].bar(['贝叶斯飞轮', '固定规则'], auc_values, color=['#7B2CBF', '#9D9D9D'])
axes[2].set_ylim(0.75, 1.0)
axes[2].set_ylabel('AUC')
axes[2].set_title(f"同案例同预算；ΔAUC={bayes['auc_delta']:.3f}")

plt.suptitle('三条证据链的本次执行裁决（非现场实测）', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(FIGURE_DIR / 'fig4_1_metric_adjudication.png', dpi=150, bbox_inches='tight')
plt.show()
"""
        ),
        new_code_cell(
            """scale_rows = []
for scenario, values in ooda['scenario_summary'].items():
    scale_rows.append({
        'scenario': scenario,
        'N': values['threat_count'],
        'adaptive_pk': values['adaptive_closed_loop_mission_probability'],
        'static_pk': values['static_closed_loop_mission_probability'],
        'mean_neutralized': values['adaptive_mean_neutralized'],
    })
scale_df = pd.DataFrame(scale_rows).sort_values('N')

fig, axes = plt.subplots(1, 2, figsize=(14, 4.8))
axes[0].plot(scale_df['N'], scale_df['adaptive_pk'], marker='o', linewidth=2.5, label='动态反馈')
axes[0].plot(scale_df['N'], scale_df['static_pk'], marker='s', linewidth=2, label='静态覆盖表（无反馈）')
axes[0].axhline(0.75, color='#D62728', linestyle='--', label='Pk=0.75')
axes[0].axvline(ooda['capacity_frontier_threat_count_at_pk_0_75'], color='#2CA02C', linestyle=':', label='容量前沿')
axes[0].set_xlabel('蜂群规模 N')
axes[0].set_ylabel('闭环使命 Pk')
axes[0].set_ylim(-0.03, 1.03)
axes[0].set_title('固定资源包的容量曲线')
axes[0].legend()

effector_df = pd.DataFrame(ooda['ooda_effector_comparison'])
x = np.arange(len(effector_df))
axes[1].bar(x, effector_df['full_loop_mean_s'], color='#4C78A8', label='完整闭环均值')
axes[1].scatter(x, effector_df['full_loop_p90_s'], color='#E45756', marker='D', label='P90')
axes[1].axhline(5.0, color='#D62728', linestyle='--', label='5 s')
axes[1].set_xticks(x, effector_df['effector_name_zh'], rotation=20)
axes[1].set_ylabel('秒')
axes[1].set_title('不同效应器的完整 OODA 闭环')
axes[1].legend()

plt.tight_layout()
plt.savefig(FIGURE_DIR / 'fig4_2_capacity_and_ooda.png', dpi=150, bbox_inches='tight')
plt.show()
scale_df
"""
        ),
        new_markdown_cell(
            """## 4. 唯一指标文件与对外引用边界

任何申报书、答辩稿或演示页引用数值时，必须从下列裁决文件回填，并保留“形式验证/参数化仿真/非现场实测”的限定语。
"""
        ),
        new_code_cell(
            """claims_policy = {
    'allowed': [
        '当前 OWL 2 DL TBox + 正向 ABox 通过 HermiT 一致性验证，互斥类型负向对照被正确拒绝。',
        '当前正向 ABox 通过 SHACL，两个受控错误值被准确检出。',
        '完整 OODA 模型显式包含传感、通信、融合识别、人工授权、分配、瞄准、效应到达和 BDA。',
        '固定资源包下，20 机动态反馈闭环使命 Pk 及其 Wilson 95% 下界达到 0.75 内部门槛。',
        '固定资源包的 Pk>=0.75 规模前沿由 1/5/10/15/20/25/30/40/50/60/75/100 扫描确定。',
        '在同构并行资源包、共享融合航迹与批量授权的合成假设下，20–100 机在 1–6 包扫描内报告 Pk>=0.75 与 Pk>=0.95 的容量前沿。',
        '多资源包主口径加入跨包同步、任务去冲突和指令编组时延；理想并行结果只作为容量上界。',
        '在各威胁规模的最少达标资源包下，动态反馈 Pk 高于同资源静态冻结规则。',
        '贝叶斯与固定规则在同案例、同五通道、同观测预算下比较 AUC。',
    ],
    'forbidden_without_new_evidence': [
        '上述 OODA、Pk 或 AUC 是机场现场实测或实装武器鉴定。',
        '固定资源能够对任意规模蜂群维持高成功率。',
        '资源包数量或合成行动成本等同于采购报价或全寿命周期成本。',
        '多资源包协调时延已经由真实竞争链路、跨阵地台架或第三方数据标定。',
        'HermiT/SHACL 已证明所有未来实例或 SWRL 规则均正确。',
        '参数表中的时间和效能数值已由第三方标定。',
    ],
    'replaced_legacy_claims': {
        'legacy_20_swarm_sigmoid': '只保留为废弃诊断值，不再作为蜂群使命成功率。',
        'software_only_ooda_latency': '已由包含真实链路分量的秒级完整闭环模型替代。',
        'rdflib_only_consistency': '已由 HermiT + SHACL 正负向验证替代。',
        'unequal_or_unexplained_auc': '已由同案例同观测预算的固定规则对照替代。',
    },
}

decision_payload = {
    'schema_version': 2,
    'generated_at_utc': datetime.now(timezone.utc).isoformat(),
    'purpose': 'single_source_of_truth_for_current_reproducible_project_metrics',
    'not_official_competition_score': True,
    'not_field_test': True,
    'inputs': {
        name: {
            'path': str(metric_paths[name].relative_to(PACKAGE_ROOT)),
            'sha256': input_hashes[name],
            'scope': metrics[name]['scope'],
        }
        for name in metric_paths
    },
    'metrics': df_adjudication.to_dict(orient='records'),
    'capacity_frontier': scale_df.to_dict(orient='records'),
    'resource_scaling': resource_scaling,
    'stress_tests': ooda['stress_tests'],
    'summary': {
        'pass': int((df_adjudication['status'] == 'PASS').sum()),
        'fail': int((df_adjudication['status'] == 'FAIL').sum()),
        'report_only': int((df_adjudication['status'] == 'REPORT_ONLY').sum()),
    },
    'claims_policy': claims_policy,
}
decision_json = VALIDATION_DIR / '指标裁决.json'
decision_json.write_text(json.dumps(decision_payload, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')

markdown_lines = [
    '# 智信 2026 新概念反无项目指标裁决',
    '',
    '> 由 Notebook 04 从 Notebook 01–03 本次输出自动生成；均非现场实测，也不是官方比赛评分。',
    '',
    '| 指标 | 值 | 单位 | 工程门槛 | 裁决 | 来源 |',
    '|---|---:|---|---|---|---|',
]
for row in df_adjudication.to_dict(orient='records'):
    markdown_lines.append(
        f"| {row['指标']} | {row['value']:.6g} | {row['unit']} | {row['工程门槛']} | {row['status']} | {row['source']} |"
    )
markdown_lines.extend([
    '',
    '## 规模容量边界',
    '',
    f"固定资源包在闭环使命 Pk 不低于 0.75 时的扫描前沿为 **N={ooda['capacity_frontier_threat_count_at_pk_0_75']}**。超过该规模的失败结果保留，不外推。",
    '',
    '### 同构资源增配（点估计门槛）',
    '',
    '| 威胁规模 | 动态反馈最少资源包 | 动态 Pk | Wilson 95% 下界 | 同资源静态 Pk | 静态规则最少资源包 |',
    '|---:|---:|---:|---:|---:|---:|',
])
for item in scaling_minimum:
    static_minimum = item['static_minimum_resource_packages']
    markdown_lines.append(
        f"| {item['threat_count']} | {item['adaptive_minimum_resource_packages']} | "
        f"{item['adaptive_pk_at_minimum']:.4f} | {item['adaptive_wilson_ci95_low_at_minimum']:.4f} | "
        f"{item['static_pk_at_same_packages']:.4f} | {static_minimum if static_minimum is not None else '>6'} |"
    )
markdown_lines.extend([
    '',
    '### 高可靠前沿（Pk>=0.95）',
    '',
    '| 威胁规模 | 动态反馈最少资源包 | 达标 Pk | 1–6 包内最佳 Pk | 最佳点资源包 |',
    '|---:|---:|---:|---:|---:|',
])
for item in high_reliability_minimum:
    minimum_packages = item['adaptive_minimum_resource_packages']
    pk_at_minimum = item['adaptive_pk_at_minimum']
    markdown_lines.append(
        f"| {item['threat_count']} | {minimum_packages if minimum_packages is not None else '>6'} | "
        f"{f'{pk_at_minimum:.4f}' if pk_at_minimum is not None else '未达到'} | "
        f"{item['best_available_adaptive_pk']:.4f} | {item['best_available_resource_packages']} |"
    )
markdown_lines.extend([
    '',
    '资源包只复制独立并行动作容量，不提高单次作用 Pk，也不缩短基础 OODA。协调感知主口径加入跨包同步、去冲突和指令编组时延；理想并行口径只作为容量上界。资源包数及行动成本不是采购报价。',
    '',
    '## 引用边界',
    '',
    '- HermiT/SHACL 结论只覆盖当前版本 TBox、ABox 和受控负向夹具。',
    '- OODA、蜂群 Pk、AUC 均是参数化固定种子仿真，非现场实测。',
    '- 容量前沿只适用于当前资源配置与 80% 失效使命定义。',
])
decision_md = VALIDATION_DIR / '指标裁决.md'
decision_md.write_text('\\n'.join(markdown_lines) + '\\n', encoding='utf-8')

print('指标裁决 JSON:', decision_json)
print('指标裁决说明:', decision_md)
print('裁决汇总:', decision_payload['summary'])
if decision_payload['summary']['fail']:
    raise AssertionError('存在未通过的内部工程门槛，详见指标裁决.json')
"""
        ),
        new_markdown_cell(
            """## 5. Effect → Action → Mission 写回复现

本节复现文字稿中的本体 Action 闭环：效果阈值和威胁/装备状态触发规则，自动动作更新一份会话状态副本，资源增配与批量授权进入人工审批队列，并输出独立 RDF 写回图。正式 OWL/ABox 文件保持只读。

这只是本地机制原型，不是 Palantir Foundry 部署、实时数据总线或真实装备控制。
"""
        ),
        new_code_cell(
            """import sys
from rdflib import Graph

APP_DIR = PACKAGE_ROOT / '03_源码' / 'streamlit_app'
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from utils.ontology_action_engine import (
    action_result_to_json,
    action_result_to_turtle,
    evaluate_action_feedback,
    load_baseline_operational_state,
)

action_state = load_baseline_operational_state()
action_state['priority'] = 3
action_metrics = {
    'detection_coverage': 0.88,
    'identification_accuracy': 0.83,
    'ooda_closure_time_s': 5.4,
    'interception_success_rate': 0.82,
    'false_alarm_rate': 0.025,
}
action_context = {
    'threat_level_previous': 3,
    'threat_level_current': 5,
    'failed_equipment_ids': ['Eq_EW_HPM_001'],
}
action_result = evaluate_action_feedback(
    action_metrics,
    action_context,
    action_state,
    generated_at_utc='2026-08-10T00:00:00+00:00',
)
action_turtle = action_result_to_turtle(action_result)
action_graph = Graph().parse(data=action_turtle, format='turtle')

assert action_result['summary'] == {
    'triggered_rules': 8,
    'auto_applied': 5,
    'pending_human_authorization': 3,
}
assert action_result['after_state']['priority'] == 5
assert action_result['after_state']['equipment_status']['Eq_EW_HPM_001'] == 'Failed'
assert action_result['canonical_model_mutated'] is False
assert action_result['not_palantir_foundry_deployment'] is True
assert len(action_graph) >= 50

action_json_path = VALIDATION_DIR / 'action_feedback_demo.json'
action_ttl_path = VALIDATION_DIR / 'action_feedback_writeback.ttl'
action_json_path.write_text(action_result_to_json(action_result), encoding='utf-8')
action_ttl_path.write_text(action_turtle, encoding='utf-8')

print('Action 决策:', action_result['decision_id'])
print('RDF 三元组:', len(action_graph))
print('JSON:', action_json_path)
print('TTL:', action_ttl_path)
pd.DataFrame(action_result['actions'])[
    ['rule_id', 'action_code', 'execution_status', 'description']
]
"""
        ),
        new_markdown_cell(
            """## 6. 结论

Notebook 04 汇总本次真实执行结果、锁定引用边界，并复现本体 Action 写回机制。出现失败时必须保留失败；只有在模型、参数、数据或代码真实改进并重新执行前三个 Notebook 后，指标裁决才会更新。
"""
        ),
    ]

    rebuilt = new_notebook(cells=cells, metadata=metadata)
    nbformat.write(rebuilt, NOTEBOOK_PATH)
    print(f"Rebuilt: {NOTEBOOK_PATH}")


if __name__ == "__main__":
    main()
