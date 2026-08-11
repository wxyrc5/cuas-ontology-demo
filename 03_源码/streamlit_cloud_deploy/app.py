"""Canonical landing page for the C-UAS competition demo."""
from __future__ import annotations

import streamlit as st

from utils.current_metrics import load_current_metrics


st.set_page_config(
    page_title="智信 2026 · 新概念反无",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

metrics = load_current_metrics()
bayes = metrics["bayesian"]
ooda = metrics["ooda"]
ontology = metrics["ontology"]
acceptance = metrics["acceptance"]

st.sidebar.title("🛡️ C-UAS Ontology")
st.sidebar.markdown("**面向重要场所的语义驱动反无人机决策与验证原型**")
st.sidebar.info("所有数值均为固定种子合成仿真或本机验收结果，不是机场现场实测。")
st.sidebar.markdown("### 本次可复现状态")
left, right = st.sidebar.columns(2)
left.metric("贝叶斯 AUC", f"{bayes['auc']:.4f}", f"Δ {bayes['auc_delta']:+.3f}")
right.metric(
    "Notebook",
    f"{acceptance['notebook_executed_code_cells']}/{acceptance['notebook_code_cells']}",
    "代码单元通过",
)
left.metric("形式一致性", ontology["verdict"], "HermiT + SHACL")
right.metric(
    "应用入口",
    f"{acceptance['streamlit_pages_passed']}/{acceptance['streamlit_pages']}",
    "AppTest 通过",
)
st.sidebar.markdown("---")
st.sidebar.markdown("**智信—2026 无人智能挑战赛**  \n创意类 · 7. 新概念反无")
st.sidebar.link_button(
    "赛事官网",
    "https://www.osredm.com/competition/ZX2026",
    width="stretch",
)

st.title("🛡️ 反无人机体系本体与机场防护决策演示")
st.caption("唯一主线：正式 TBox/ABox · 五通道贝叶斯飞轮 · 全链路 OODA · PKX/BRU/MUC 同源防御包络")

st.warning(
    "证据边界：当前原型验证的是语义建模、查询、合成决策链和可视化流程。"
    "P_k、AUC 与时延均不得表述为实装武器效能或机场现场测试结果。"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("贝叶斯同预算 AUC", f"{bayes['auc']:.4f}", f"固定规则 {bayes['fixed_rule_auc']:.4f}")
c2.metric("20 机闭环使命 Pk", f"{ooda['swarm_20']['closed_loop_pk']:.3f}", "Wilson 下界 ≥ 0.75")
c3.metric("HPM 完整闭环 P90", f"{ooda['hpm_20']['full_loop_p90_s']:.2f} s", "含传感/授权/效应/BDA")
c4.metric("固定资源规模前沿", f"N={ooda['capacity_frontier_n_at_pk_0_75']}", "Pk ≥ 0.75")

st.markdown("---")
goal, evidence, demo = st.columns(3)
with goal:
    st.subheader("🎯 解决什么问题")
    st.markdown(
        """
        - 异构探测、识别、决策与处置数据缺少共同语义；
        - 任务—场景—能力—装备—效果之间难以追溯；
        - 二维、三维和统计结果容易因多版本而相互矛盾。
        """
    )
with evidence:
    st.subheader("🧬 当前实现")
    st.markdown(
        """
        - 8 个 Object Type、10 个 Link Type；
        - HermiT/SHACL 正负向一致性验证与真实 ABox SPARQL；
        - 五通道 Beta-Binomial 飞轮及同预算固定规则 AUC；
        - 全链路 OODA 与资源约束蜂群裁决；
        - PKX/BRU/MUC 离线地图、连续三波次航迹与三维防御包络；
        - Jupyter 一键重跑和机器可读指标裁决。
        """
    )
with demo:
    st.subheader("🚀 推荐演示顺序")
    st.markdown(
        """
        1. **本体浏览**：查看 8 OT + 10 LT；
        2. **SPARQL 查询**：追踪任务关系；
        3. **贝叶斯实验**：观察参数化合成结果；
        4. **机场反无**：对照二维/三维同源态势。
        """
    )

st.markdown("---")
st.subheader("⚠️ 当前证据边界与剩余工作")
for gap in metrics["known_gaps"]:
    st.markdown(f"- {gap}")

st.success(
    "主应用、5 个功能页面、离线地图和四个规范 Notebook 已在本机通过当前轮验收。"
    "最终申报材料仍需用本次指标裁决逐项回填。"
)
st.caption("智信 2026 · 赛题 7 新概念反无 · 指标快照由本地验收流程生成")
