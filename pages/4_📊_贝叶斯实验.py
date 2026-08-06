"""Page 4 – Bayesian Experiment / 贝叶斯实验."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.bayes_engine import run_experiment, run_preset
from utils.ontology_loader import load_bayes_params


def show() -> None:
    st.title("📊 贝叶斯自适应威胁识别实验")
    st.markdown(
        """
        使用 **Beta-Binomial 共轭模型** 自适应估计敌方无人机的真实阳性率 *P*。
        与传统的 **固定阈值 LLR 规则** 比较 AUC、收敛速度与鲁棒性。
        """
    )

    cfg = load_bayes_params()
    presets = cfg["preset_scenarios"]

    # ------------------------------------------------------------------
    # Preset picker
    # ------------------------------------------------------------------
    st.subheader("🎬 内置场景预设")

    p_cols = st.columns(len(presets))
    chosen_preset = None
    for i, p in enumerate(presets):
        with p_cols[i]:
            if st.button(f"📌 {p['name']}", key=f"preset_{i}", use_container_width=True):
                chosen_preset = p

    st.markdown("---")

    # ------------------------------------------------------------------
    # Manual parameter sliders
    # ------------------------------------------------------------------
    st.subheader("🛠️ 参数调节（自定义实验）")

    col_left, col_right = st.columns([1, 2])

    with col_left:
        with st.container(border=True):
            st.markdown("**先验（Beta 分布）**")
            alpha = st.slider("α (伪成功)", 1.0, 50.0, 4.0, 0.5)
            beta_p = st.slider("β (伪失败)", 1.0, 50.0, 2.0, 0.5)
            st.markdown(f"先验均值 ≈ **{alpha/(alpha+beta_p):.3f}**")

            st.markdown("**似然 / 真值**")
            true_p = st.slider("真实阳性率 p", 0.50, 0.95, 0.70, 0.01)
            noise = st.slider("观测噪声", 0.00, 0.30, 0.10, 0.01)

            st.markdown("**采样**")
            n_obs = st.slider("观察次数 n", 10, 1000, 200, 10)
            n_seeds = st.slider("随机种子数", 1, 20, 8, 1)
            fixed_thr = st.slider("固定阈值 LLR", 0.0, 5.0, 1.5, 0.1)

            run_btn = st.button("🚀 跑实验", type="primary", use_container_width=True)

    # Decide which experiment to run
    if run_btn:
        with st.spinner("运行贝叶斯与固定规则 AUC 实验..."):
            st.session_state["bayes_result"] = run_experiment(
                n_obs=n_obs, true_p=true_p, noise=noise,
                n_seeds=n_seeds,
                alpha_prior=alpha, beta_prior=beta_p,
                fixed_threshold=fixed_thr,
            )
    elif chosen_preset:
        with st.spinner(f"加载预设 {chosen_preset['name']} ..."):
            st.session_state["bayes_result"] = run_preset(chosen_preset)

    # First run with defaults?
    if run_btn is False and "bayes_result" not in st.session_state:
        with st.spinner("加载默认实验..."):
            st.session_state["bayes_result"] = run_preset(presets[0])

    # ------------------------------------------------------------------
    # Results panel
    # ------------------------------------------------------------------
    if "bayes_result" in st.session_state:
        result = st.session_state["bayes_result"]

        with col_right:
            # ----- Metric cards
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("贝叶斯 AUC", f"{result.bayes_auc:.4f}")
            m2.metric("固定规则 AUC", f"{result.fixed_auc:.4f}")
            m3.metric("提升 Δ", f"+{result.improvement:.4f}")
            p_str = "< 1e-25" if result.p_value_better < 1e-25 else f"{result.p_value_better:.2e}"
            m4.metric("p 值", p_str)

            st.markdown(
                f"""
                实验设置：`n={result.n_obs}`, `p={result.true_p}`,
                `noise={result.noise}`, `seeds={result.n_seeds}` ·
                后验均值 **{result.posterior_mean:.3f} ± {result.posterior_std:.3f}**
                """
            )

            st.markdown("---")

            # ----- ROC Plot
            st.markdown("### 📈 ROC 曲线对比")
            fig_roc = go.Figure()
            b = result.bayes_roc
            f = result.fixed_roc
            fig_roc.add_trace(go.Scatter(
                x=b["fpr"], y=b["tpr"], mode="lines",
                name=f"贝叶斯 (AUC={result.bayes_auc:.4f})",
                line=dict(color="#1F77B4", width=3),
                fill="tozeroy", fillcolor="rgba(31,119,180,0.15)",
            ))
            fig_roc.add_trace(go.Scatter(
                x=f["fpr"], y=f["tpr"], mode="lines",
                name=f"固定规则 (AUC={result.fixed_auc:.4f})",
                line=dict(color="#D62728", width=3, dash="dash"),
            ))
            fig_roc.add_trace(go.Scatter(
                x=[0, 1], y=[0, 1], mode="lines",
                name="随机 (AUC=0.5)",
                line=dict(color="gray", width=1, dash="dot"),
                showlegend=True,
            ))
            fig_roc.update_layout(
                xaxis_title="假阳率 FPR",
                yaxis_title="真阳率 TPR",
                height=420,
                legend=dict(x=0.55, y=0.05),
                plot_bgcolor="#F8F9FB",
            )
            st.plotly_chart(fig_roc, use_container_width=True)

            # ----- Posterior evolution
            st.markdown("### 🧬 后验均值随观察次数演化")
            if result.posterior_curve:
                xs = [p["n"] for p in result.posterior_curve]
                ys = [p["mean"] for p in result.posterior_curve]
                lo = [max(0, m - 1.96 * math.sqrt(max(m * (1 - m), 1e-3) / max(n, 1)))
                      for n, m in zip(xs, ys)]
                hi = [min(1, m + 1.96 * math.sqrt(max(m * (1 - m), 1e-3) / max(n, 1)))
                      for n, m in zip(xs, ys)]

                fig_post = go.Figure()
                # CI band
                fig_post.add_trace(go.Scatter(
                    x=xs + xs[::-1], y=hi + lo[::-1],
                    fill="toself", fillcolor="rgba(31,119,180,0.15)",
                    line=dict(width=0),
                    name="95% CI",
                    hoverinfo="skip",
                ))
                fig_post.add_trace(go.Scatter(
                    x=xs, y=ys, mode="lines+markers",
                    name="后验均值",
                    line=dict(color="#1F77B4", width=3),
                    marker=dict(size=6),
                ))
                fig_post.add_hline(y=result.true_p, line_dash="dash",
                                    line_color="#2CA02C",
                                    annotation_text=f"真值 p={result.true_p}",
                                    annotation_position="top left")
                fig_post.add_hline(y=0.5, line_dash="dot",
                                    line_color="#999",
                                    annotation_text="决策阈值 0.5",
                                    annotation_position="bottom left")
                fig_post.update_layout(
                    xaxis_title="观察次数 n",
                    yaxis_title="阳性率估计",
                    height=380,
                    plot_bgcolor="#F8F9FB",
                    yaxis=dict(range=[0, 1]),
                )
                st.plotly_chart(fig_post, use_container_width=True)

            # ----- Convergence speed
            st.markdown("### 🚀 收敛速度分析")
            conv = cfg["plots"]["convergence_speed"]
            fig_conv = go.Figure()
            x = conv["x"]
            fig_conv.add_trace(go.Scatter(
                x=x, y=conv["bayes_auc_mean"], mode="lines+markers",
                name="贝叶斯 AUC", line=dict(color="#1F77B4", width=3),
                error_y=dict(type="data", array=conv["bayes_auc_std"], thickness=2,
                             color="rgba(31,119,180,0.4)"),
            ))
            fig_conv.add_trace(go.Scatter(
                x=x, y=conv["fixed_auc_mean"], mode="lines+markers",
                name="固定规则 AUC", line=dict(color="#D62728", width=3, dash="dash"),
                error_y=dict(type="data", array=conv["fixed_auc_std"], thickness=2,
                             color="rgba(214,39,40,0.4)"),
            ))
            fig_conv.add_hline(y=0.9, line_dash="dot", line_color="#2CA02C",
                                annotation_text="可部署阈值 AUC=0.9")
            fig_conv.update_layout(
                xaxis_title="观察次数 n",
                yaxis_title="AUC",
                height=380, xaxis_type="log",
                plot_bgcolor="#F8F9FB",
                yaxis=dict(range=[0.4, 1.02]),
            )
            st.plotly_chart(fig_conv, use_container_width=True)

            # ----- Fixed-rule LLR trace
            st.markdown("### 📏 固定规则 LLR 分数 (样本轨迹)")
            if result.fixed_series:
                fig_llr = go.Figure()
                fig_llr.add_trace(go.Scatter(
                    y=result.fixed_series[:200],
                    mode="lines",
                    line=dict(color="#D62728", width=2),
                    name="LLR",
                ))
                fig_llr.add_hline(y=result.fixed_threshold, line_dash="dash",
                                   line_color="#000",
                                   annotation_text=f"阈值={result.fixed_threshold:.2f}",
                                   annotation_position="top right")
                fig_llr.add_hline(y=0, line_color="#999", line_width=1)
                fig_llr.update_layout(
                    xaxis_title="观察序号",
                    yaxis_title="LLR 分数",
                    height=300,
                    plot_bgcolor="#F8F9FB",
                )
                st.plotly_chart(fig_llr, use_container_width=True)

            # ----- Sign test summary
            st.markdown("---")
            st.markdown("### 🧪 显著性检验（贝叶斯 vs 固定规则）")
            stats = cfg["expected_results"]
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("参考 AUC 提升", f"+{stats['improvement']:.4f}")
            sc2.metric("p 值", f"{stats['p_value']:.2e}")
            sc3.metric("Cohen's d", f"{stats['cohen_d']:.1f}")
            sc4.metric("中位收敛", f"{stats['median_convergence_obs']} obs")

            with st.expander("📑 统计方法说明", expanded=False):
                st.markdown(
                    """
                    - **贝叶斯分类器**：Beta(α₀ + Σs, β₀ + Σf) 共轭后验，取 P̂ > 0.5 为阳性。
                    - **固定规则分类器**：log[p/(1−p)] > τ，本实验中 τ 通过网格搜索最大化 AUC。
                    - **AUC**：对每个种子算 ROC 曲线后取均值。
                    - **p 值**：双样本 Welch's t 检验对贝叶斯 vs 固定规则的 AUC 分布做差异检验。
                    - **收敛**：首次到达 AUC ≥ 0.95 的观察序号。
                    """
                )

    st.markdown("---")
    st.caption("页 4 · Bayesian Experiment · Beta-Binomial Conjugate")


if __name__ == "__main__":
    show()
