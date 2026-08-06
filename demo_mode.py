"""Demo Mode – 30 分钟精华自动演示.

进入后，按一个按钮即可从 主页 → 本体浏览 → SPARQL → 贝叶斯 → 机场反无 顺序
依次跳转到对应页面。  内置 **自动播放** 选项，按 8 分钟精华视频节奏跳转。
"""
from __future__ import annotations

import time

import streamlit as st


PAGES = [
    {"key": "home",      "label": "🏠 主页",            "duration_s": 60,
     "summary": "30 秒项目介绍 + 3 大指标 (AUC 0.9958, OODA <5s, 8 OT + 10 LT)"},
    {"key": "ontology",  "label": "🧬 本体浏览",         "duration_s": 180,
     "summary": "3 分钟浏览 8 个 OT 卡片 + 10 个 LT 网络图，点开实例"},
    {"key": "sparql",    "label": "🔍 SPARQL 查询",      "duration_s": 240,
     "summary": "4 分钟运行 5 个内置模板查询 + 1 个自定义查询"},
    {"key": "bayes",     "label": "📊 贝叶斯实验",       "duration_s": 240,
     "summary": "4 分钟跑贝叶斯自适应实验 + ROC + 收敛速度"},
    {"key": "airport",   "label": "🗺 机场反无",          "duration_s": 240,
     "summary": "4 分钟 PEK/BRU/MUC 三大机场仿真 + OODA 瀑布"},
]
TOTAL_SECONDS = sum(p["duration_s"] for p in PAGES)   # 960 s ≈ 16 min condensed

st.set_page_config(
    page_title="C-UAS · Demo Mode",
    page_icon="🎬",
    layout="wide",
)


def main() -> None:
    st.title("🎬 自动演示模式（30 分钟精华版）")
    st.markdown(
        """
        按照专家建议的演示流程，**一键** 跳转到每个核心页面。
        在每个页面上，**停留合理时长** 给评委提问、互动。
        """
    )

    # ------------------------------------------------------------------
    # Top metrics row
    # ------------------------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总时长", f"{TOTAL_SECONDS//60} 分 {TOTAL_SECONDS%60} 秒")
    c2.metric("页面数", len(PAGES))
    c3.metric("核心指标", "AUC 0.9958")
    c4.metric("OODA", "< 5s")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Side selector
    # ------------------------------------------------------------------
    col_l, col_r = st.columns([2, 1])

    with col_l:
        st.subheader("📜 演示剧本")

        if "step" not in st.session_state:
            st.session_state["step"] = 0
        if "history" not in st.session_state:
            st.session_state["history"] = []

        for i, p in enumerate(PAGES):
            marker = "✅" if i < st.session_state["step"] else ("▶️" if i == st.session_state["step"] else "⏳")
            st.markdown(
                f"""
                <div style="border-left:5px solid #1F4E79; padding:12px; margin:8px 0;
                            background:#F4F6FA; border-radius:6px;">
                    <b>{marker} {i+1}. {p['label']}</b> · 停留 <b>{p['duration_s']} s</b><br>
                    <span style="color:#555;">{p['summary']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("---")

        ctrl_l, ctrl_m, ctrl_r = st.columns(3)
        prev_clicked = ctrl_l.button("⏮ 上一页", use_container_width=True)
        next_clicked = ctrl_m.button("⏭ 下一页", type="primary", use_container_width=True)
        reset_clicked = ctrl_r.button("🔄 重置", use_container_width=True)

        if reset_clicked:
            st.session_state["step"] = 0
            st.session_state["history"] = []
            st.success("🔄 已重置剧本。")
            st.rerun()

        if prev_clicked:
            st.session_state["step"] = max(0, st.session_state["step"] - 1)
            st.rerun()

        if next_clicked:
            step_now = st.session_state["step"]
            st.session_state["history"].append(PAGES[step_now]["label"])
            if step_now + 1 < len(PAGES):
                st.session_state["step"] = step_now + 1
            else:
                st.success("🎉 已完成全部页面！")
            st.rerun()

    with col_r:
        st.subheader("🎯 跳转")

        cur = PAGES[st.session_state["step"]]
        st.markdown(
            f"""
            ### 当前：{cur['label']}

            **{cur['summary']}**

            **建议在此页面演示**：
            """
        )
        if cur["key"] == "home":
            st.markdown(
                """
                1. 突出 **三大指标** (AUC / OODA / 8+10+4)
                2. 播放 **8 分钟精华视频**
                3. 介绍 **团队成员**
                """
            )
        elif cur["key"] == "ontology":
            st.markdown(
                """
                1. 点击 **8 OT 卡片** 逐个介绍
                2. 展开 **10 LT 网络图**
                3. 选择一个 OT 显示 **实例表**
                """
            )
        elif cur["key"] == "sparql":
            st.markdown(
                """
                1. 运行 **反蜂群** 模板查询
                2. 切换为 **机场防护** 模板
                3. 修改自定义查询
                """
            )
        elif cur["key"] == "bayes":
            st.markdown(
                """
                1. 点击 **预设场景** → 4 个一键加载
                2. 调整 **滑块** 看 AUC 实时变化
                3. 展示 **ROC + 收敛曲线**
                """
            )
        elif cur["key"] == "airport":
            st.markdown(
                """
                1. 切换 **PEK / BRU / MUC**
                2. 滑块从 5 → 50 无人机
                3. 动画帧播放、效应器组合
                """
            )

        # Direct jump buttons for every page
        st.markdown("---")
        st.markdown("**一键跳转：**")
        for p in PAGES:
            if st.button(p["label"], key=f"jump_{p['key']}", use_container_width=True):
                st.session_state["step"] = next(
                    i for i, pp in enumerate(PAGES) if pp["key"] == p["key"]
                )
                st.info(f"➡️ 已选中 {p['label']} — 请使用左侧 Streamlit 多页导航切换。")

        st.markdown("---")
        st.markdown("### 📜 历史")
        if st.session_state["history"]:
            for h in st.session_state["history"][-5:]:
                st.markdown(f"- {h}")
        else:
            st.caption("(未开始)")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Auto play mode
    # ------------------------------------------------------------------
    st.subheader("⏯ 自动播放模式")
    ap1, ap2 = st.columns([1, 3])
    with ap1:
        auto = st.button("▶ 开始自动播放", type="primary", use_container_width=True)
        stop = st.button("⏹ 停止", use_container_width=True)
    with ap2:
        st.caption(
            "自动模式会模拟一个 Streamlit 多页跳转的效果（重定向到对应页面）。"
            "Streamlit 多页应用模式下，**跳转实际通过左侧导航栏实现**。"
        )

    if auto and not stop:
        with st.spinner("自动播放中..."):
            for i, p in enumerate(PAGES):
                st.session_state["step"] = i
                progress = (i + 1) / len(PAGES)
                st.progress(progress, text=f"▶ {p['label']} ({p['duration_s']}s)")
                time.sleep(min(2, p["duration_s"] // 4))   # speed up: real demo takes 30 min, we condense to ~30s
            st.success("🎉 自动演示完成！")

    st.markdown("---")
    st.caption("Demo Mode · 自动播放 30 分钟精华 / 压缩到 ~30 秒演示 · C-UAS Ontology")


if __name__ == "__main__":
    main()
