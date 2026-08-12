"""Competition-facing landing page for the canonical C-UAS demo."""
from __future__ import annotations

import streamlit as st

from utils.current_metrics import load_current_metrics


st.set_page_config(
    page_title="智盾 · 反无任务编排与验证台",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

metrics = load_current_metrics()
bayes = metrics["bayesian"]
ooda = metrics["ooda"]
ontology = metrics["ontology"]
acceptance = metrics["acceptance"]

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.7rem; padding-bottom: 2rem;}
      .hero {padding: 1.35rem 1.55rem; border: 1px solid #d9e2ec; border-radius: 18px;
             background: linear-gradient(135deg,#f6fbff 0%,#eef5fb 55%,#f9fbfd 100%);}
      .hero-kicker {font-size:.84rem; color:#355b7d; letter-spacing:.12em; font-weight:700;}
      .hero h1 {font-size:2.05rem; line-height:1.25; color:#0b2545; margin:.35rem 0 .5rem;}
      .hero p {font-size:1.03rem; color:#334e68; margin:0; max-width:980px;}
      .act {padding:1rem 1.05rem; min-height:150px; border:1px solid #d9e2ec;
            border-radius:14px; background:#fff;}
      .act b {color:#0b2545; font-size:1.05rem;}
      .act small {color:#627d98;}
      .boundary {padding:.8rem 1rem; border-left:5px solid #d29b2f; background:#fff8e8;
                 border-radius:8px; color:#5c4616;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.title("🛡️ 智盾演示台")
st.sidebar.markdown("**反无任务编排与验证原型**")
st.sidebar.success("当前状态：可现场演示、可本地复现、可接入扩展")
st.sidebar.info("所有概率、时延和资源结果均为参数化合成仿真，不是机场现场或装备实测。")
st.sidebar.page_link("pages/0_🎬_专家演示.py", label="进入专家演示模式", icon="🎬", width="stretch")
st.sidebar.markdown("### 本轮可核验证据")
left, right = st.sidebar.columns(2)
left.metric("形式模型", ontology["verdict"], "HermiT + SHACL")
right.metric(
    "Notebook",
    f"{acceptance['notebook_executed_code_cells']}/{acceptance['notebook_code_cells']}",
    "代码单元通过",
)
left.metric("页面验收", f"{acceptance['streamlit_pages_passed']}/{acceptance['streamlit_pages']}")
right.metric("贝叶斯 AUC", f"{bayes['auc']:.3f}", f"固定规则 {bayes['fixed_rule_auc']:.3f}")
st.sidebar.markdown("---")
st.sidebar.markdown("**智信—2026 无人智能挑战赛**  \n创意类 · 科目 7 新概念反无")
st.sidebar.link_button("赛事官网", "https://www.osredm.com/competition/ZX2026", width="stretch")

st.markdown(
    """
    <section class="hero">
      <div class="hero-kicker">智信—2026 · 创意类 · 科目 7</div>
      <h1>智盾：让异构反无能力在同一任务语义下协同</h1>
      <p>重点场所真正缺少的，不是又一台孤立设备，而是一套能把传感、规则、人工授权、效应器和效果反馈组织成可解释闭环的决策底座。</p>
    </section>
    """,
    unsafe_allow_html=True,
)

st.caption("产品形态：本地可运行的任务编排与数字化试验台｜核心机制：本体 + 贝叶斯反馈 + 全链路 OODA + 同源二维/三维态势")

c1, c2, c3, c4 = st.columns(4)
c1.metric("20 机闭环使命 Pk", f"{ooda['swarm_20']['closed_loop_pk']:.3f}", "固定资源，Wilson 下界≥0.75")
c2.metric("HPM 闭环 P90", f"{ooda['hpm_20']['full_loop_p90_s']:.2f} s", "含传感、授权、效应、反馈")
c3.metric("同预算 AUC 增量", f"+{bayes['auc_delta']:.3f}", "相对固定规则")
c4.metric("固定资源规模前沿", f"N={ooda['capacity_frontier_n_at_pk_0_75']}", "25 机起需资源扩容")

st.markdown("## 评委只需记住四幕")
cols = st.columns(4)
cards = [
    ("01 看见", "多源态势同源", "离线地图、连续轨迹、二维/三维同一状态，先把威胁看清。"),
    ("02 看懂", "任务语义可追溯", "从使命追到威胁、资产、能力、装备、人员和指标，回答“为什么”。"),
    ("03 处置", "约束下动态编排", "把人工授权、射界、通道容量和效应器时延放进完整 OODA。"),
    ("04 进化", "效果反馈驱动迭代", "处置结果写回指标；贝叶斯飞轮持续更新，同预算优于固定规则。"),
]
for column, (number, title, text) in zip(cols, cards):
    with column:
        st.markdown(
            f'<div class="act"><small>{number}</small><br><b>{title}</b><p>{text}</p></div>',
            unsafe_allow_html=True,
        )

st.markdown("## 一个现场故事")
story, product = st.columns([1.7, 1])
with story:
    st.markdown(
        """
        **场景：20 架低慢小目标逼近重点场所。** 系统先将多源观测关联为威胁对象，
        再依据保护资产、交战规则和可用能力生成任务链；人工完成批次授权后，
        动态反馈策略在通道与时间约束下分配效应器，并把结果回写为下一轮证据。

        评委可以继续把规模提升到 25–100 机，看到固定资源何时失效、增加几个同构资源包后重新达标，
        以及跨包同步时延如何侵蚀理想并行收益。失败不是被隐藏，而是直接变成资源规划边界。
        """
    )
    st.page_link("pages/0_🎬_专家演示.py", label="启动 8 分钟专家演示路径", icon="🎬", width="stretch")
with product:
    st.markdown("**好产品**：一套可运行的反无任务编排与验证台")
    st.markdown("**好创意**：把本体从知识图谱变成可执行、可回写的任务契约")
    st.markdown("**快速转化**：通过数据契约与适配器接入传感器、C2 和效应器，而非推倒重建")
    st.markdown("**可审计**：结论、假设、失败工况和版本均有机器可读证据")

st.markdown("## 从比赛原型到应用验证")
roadmap = st.columns(4)
for column, title, body in [
    (roadmap[0], "P0 可演示原型", "本体、查询、飞轮、OODA、蜂群裁决、2D/3D 已贯通。"),
    (roadmap[1], "P1 数据回放", "接入脱敏雷达/RF/光电日志，建立时间同步和偏差报告。"),
    (roadmap[2], "P2 半实物闭环", "校准竞争链路、人工授权、射界与效应器参数。"),
    (roadmap[3], "P3 场景试点", "在合规条件下开展专家工作坊、红蓝压测与小规模场试。"),
]:
    with column:
        st.markdown(f"**{title}**")
        st.caption(body)

st.markdown(
    "<div class='boundary'><b>证据边界：</b>当前证明的是软件体系、形式模型和参数化试验方法可运行、可复现；不宣称真实装备接入、现场识别率、物理拦截效能、Palantir Foundry 部署、SWRL 执行或已完成专家/红蓝实测。</div>",
    unsafe_allow_html=True,
)
st.caption("智盾 · 反无任务编排与验证台｜指标快照由本地验收流程生成")
