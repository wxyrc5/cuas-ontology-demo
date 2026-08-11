# Notebook 复现入口

本目录只保留 4 个规范源 Notebook，按以下顺序执行：

1. `notebook_01_ontology_validation.ipynb`：本体结构、约束与查询验证；
2. `notebook_02_ooda_simulation.ipynb`：OODA 时延、20 机主裁决，以及 20–100 机 × 1–6 包的协调感知/理想并行资源前沿；
3. `notebook_03_bayesian_adaptive.ipynb`：贝叶斯自适应、ROC 与鲁棒性；
4. `notebook_04_demo_end_to_end.ipynb`：汇总裁决并复现 Effect→Action→Mission 独立 RDF 写回；不另造指标值。

启动方式：

```powershell
..\06_部署脚本\启动Jupyter.ps1
```

批量执行与核验：

```powershell
..\06_部署脚本\执行全部Notebook.ps1
```

交付前推荐运行包含两轮网页验收与跨文件哈希终审的一键入口：

```powershell
..\06_部署脚本\执行技术验收.ps1
```

批处理会先运行 `fix_notebook_fonts.py`，把可移植的中文 Matplotlib 字体配置写入每个规范 Notebook，再执行全部代码单元。

## 输出规则

- 新鲜执行副本、HTML 和执行清单写入 `验证输出/最新执行`；
- 图表写入 `验证输出/figures`；
- Action 复现输出写入 `验证输出/action_feedback_demo.json` 与 `action_feedback_writeback.ttl`；正式本体文件不被修改；
- 原始打包时附带的已执行副本、合并版和旧 HTML 已归档到 `历史版本/2026-08-06_原始快照`；
- 旧 `experiments_replication` 已归档到 `历史版本/2026-08-06_旧实验复现_非口径`；它与四个规范 Notebook 不是同一实验口径；
- 历史输出不得作为最终提案、PPT 或网页的指标来源。

所有规范源 Notebook 已改为相对项目路径，并为重复蒙特卡洛实验设置固定主种子和确定性子种子。
