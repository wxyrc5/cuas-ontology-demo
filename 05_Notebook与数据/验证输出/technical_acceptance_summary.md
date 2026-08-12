# C-UAS 技术主线最终验收摘要

- 总结论：**通过**
- 生成时间：2026-08-12T20:36:33+08:00
- 项目根目录：`D:\Downloads\反无人机体系\cuas-ontology-demo-consolidated`

| 检查 | 结果 | 证据 |
|---|---:|---|
| 4 个规范 Notebook 全量执行 | 通过 | notebooks=4; code_cells=43/43; errors=0 |
| 执行清单与当前 Notebook 源文件哈希一致 | 通过 | 4/4 source SHA-256 checked |
| 指标裁决引用当前 3 个上游指标文件 | 通过 | pass=21; fail=0; report_only=2 |
| 本体形式一致性 | 通过 | 8 core OT / 10 core LT + 3/6 extensions; HermiT and SHACL controls passed |
| 20 机闭环与容量前沿 | 通过 | adaptive_pk=0.765500; wilson_low=0.759577; static_pk=0.300700; frontier=20 |
| 20–100 机协调感知资源增配与同资源策略优势 | 通过 | adaptive_min_packages={20: 1, 25: 2, 30: 2, 40: 2, 50: 3, 60: 3, 75: 4, 100: 5}; static_min_packages={20: 2, 25: 4, 30: None, 40: None, 50: None, 60: None, 75: None, 100: None}; grid=48 x 3000 runs |
| 五通道贝叶斯与固定规则公平对照 | 通过 | bayesian_auc=0.967892; fixed_auc=0.868806; delta_ci95=[0.094902, 0.103465] |
| Streamlit、SPARQL、离线地图与防御包络验收 | 通过 | pages=8/8; templates={'anti_swarm': 8, 'asset_protection': 1, 'kill_chain': 12, 'operator_roster': 3, 'ontology_schema': 10}; envelopes={'PKX': 3, 'BRU': 3, 'MUC': 3}; interactive_50x3={'闭环使命 Pk': '96.9%', '平均失效目标': '48.6/50', '同构资源包': '3 包', '平均行动成本': '19.14'} |
| 蜂群轨迹连续性与二维/三维同源状态 | 通过 | PKX 20 UAV x 60 frames; max_step=0.2985318415747092 km; max_outward=0.0 km; 2D/3D states=20 |
| 本地 Streamlit 隔离端口真实启动 | 通过 | port=8510; startup=1.59s; health=200/ok; root=200; cleanup=True |
| 本体 Effect→Action→Mission 写回原型 | 通过 | decision=ACT-CE7C636D7E17; rules=8; auto=5; human_gate=3; rdf_triples=153; canonical unchanged |
| Streamlit 唯一主线与部署镜像哈希一致 | 通过 | 42/42 managed files matched |
| 网页指标快照与 Notebook/验收结果完全一致 | 通过 | notebook_cells=43; pages=8; pk20=0.7655; auc=0.967891796875 |
| 形式模型、OODA、蜂群资源与机场参数文件齐备 | 通过 | 15/15 required files present |

## 范围

本报告只证明当前技术主线的本体、Notebook、Streamlit、参数文件和指标快照彼此一致。
申报书、PPT、视频、实名报名材料和最终提交压缩包属于用户明确暂缓的后续步骤。
