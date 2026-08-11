"""Page 4 – five-channel Bayesian feedback flywheel."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.bayesian_flywheel import (
    CHANNELS,
    COMPOSITE_THRESHOLD,
    evaluate_fixed_rule_baseline,
    flywheel_channel_rows,
    simulate_flywheel,
)


COLORS = {
    "detection": "#1F77B4",
    "identification": "#2CA02C",
    "interception": "#FF7F0E",
    "ooda_closure": "#7B2CBF",
    "false_alarm_compliance": "#D62728",
}


def _rgba(hex_color: str, alpha: float) -> str:
    value = hex_color.lstrip("#")
    red, green, blue = (int(value[index:index + 2], 16) for index in (0, 2, 4))
    return f"rgba({red},{green},{blue},{alpha:.3f})"


@st.cache_data(show_spinner=False)
def _run_models(
    n_observations: int,
    flywheel_seed: int,
    observations_per_case: int,
    cases_per_seed: int,
):
    flywheel = simulate_flywheel(
        n_observations=n_observations,
        seed=flywheel_seed,
    )
    comparison = evaluate_fixed_rule_baseline(
        n_cases_per_seed=cases_per_seed,
        observations_per_channel=observations_per_case,
        n_seeds=20,
        seed=20260810,
    )
    return flywheel, comparison


def _flywheel_figure(result) -> go.Figure:
    fig = go.Figure()
    x = result.steps
    for channel in CHANNELS:
        key = channel.key
        color = COLORS[key]
        fig.add_trace(
            go.Scatter(
                x=x,
                y=result.credible_high[key],
                mode="lines",
                line=dict(width=0),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=x,
                y=result.credible_low[key],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor=_rgba(color, 0.13),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=x,
                y=result.posterior_mean[key],
                mode="lines",
                name=channel.label_zh,
                line=dict(color=color, width=2.2),
                hovertemplate="n=%{x}<br>后验均值=%{y:.3f}<extra></extra>",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=result.combined_high,
            mode="lines",
            line=dict(width=0),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=result.combined_low,
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(20,20,20,0.10)",
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=result.combined_mean,
            mode="lines",
            name="综合 P(M_success)",
            line=dict(color="#111111", width=4, dash="dash"),
            hovertemplate="n=%{x}<br>综合后验=%{y:.3f}<extra></extra>",
        )
    )
    fig.add_hline(
        y=COMPOSITE_THRESHOLD,
        line_color="#E53935",
        line_width=2,
        line_dash="dot",
        annotation_text=f"综合门槛 {COMPOSITE_THRESHOLD:.2f}",
        annotation_position="bottom right",
    )
    fig.update_layout(
        title=f"五通道 Beta-Binomial 自适应收敛（seed={result.seed}）",
        xaxis_title="观测次数 n",
        yaxis_title="后验任务满足概率",
        yaxis=dict(range=[0.35, 1.01]),
        height=620,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=-0.30, x=0),
        margin=dict(l=40, r=30, t=65, b=130),
        plot_bgcolor="#FAFBFD",
    )
    return fig


def _roc_figure(comparison) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=comparison.bayesian_roc["fpr"],
            y=comparison.bayesian_roc["tpr"],
            mode="lines",
            name=f"贝叶斯（AUC={comparison.bayesian_auc:.3f}）",
            line=dict(color="#1F77B4", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=comparison.fixed_rule_roc["fpr"],
            y=comparison.fixed_rule_roc["tpr"],
            mode="lines+markers",
            name=f"固定规则（AUC={comparison.fixed_rule_auc:.3f}）",
            line=dict(color="#D62728", width=3, dash="dash"),
            marker=dict(size=5),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode="lines",
            name="随机基线",
            line=dict(color="#777", width=1, dash="dot"),
        )
    )
    fig.update_layout(
        title="同场景、同五通道、同观测预算的 ROC 对照",
        xaxis_title="假阳率 FPR",
        yaxis_title="真阳率 TPR",
        xaxis=dict(range=[0, 1]),
        yaxis=dict(range=[0, 1.01]),
        height=430,
        legend=dict(x=0.47, y=0.08),
        plot_bgcolor="#FAFBFD",
    )
    return fig


def show() -> None:
    st.title("📊 五通道贝叶斯反馈飞轮")
    st.markdown(
        "探测、识别、拦截、OODA 闭环和低虚警合规五类 Effect 证据，"
        "分别用 Beta-Binomial 后验更新，再通过归一化任务权重回写 Mission。"
    )
    st.warning(
        "本页全部数值为固定种子的合成工程仿真，不是机场现场测试或实装武器效能。",
        icon="⚠️",
    )

    with st.expander("实验参数", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        n_observations = c1.slider("飞轮观测数", 50, 400, 200, 10)
        flywheel_seed = c2.number_input("飞轮随机种子", 0, 999999, 42, 1)
        observations_per_case = c3.slider("AUC 每通道观测数", 10, 80, 30, 5)
        cases_per_seed = c4.select_slider("AUC 每种子案例数", [200, 400, 800, 1200], 800)

    with st.spinner("计算五通道后验和公平 AUC 对照..."):
        flywheel, comparison = _run_models(
            int(n_observations),
            int(flywheel_seed),
            int(observations_per_case),
            int(cases_per_seed),
        )

    interval_low, interval_high = flywheel.final_composite_interval
    sustained = flywheel.sustained_threshold_crossing
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("终态综合后验", f"{flywheel.final_composite:.3f}")
    m2.metric("终态 95% CI", f"[{interval_low:.3f}, {interval_high:.3f}]")
    m3.metric("连续 10 次越过 0.90", f"n={sustained}" if sustained else "未达到")
    m4.metric("贝叶斯 AUC", f"{comparison.bayesian_auc:.3f}")
    m5.metric("固定规则 AUC", f"{comparison.fixed_rule_auc:.3f}")

    st.plotly_chart(_flywheel_figure(flywheel), width="stretch")
    st.caption(
        "综合曲线采用 ΣwₖE[pₖ|D]，权重严格归一化为 1.00；"
        "它是任务满足度后验，不等同于假定五通道独立后的概率乘积。"
    )

    rows = pd.DataFrame(flywheel_channel_rows(flywheel))
    st.subheader("五通道参数与终态后验（可查询）")
    st.dataframe(
        rows,
        width="stretch",
        hide_index=True,
        column_config={
            "权重": st.column_config.NumberColumn(format="%.2f"),
            "合成真值": st.column_config.NumberColumn(format="%.3f"),
            "工程门槛": st.column_config.NumberColumn(format="%.3f"),
            "终态后验均值": st.column_config.NumberColumn(format="%.3f"),
            "95%下界": st.column_config.NumberColumn(format="%.3f"),
            "95%上界": st.column_config.NumberColumn(format="%.3f"),
        },
    )

    st.subheader("固定规则 AUC 对照")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("AUC 差值", f"{comparison.auc_delta:+.3f}")
    ci_low, ci_high = comparison.paired_seed_auc_delta_ci95
    r2.metric("配对种子 ΔAUC 95% CI", f"[{ci_low:.3f}, {ci_high:.3f}]")
    r3.metric(
        "贝叶斯 FPR / FNR",
        f"{comparison.bayesian_fpr:.1%} / {comparison.bayesian_fnr:.1%}",
    )
    r4.metric(
        "固定规则 FPR / FNR",
        f"{comparison.fixed_rule_fpr:.1%} / {comparison.fixed_rule_fnr:.1%}",
    )
    st.plotly_chart(_roc_figure(comparison), width="stretch")

    with st.expander("比较口径与可审计边界", expanded=True):
        st.markdown(
            f"""
            - 两个模型共享 **{comparison.n_seeds} 个种子 × {comparison.n_cases_per_seed} 个案例 × 5 个通道 × {comparison.observations_per_channel} 次观测**。
            - 贝叶斯模型计算每个通道超过工程门槛的后验概率，并做加权几何聚合。
            - 固定规则对同一批经验成功率直接执行五个预先声明的硬阈值，并以通过权重之和作为 ROC 分数。
            - 正负类在门槛附近设置 0.04 的合成灰区；灰区案例标为“不确定”，不被强行纳入 ROC 标签。
            - 所有参数、权重、门槛和随机种子均在源码与 Notebook 03 中公开，未使用未来观测或不等样本预算。
            """
        )

    st.caption("页 4 · Bayesian Effect→Mission Flywheel · 合成可复现实验")


if __name__ == "__main__":
    show()
