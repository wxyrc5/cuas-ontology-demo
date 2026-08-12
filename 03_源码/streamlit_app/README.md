# C-UAS Streamlit 演示应用

这是参赛项目的本地交互主线，包含主页、本体浏览、SPARQL 查询、概率时序融合沙盒和机场二维/三维态势五个功能页，另有一页 12 分钟演示提示单。

## 启动

从项目根目录执行：

```powershell
.\06_部署脚本\启动本地项目.ps1
```

或使用隔离环境直接启动：

```powershell
& ..\.venv-cuas\python.exe -m streamlit run .\03_源码\streamlit_app\app.py
```

## 页面

| 页面 | 用途 | 证据边界 |
|---|---|---|
| `app.py` | 入口、可信指标与已知缺口 | 读取 `data/current_metrics.json` |
| 主页 | 项目逻辑、验证状态与演示说明 | 不提供未核验团队或在线地址 |
| 本体浏览 | 8/10 核心 + 3/6 扩展、26 个随包核心实例、45 条样例边，以及热插拔、L1/L2/L3、失败复盘、WTA 与 Action 写回 | Action 只写会话状态与独立 RDF 预览；不是 Foundry/真实装备接入 |
| SPARQL 查询 | 对随包 RDF 图执行模板或自定义查询 | RDFLib 内存图 |
| 概率时序融合 | 参数化机制沙盒和即时 ROC | 合成互动结果；不覆盖 Notebook 03 基准 |
| 机场反无 | PKX、BRU、MUC 的二维/三维同源态势 | 参数化演示；非现场效能 |
| `demo_mode.py` | 12 分钟答辩操作提示 | 人工切页，不是自动计时器 |

## 可信指标

`data/current_metrics.json` 由 `06_部署脚本/export_current_metrics.py` 从三份已验证结果导出：

- `指标裁决.json`
- `最新执行/execution_manifest.json`
- `streamlit_acceptance.json`

不要手工改写该快照。重新运行 Notebook 或应用验收后，再运行导出与同步脚本。

## 二维/三维主线

机场态势页使用固定随机种子、60 帧连续轨迹和三波不同高度威胁；二维与三维读取同一状态。北京大兴机场代码为 PKX/ZBAD。离线地图位于 `static/maps/`，不依赖网络底图请求。

## 验收

```powershell
& ..\..\..\.venv-cuas\python.exe .\06_部署脚本\verify_streamlit_app.py
& ..\..\..\.venv-cuas\python.exe .\06_部署脚本\export_current_metrics.py
.\06_部署脚本\sync_streamlit_deploy.ps1
```

截至 2026-08-12，八个入口与页面均通过语法和 Streamlit AppTest；Effect→Action→Mission 原型另经确定性决策、分级授权门、RDF 可解析性和正式本体不变性检查；语义热插拔、三机场 CRS、异常入口隔离、20 目标 WTA 和失败溯源夹具也通过自动验收。当前 OWL 2 DL TBox + 正向 ABox 已通过 HermiT 一致性验证，并以互斥类型负向对照验证推理器能拒绝矛盾模型；该结论只覆盖当前版本。正式陈述仍须明确：当前仅有软件原型和合成仿真，没有 Palantir Foundry 部署、机场现场测试、SCM 因果识别或真实专家标注验证。
