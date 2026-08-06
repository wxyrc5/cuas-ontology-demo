"""Page 1 – Home / 主页."""
import streamlit as st


def show() -> None:
    # Custom CSS — emphasizes 3 giant metrics
    st.markdown(
        """
        <style>
            .big-metric {
                font-size: 56px;
                font-weight: 900;
                color: #1F4E79;
                text-align: center;
                line-height: 1.1;
            }
            .big-metric-label {
                font-size: 16px;
                color: #555;
                text-align: center;
                margin-bottom: 8px;
            }
            .big-metric-delta {
                font-size: 14px;
                text-align: center;
                color: #2E7D32;
            }
            .hero {
                background: linear-gradient(135deg, #1F4E79 0%, #2E7D32 100%);
                color: white;
                padding: 30px;
                border-radius: 12px;
            }
            .hero h1 { color: white; }
            .badge {
                display: inline-block;
                padding: 4px 10px;
                border-radius: 6px;
                font-size: 12px;
                margin-right: 6px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # Hero
    # ------------------------------------------------------------------
    st.markdown(
        """
        <div class="hero">
            <h1>🛡️ 反无人机体系本体论 — 实时交互演示</h1>
            <p style="font-size:18px; margin-top:8px;">
              基于 Palantir Ontology 方法论构建的 <b>反蜂群机场防护杀伤网</b>。<br>
              现场体验本体推理 · 贝叶斯自适应 · OODA 闭环。
            </p>
            <p>
                <span class="badge" style="background:#FFD54F;color:#000">OSREDM 2026</span>
                <span class="badge" style="background:#FFFFFF;color:#1F4E79">赛道 7 · 新概念反无</span>
                <span class="badge" style="background:#81C784;color:#000">Palantir 风格</span>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("")

    # ------------------------------------------------------------------
    # 3 Big Metrics
    # ------------------------------------------------------------------
    st.header("🎯 三大核心指标")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="big-metric">0.9958</div>', unsafe_allow_html=True)
        st.markdown('<div class="big-metric-label">贝叶斯 AUC</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="big-metric-delta">▲ +0.428 vs 固定规则 0.567</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown('<div class="big-metric">&lt; 5s</div>', unsafe_allow_html=True)
        st.markdown('<div class="big-metric-label">OODA 闭环时延</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="big-metric-delta">vs 传统 10-15 秒 (-60%)</div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown('<div class="big-metric">8 + 10 + 4</div>', unsafe_allow_html=True)
        st.markdown('<div class="big-metric-label">本体规模</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="big-metric-delta">8 OT · 10 LT · 4 ST</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ------------------------------------------------------------------
    # Video placeholder
    # ------------------------------------------------------------------
    st.header("🎬 8 分钟精华视频")

    col_vid, col_caption = st.columns([3, 2])
    with col_vid:
        # Use a placeholder / open-source sample for demo.
        # In production this would point at our produced 8-minute showcase.
        st.video("https://www.youtube.com/watch?v=ScMzIvxBSi4")
    with col_caption:
        st.info(
            """
            📌 **视频要点**：
            1. 反蜂群机场威胁 (0:00)
            2. 本体论方法 (1:30)
            3. SPARQL 杀伤链推理 (3:00)
            4. 贝叶斯自适应实验 (4:30)
            5. PEK / BRU / MUC 仿真 (6:00)
            6. 总结与展望 (7:30)
            """
        )
        st.markdown(
            """
            > 视频无法播放时，请直接通过左侧导航浏览 **5 个交互页面**。
            """
        )

    st.markdown("---")

    # ------------------------------------------------------------------
    # Team
    # ------------------------------------------------------------------
    st.header("👥 团队介绍")

    members = [
        ("🎖️ 张致远", "首席科学家", "PhD · 雷达信号处理 10 年经验，主持 XX 重大项目。"),
        ("🛡️ 李梦琦", "本体架构师", "前 Palantir 工程师，8 OT + 10 LT 主设计者。"),
        ("📊 王思博", "贝叶斯算法负责人", "剑桥统计博士，Beta-Binomial 共轭模型主研。"),
        ("🗺 陈宇航", "仿真工程师", "MUC 机场反无集成负责人，6 年兵棋推演经验。"),
        ("🎨 赵子涵", "交互可视化设计师", "Streamlit + Plotly 交互界面全栈实现。"),
        ("📝 林清扬", "文档 & 答辩", "OSREDM 提案撰写人，赛队答辩主讲。"),
    ]

    cols = st.columns(3)
    for i, (name, role, intro) in enumerate(members):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"### {name}")
                st.markdown(f"**{role}**")
                st.write(intro)

    st.markdown("---")

    # ------------------------------------------------------------------
    # Competition CTA
    # ------------------------------------------------------------------
    st.header("🏆 报名 & 联系我们")

    cta_l, cta_r = st.columns(2)
    with cta_l:
        st.markdown(
            """
            ### 📮 OSREDM 2026 报名
            - 赛道 7 · 新概念反无
            - 报名截止：**2026-03-15**
            - 初赛：**2026-04-01**
            - 决赛：**2026-05-20 北京**

            👉 **报名链接**：https://osredm.example.org/register
            """
        )
        st.link_button(
            "👉 前往 OSREDM 官网",
            "https://osredm.example.org",
            use_container_width=True,
        )
    with cta_r:
        st.markdown(
            """
            ### 📬 联系我们
            - 邮箱：`c-uas-ontology@example.org`
            - GitHub：`github.com/cuas-ontology/cuas-osredm2026`
            - Slack：`cuas-osredm.slack.com`

            ### 🔬 技术合作
            我们诚邀 Palantir / Anduril 等公司本体工程师
            来信指导。
            """
        )
        st.button(
            "📨 发送邮件",
            use_container_width=True,
            help="mailto:c-uas-ontology@example.org",
        )

    st.markdown("---")
    st.caption("首页 · C-UAS Ontology Streamlit Demo · 2025")
