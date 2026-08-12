"""Judge-facing guided route for the live ZX2026 demonstration."""
from __future__ import annotations

import streamlit as st

from utils.current_metrics import load_current_metrics


ACTS = [
    {
        "name": "第一幕 · 看见",
        "time": "0:20–0:55",
        "path": "pages/5_🗺_机场反无.py",
        "icon": "🗺️",
        "action": "打开 PKX 二维态势，再切换三维和语义事件日志；指出非圆防御包络、20 机连续航迹和同源状态。",
        "claim": "我们先解决‘态势能否可信展示’：地图离线、轨迹连续、二维三维不再各演各的。",
        "evidence": "PKX/BRU/MUC 各 3 层防御包络；20×60 帧；二维/三维 20 个目标逐一同源。",
    },
    {
        "name": "第二幕 · 看懂",
        "time": "0:55–2:00",
        "path": "pages/2_🧬_本体浏览.py",
        "icon": "🧬",
        "action": "先演示 16 条声明热插拔，再展示 Mission 主链、一致性图和 HPM 失败逆向复盘。",
        "claim": "本体不是静态词典，而是可插拔的任务合同和失败复盘索引。",
        "evidence": "原查询发现新装备且 SHACL 通过；8/10 + 3/6；TBox+ABox 653 triples；根因候选不冒充因果效应。",
    },
    {
        "name": "第三幕 · 处置",
        "time": "2:00–3:30",
        "path": "pages/2_🧬_本体浏览.py",
        "icon": "🎯",
        "action": "展示 L1/L2/L3、20 目标 WTA，再解释设计态/运行态分离与完整 OODA、20 机裁决。",
        "claim": "决策不是‘看到就打’，而是在授权、射界、容量和完整 OODA 时限内选择可执行链路。",
        "evidence": "WTA 三类约束通过；20 机闭环 Pk=0.7655；HPM P90=3.670 s；100 机点估计达标需 5 包。",
    },
    {
        "name": "第四幕 · 进化",
        "time": "3:30–4:05",
        "path": "pages/4_📊_贝叶斯实验.py",
        "icon": "📈",
        "action": "展示五通道后验、同预算固定规则对照，以及主雷达失效—备份重构反事实。",
        "claim": "系统不是一次性规则表，而是处置一次、积累一次证据、修正一次资源与阈值。",
        "evidence": "贝叶斯 AUC=0.9679，固定规则=0.8688；反事实路径由当前 RDF 图解析。",
    },
]


def main() -> None:
    st.set_page_config(page_title="智盾 · 专家演示模式", page_icon="🎬", layout="wide")
    metrics = load_current_metrics()
    acceptance = metrics["acceptance"]

    st.title("🎬 初筛演示模式：4 分 30 秒讲清一个好产品")
    st.caption("昆仑智镜（KunLun MirAI）")
    st.info(
        "主线只有一句：把异构传感、规则、人工授权和效应器编排成可解释、可复盘、可迭代的反无任务闭环。"
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("演示结构", "4 幕", "看见—看懂—处置—进化")
    c2.metric("形式模型", metrics["ontology"]["verdict"], "HermiT + SHACL")
    c3.metric("Notebook", f"{acceptance['notebook_executed_code_cells']}/{acceptance['notebook_code_cells']}")
    c4.metric("页面验收", f"{acceptance['streamlit_pages_passed']}/{acceptance['streamlit_pages']}")

    st.markdown("### 0:00–0:20｜先抛出矛盾")
    st.markdown(
        "> 20 架低慢小目标同时逼近重点场所。单点设备可以报警，但谁来把多源观测、交战规则、人工授权和有限效应器在 5 秒内组织成一条能解释、能复盘的处置链？这就是智盾要解决的问题。"
    )

    for index, act in enumerate(ACTS, start=1):
        with st.container(border=True):
            head, jump = st.columns([5, 1])
            with head:
                st.subheader(f"{act['icon']} {act['name']}｜{act['time']}")
            with jump:
                if st.button("➡️ 进入演示", key=f"jump_{index}", width="stretch"):
                    st.switch_page(act["path"])
            a, b, c = st.columns(3)
            with a:
                st.markdown("**现场动作**")
                st.write(act["action"])
            with b:
                st.markdown("**只讲一句**")
                st.write(act["claim"])
            with c:
                st.markdown("**落到证据**")
                st.write(act["evidence"])

    st.markdown("### 4:05–4:30｜流水账、哈希与转化路径收口")
    st.success(
        "今天交付的是可运行的任务编排与验证原型。下一步不是重写系统，而是按数据契约接入脱敏传感日志，"
        "在台架上标定竞争链路、人工授权、射界和效应器参数，再进入专家工作坊、红蓝压测与合规场景试点。"
    )
    st.warning(
        "必须主动说明：全部概率、时延和扩容结果均为参数化合成仿真；当前未完成真实装备接口、"
        "商业平台部署、SWRL 在线执行或真实专家/红蓝验证。"
    )

    with st.expander("评委追问时再展开：固定资源为什么到 25 机失效？"):
        st.markdown(
            "固定资源的并行通道、循环周期和库存有硬上限，因此 25 机起使命成功率快速下降。"
            "资源包扩容实验没有提高单次作用概率，也没有缩短基础 OODA，只复制独立并行容量，"
            "同时计入跨包同步、去冲突和指令编组时延。这给出了可查询的能力边界，而不是‘无限抗蜂群’宣传。"
        )

    with st.expander("评委追问时再展开：为什么本体不是普通数据库？"):
        st.markdown(
            "SQL 也可以元数据驱动，所以我们不贬低数据库。当前夹具的可见差异是：加入 16 条合规语义声明后，"
            "不改原查询和可执行代码、不重启进程即可发现新装备并通过 SHACL；刚性集成基线的人天和代码行必须同题实测。"
        )

    st.caption("演示模式不自动计时、不自动跳页，避免现场网络或渲染波动造成失控。")


if __name__ == "__main__":
    main()
