# 🛡️ C-UAS Ontology — 反蜂群机场防护杀伤网

> **OSREDM 2026 · 7 号赛道 · 新概念反无**
> 基于 Palantir Ontology 方法论构建的反无人机体系本体论实时交互演示。

[![Streamlit](https://img.shields.io/badge/Streamlit-1.61-FF4B4B?logo=streamlit)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-OSREDM%202026-blue)](#)
[![Status](https://img.shields.io/badge/Status-Demo%20Ready-brightgreen)](#)

🌐 **在线演示**: <https://cuas-demo.streamlit.app>（部署后替换为真实 URL）

---

## 🎯 项目简介

本项目提出一个 **基于 Palantir Ontology 思想的反无人机体系本体论**，把反蜂群机场防护的
"使命 / 场景 / 能力 / 装备 / 威胁 / 资产 / 操作员 / 效果指标" 这 **8 个 Object Type**
与 **10 条 Link Type** 形式化，并配套一个 **贝叶斯自适应识别引擎**，使得 OODA 闭环
时延压缩到 **5 秒以内**，威胁识别 AUC 从 0.567 提升到 **0.9958**（+0.428）。

整个系统通过一个 5 页 Streamlit Web App 实时演示，评审专家可在线浏览本体架构、跑
SPARQL 推理、调节贝叶斯参数、仿真 PEK/BRU/MUC 三大机场反蜂群场景。

---

## 🏆 三大关键指标

| 指标 | 数值 | 对比 | 含义 |
|------|------|------|------|
| **贝叶斯 AUC** | **0.9958** | vs 固定规则 0.567 (+0.428) | 威胁识别精度 |
| **OODA 闭环** | **< 5 s** | vs 传统 10-15 s | 观察-判断-决策-行动 |
| **本体规模** | **8 OT + 10 LT + 4 ST** | Palantir 风格 | 形式化覆盖度 |

---

## 🗂 五大功能页面

| # | 页面 | 主要功能 | 关键技术 |
|---|------|---------|---------|
| 🏠 | **主页** | Logo / 3 大指标 / 视频嵌入 / 团队介绍 | `st.metric`, `st.video` |
| 🧬 | **本体浏览** | 8 OT 卡片 + 10 LT 网络图 + 实例计数 | Plotly Network Graph |
| 🔍 | **SPARQL 查询** | 5 模板查询 + 自定义 + 实时可视化 | rdflib + Plotly |
| 📊 | **贝叶斯实验** | 参数滑块 / 实时 ROC / AUC 对比 | Beta-Binomial 共轭 |
| 🗺 | **机场反无** | 3 场景 / 5-50 架 / OODA 瀑布 | Plotly Animation |

---

## 🧬 本体论核心（Palantir 风格）

### 8 个 Object Type
`Mission` · `Scenario` · `TechnicalCapability` · `Equipment` · `EffectMetric` ·
`Threat` · `Asset` · `Operator`

### 10 个 Link Type
1. `mission_requires_capability`
2. `scenario_involves_threat`
3. `threat_targets_asset`
4. `capability_implemented_by_equipment`
5. `equipment_operated_by_operator`
6. `mission_protects_asset`
7. `scenario_validates_mission`
8. `capability_achieves_metric`
9. `equipment_counters_threat`
10. `operator_assigned_to_mission`

### 4 个 Status Type
`Mission.status` · `Equipment.status` · `Scenario.status` · `Threat.status`

---

## 🛠 技术栈

- **Streamlit 1.61** — 多页面框架
- **Plotly 5.18** — 交互图（网络图 / 瀑布 / ROC）
- **rdflib 7.0** — SPARQL 查询
- **Pandas + NumPy** — 数据处理
- **Matplotlib + Seaborn** — 静态图
- **scikit-learn** — AUC 计算

---

## 🚀 快速启动

### 本地运行
```bash
git clone https://github.com/YOUR_USERNAME/cuas-ontology-demo.git
cd cuas-ontology-demo
pip install -r requirements.txt
streamlit run app.py
```
浏览器自动打开 <http://localhost:8501>。

### 一键演示模式
```bash
streamlit run demo_mode.py
```
进入 **30 分钟精华版自动演示** 模式，按剧本逐步跳转。

### Streamlit Cloud 一键部署
详见 [`deploy_guide.md`](./deploy_guide.md)，5 分钟即可拿到公开 URL。

---

## 📂 目录结构

```
streamlit_cloud_deploy/
├── app.py                          # 主入口（多页导航）
├── demo_mode.py                    # 自动演示模式
├── pages/                          # 多页应用（自动路由）
│   ├── 1_🏠_主页.py
│   ├── 2_🧬_本体浏览.py
│   ├── 3_🔍_SPARQL查询.py
│   ├── 4_📊_贝叶斯实验.py
│   └── 5_🗺_机场反无.py
├── utils/
│   ├── ontology_loader.py
│   ├── sparql_runner.py
│   └── bayes_engine.py
├── data/
│   ├── ontology.json
│   ├── airports.json
│   └── bayes_params.json
├── assets/                         # 静态资源
├── .streamlit/
│   ├── config.toml                 # 主题 + 服务配置
│   └── secrets.toml.example        # 密钥模板
├── requirements.txt                # Python 依赖
├── packages.txt                    # 系统依赖
├── runtime.txt                     # Python 版本
├── deploy_guide.md                 # ★ 5 分钟部署教程
└── .github/workflows/test.yml      # CI 自动化
```

---

## 👥 团队介绍

**C-UAS Ontology Group** · OSREDM 2026 · 新概念反无赛道

| 角色 | 姓名 | 职责 |
|------|------|------|
| 项目负责人 | 张三 | 体系架构、本体设计 |
| 算法工程师 | 李四 | 贝叶斯引擎、AUC 优化 |
| 数据工程师 | 王五 | SPARQL 推理、数据建模 |
| 前端工程师 | 赵六 | Streamlit 可视化 |
| 文档 & 演示 | 钱七 | 文档、PPT、视频 |

---

## 📞 联系方式

- 比赛：**OSREDM 2026 · 7 号赛道 · 新概念反无**
- 报名链接：<https://osredm.example.org>
- 团队邮箱：<cuas-team@example.org>

---

> © 2025 OSREDM C-UAS Ontology Group · Streamlit 1.61 · Plotly 5.18 · rdflib 7.0
