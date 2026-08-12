"""Project overview backed by the current audited metric snapshot."""
from __future__ import annotations

import streamlit as st

from utils.current_metrics import load_current_metrics


def show() -> None:
    metrics = load_current_metrics()
    bayes = metrics["bayesian"]
    ooda = metrics["ooda"]
    ontology = metrics["ontology"]
    acceptance = metrics["acceptance"]

    st.title("🛡️ 语义驱动的反无人机决策与验证原型")
    st.markdown(
        "面向机场等重要场所，把 **Mission—Scenario—Capability—Equipment—Effect** "
        "组织成可查询、可追溯、可复现的数字链路。"
    )
    st.warning(
        "本页只展示当前机器裁决结果。所有 AUC、P_k 和时延均来自固定种子合成仿真，"
        "不是现场测试或实装武器效能。"
    )

    st.header("本次可复现结果")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("贝叶斯同预算 AUC", f"{bayes['auc']:.4f}", f"固定规则 {bayes['fixed_rule_auc']:.4f}")
    col2.metric("20 机闭环使命 Pk", f"{ooda['swarm_20']['closed_loop_pk']:.3f}", "Wilson 下界 ≥ 0.75")
    col3.metric("本体一致性", ontology["verdict"], "HermiT + SHACL")
    col4.metric(
        "Notebook 代码单元",
        f"{acceptance['notebook_executed_code_cells']}/{acceptance['notebook_code_cells']}",
        "全量执行通过",
    )

    st.markdown("---")
    left, right = st.columns(2)
    with left:
        st.subheader("🧬 本体与查询范围")
        st.markdown(
            f"""
            - 核心模型：**8 Object Type + 10 Link Type**；
            - TBox / 正向 ABox：**{ontology['tbox_triples']} / {ontology['valid_abox_triples']} triples**；
            - HermiT 正向可满足性：**{ontology['checks']['hermit_positive_consistent']}**；
            - HermiT 互斥类型负向对照：**{ontology['checks']['hermit_disjointness_negative_control_rejected']}**；
            - SHACL 正向通过，受控负向违规准确检出 **{ontology['shacl_negative_violation_count']}** 项。
            """
        )
        st.caption("SWRL 执行正确性与真实专家标注不在本轮形式一致性范围内。")

    with right:
        st.subheader("📊 全链路 OODA 与蜂群容量")
        hpm = ooda["hpm_20"]
        swarm = ooda["swarm_20"]
        st.metric("20 机 HPM 完整闭环 P90", f"{hpm['full_loop_p90_s']:.2f} s", f"P(<5s)={hpm['probability_under_5s']:.1%}")
        st.metric("20 机动态反馈闭环 Pk", f"{swarm['closed_loop_pk']:.3f}", f"95% CI [{swarm['wilson_ci95'][0]:.3f}, {swarm['wilson_ci95'][1]:.3f}]")
        st.metric("同资源静态覆盖表 Pk", f"{swarm['static_closed_loop_pk']:.3f}", "覆盖优先、目标表冻结、无效果反馈")
        st.metric("单资源包 Pk≥0.75 前沿", f"N={ooda['capacity_frontier_n_at_pk_0_75']}", "更大规模必须增配资源")
        st.caption(
            "时延表显式包含传感扫描、通信、融合识别、人工授权、目标分配、瞄准、效应到达与 BDA；参数仍是工程假设，非现场实测。"
        )

    scaling = ooda["resource_scaling"]
    with st.expander("查看 20–100 机协调感知资源前沿（正式 Notebook 结果）", expanded=True):
        scaling_rows = []
        high_reliability = {
            int(item["threat_count"]): item["adaptive_minimum_resource_packages"]
            for item in scaling["high_reliability_minimum_packages"]
        }
        for item in scaling["minimum_packages"]:
            static_packages = item["static_minimum_resource_packages"]
            reliable_packages = high_reliability[int(item["threat_count"])]
            scaling_rows.append(
                {
                    "威胁规模 N": item["threat_count"],
                    "动态反馈最少资源包": item["adaptive_minimum_resource_packages"],
                    "动态 Pk": item["adaptive_pk_at_minimum"],
                    "95% CI 下界": item["adaptive_wilson_ci95_low_at_minimum"],
                    "Pk≥0.95 最少资源包": (
                        str(reliable_packages) if reliable_packages is not None else ">6"
                    ),
                    "同资源静态 Pk": item["static_pk_at_same_packages"],
                    "静态规则达标所需": str(static_packages) if static_packages is not None else ">6",
                }
            )
        st.dataframe(
            scaling_rows,
            width="stretch",
            hide_index=True,
            column_config={
                "动态 Pk": st.column_config.NumberColumn(format="%.3f"),
                "95% CI 下界": st.column_config.NumberColumn(format="%.3f"),
                "同资源静态 Pk": st.column_config.NumberColumn(format="%.3f"),
            },
        )
        st.caption(
            "资源包只复制并行动作容量，不提高单次作用 Pk，也不缩短基础 OODA；"
            "主口径加入跨包同步、去冲突和指令编组时延，理想并行结果只作为上界。"
            "每格 3,000 次共同随机数仿真；资源包数和行动成本不是采购报价。"
        )

    st.markdown("---")
    st.subheader("🗺️ 正式演示路径")
    st.markdown(
        """
        1. **本体浏览**：查看对象类型、链路类型和样例关系；
        2. **SPARQL 查询**：运行预设或自定义查询；
        3. **贝叶斯实验**：操作参数化合成实验，结果与正式裁决分开标识；
        4. **机场反无**：PKX/BRU/MUC 离线底图，二维与三维共享同一连续航迹、拦截事件与各向异性防御包络。
        """
    )
    st.info("本轮以交互应用和四个可复现 Notebook 为技术证据；申报书、PPT 与视频暂不在本轮更新范围内。")

    st.subheader("🏆 赛事与赛队信息")
    st.markdown(
        "赛题：**智信—2026 无人智能挑战赛 · 创意类 · 7. 新概念反无**。  \n"
        "赛队名称、成员和联系方式以最终签字/盖章报名表为准，当前应用不展示未经确认的个人信息。"
    )
    st.link_button(
        "查看赛事官网",
        "https://www.osredm.com/competition/ZX2026",
        width="stretch",
    )
    st.caption("主页 · 指标来源：验证输出/指标裁决.json 与本次验收报告")


show()
