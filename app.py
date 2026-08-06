"""Streamlit multi-page C-UAS demo application."""
import streamlit as st

# ---------------------------------------------------------------------------
# Page configuration (MUST be the first Streamlit command)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="C-UAS Ontology 演示",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("🛡️ C-UAS Ontology")
st.sidebar.markdown(
    "**基于 Palantir 本体论的反蜂群机场防护杀伤网**"
)
st.sidebar.markdown("---")

st.sidebar.markdown("### 📑 快速导航")
st.sidebar.markdown(
    """
    - 🏠 [主页](#)
    - 🧬 [本体浏览](#)
    - 🔍 [SPARQL 查询](#)
    - 📊 [贝叶斯实验](#)
    - 🗺 [机场反无](#)
    """
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 关键指标")

c1, c2 = st.sidebar.columns(2)
c1.metric("贝叶斯 AUC", "0.9958", "+0.428")
c2.metric("OODA 闭环", "< 5s", "vs 10-15s")
c1.metric("本体规模", "8 OT", "")
c2.metric("链路规模", "10 LT", "")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🏆 比赛")
st.sidebar.markdown(
    """
    **OSREDM 2026** · 7 号赛道 · 新概念反无
    参赛组：C-UAS Ontology Group
    """
)
st.sidebar.markdown("[🌐 报名链接](https://osredm.example.org)")

# ---------------------------------------------------------------------------
# Page routing
# ---------------------------------------------------------------------------
PAGES = {
    "🏠 主页":            "home",
    "🧬 本体浏览":        "ontology",
    "🔍 SPARQL 查询":     "sparql",
    "📊 贝叶斯实验":      "bayes",
    "🗺 机场反无":         "airport",
}

with st.sidebar:
    page_label = st.radio(
        "选择页面",
        list(PAGES.keys()),
        index=0,
        label_visibility="collapsed",
    )
    st.session_state.current_page = PAGES[page_label]

# ---------------------------------------------------------------------------
# Friendly launcher (rather than expecting the framework's multipage routing)
# ---------------------------------------------------------------------------
st.title("🛡️ 反无人机体系本体 — 实时演示")

st.success(
    f"**欢迎进入 C-UAS Ontology 演示应用！** 当前页面：**{page_label}**。"
)

st.markdown("---")

# Brief intro card
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.markdown(
        """
        ### 🎯 核心目标
        现场演示我们的 **Palantir 风格反无人机本体论**。
        用 5 个页面让评委亲手操作：
        - 浏览 8 OT + 10 LT
        - 跑 SPARQL 推理杀伤链
        - 玩转贝叶斯自适应参数
        - 仿真机场反蜂群决策
        """
    )
with col_b:
    st.markdown(
        """
        ### 🧬 技术亮点
        - **Palantir Ontology** 8 OT + 10 LT + 4 ST
        - **Beta-Binomial** 共轭自适应
        - **OODA** < 5 s 闭环
        - **AUC** 0.9958（+0.428 提升）
        - **Plotly** 交互图 + rdflib SPARQL
        """
    )
with col_c:
    st.markdown(
        """
        ### 🚀 开始演示
        在 **左侧菜单** 选择页面，或点击下方按钮一键跳转：
        """
    )
    nav_choice = st.radio(
        "快速进入",
        list(PAGES.keys()),
        label_visibility="collapsed",
    )
    if st.button("➡️ 进入选中的页面", use_container_width=True):
        st.session_state.current_page = PAGES[nav_choice]
        st.success(f"已切换到：{nav_choice}")
        st.info(
            "💡 提示：在多页应用模式下，请直接通过 **侧边栏页面切换器** "
            "或使用浏览器左侧的 `pages/` 列表。"
        )

st.markdown("---")

# Recommendation block
st.markdown(
    """
    ### 📍 推荐演示顺序
    1. **🧬 本体浏览** — 先了解我们的本体论基础架构。
    2. **🔍 SPARQL 查询** — 看如何用语义推理找出杀伤链。
    3. **📊 贝叶斯实验** — 拖动滑块感受 AUC 实时变化。
    4. **🗺 机场反无** — 仿真 PEK / BRU / MUC 三大场景。

    > 或直接运行 `streamlit run demo_mode.py` 进入 30 分钟精华自动演示模式。
    """
)

st.markdown("---")
st.caption(
    "© 2025 OSREDM C-UAS Ontology Group · Streamlit 1.61 · Plotly 6.0 · rdflib 7.0"
)
