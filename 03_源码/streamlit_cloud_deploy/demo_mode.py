"""A concise, evidence-scoped cue sheet for a live competition demo."""
from __future__ import annotations

import streamlit as st

from utils.current_metrics import load_current_metrics


PAGES = [
    {
        "label": "🏠 主页",
        "path": "pages/1_🏠_主页.py",
        "minutes": 1,
        "summary": "先说明合成/非现场证据边界与本次验收状态。",
    },
    {
        "label": "🧬 本体浏览",
        "path": "pages/2_🧬_本体浏览.py",
        "minutes": 2,
        "summary": "演示 8 OT、10 LT、样例实例与任务关系。",
    },
    {
        "label": "🔍 SPARQL 查询",
        "path": "pages/3_🔍_SPARQL查询.py",
        "minutes": 2,
        "summary": "运行预设查询，再改一处条件展示可追溯性。",
    },
    {
        "label": "📊 贝叶斯实验",
        "path": "pages/4_📊_贝叶斯实验.py",
        "minutes": 3,
        "summary": "说明交互页是参数化合成实验，正式引用值来自 Notebook 03。",
    },
    {
        "label": "🗺 机场反无",
        "path": "pages/5_🗺_机场反无.py",
        "minutes": 4,
        "summary": "展示 PKX 离线地图、连续三波次航迹及二维/三维同源拦截事件。",
    },
]


def main() -> None:
    st.set_page_config(page_title="C-UAS · 演示提词", page_icon="🎬", layout="wide")
    metrics = load_current_metrics()
    acceptance = metrics["acceptance"]

    st.title("🎬 现场演示提词页")
    st.info(
        "建议总时长约 12 分钟。该页面只负责提词和真实跳转，不自动播放，"
        "避免答辩现场因定时器或页面状态失控。"
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("建议时长", f"{sum(item['minutes'] for item in PAGES)} 分钟")
    c2.metric(
        "Notebook",
        f"{acceptance['notebook_executed_code_cells']}/{acceptance['notebook_code_cells']}",
        "本次执行通过",
    )
    c3.metric(
        "应用入口",
        f"{acceptance['streamlit_pages_passed']}/{acceptance['streamlit_pages']}",
        "本次 AppTest 通过",
    )

    st.warning(
        "答辩中不得把 AUC、P_k 或时延说成机场现场实测；"
        f"当前固定资源在 20 机达标，Pk≥0.75 的扫描前沿为 N={metrics['ooda']['capacity_frontier_n_at_pk_0_75']}；"
        "25 机及以上只有在另行声明的同构资源增配假设下才重新达标。"
    )

    for index, item in enumerate(PAGES, start=1):
        with st.container(border=True):
            left, right = st.columns([4, 1])
            with left:
                st.subheader(f"{index}. {item['label']} · {item['minutes']} 分钟")
                st.write(item["summary"])
            with right:
                st.page_link(item["path"], label="进入页面", icon="➡️", width="stretch")

    st.subheader("结束语")
    st.markdown(
        "当前成果是一个可运行、可复现、可追溯的原型，已完成 HermiT/SHACL 形式验证、"
        "20 机资源约束闭环裁决、20–100 机协调感知资源前沿与五通道贝叶斯对照。"
        "下一阶段应优先做参数标定、真实竞争链路和跨阵地台架验证。"
    )
    st.caption("演示提词页 · 当前指标来自 current_metrics.json")


if __name__ == "__main__":
    main()
