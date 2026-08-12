# OODA 参数公开证据与选择说明

版本：v1.0（2026-08-12）  
配套机器可读表：`03_源码/streamlit_app/data/ooda_timing_params.json`  
适用边界：以下资料用于约束**量级与相对关系**，不是对任何真实反无系统、人员席位或效应器的标定。

## 1. 选择方法

1. 只使用可公开访问的政府、标准组织或原厂资料确认“可达到什么量级、哪些因素必须计入”。
2. 当公开资料没有给出反无特定数值时，不反推或虚构精确值；使用三角分布，并标记为待标定工程假设。
3. 主场景采用经过预案和态势压缩后的**单批次人工授权**；逐目标授权单独作为压力工况，避免用乐观的人因参数掩盖蜂群失效。
4. 所有网络数字都按端到端应用链路理解，不把 5G 空口指标直接当成系统端到端时延。

## 2. 证据—参数裁决表

| 参数组 | 当前三角分布/规则 | 公开证据 | 选择与边界 |
|---|---:|---|---|
| 雷达重访与连续确认 | 0.12 / 0.25 / 0.55 s | Echodyne EchoGuard 公开资料给出 10 Hz 航迹更新率、最多 20 条同时航迹 | 0.1 s 是单次更新量级；当前范围覆盖约 1–5 次更新及应用处理。只说明可行量级，不代表项目使用该雷达 |
| 航迹起始与稳定 | 0.08 / 0.18 / 0.40 s，随规模 log2 增长 | 同一公开资料说明 10 Hz 更新与 20 航迹容量 | 以多次更新形成稳定航迹；20 机恰处公开示例容量上限，因此规模增大必须出现排队/关联压力 |
| 传感上行 / C2 / 指令下行 | 15–120 ms | ITU IMT-2020 评估指标：URLLC 空口用户面 1 ms、控制面 20 ms；ITU-T Y.3147 的远控示例为端到端一般 20–50 ms | 项目取值包含编解码、排队与应用转发，故高于理想空口；对抗链路乘 1.8。不是 5G 实网测量 |
| 跨资源包同步与去冲突 | 每额外资源包 20 / 60 / 140 ms | SAPIENT ICD 说明数据代理验证输入、可能限制带宽，并建议多个本地传感集合采用层级 SAPIENT；ITU-T Y.3147 把同步精度与应用端到端时延分开 | 本参数是航迹合并、任务去冲突和指令编组的**应用级协调**，不是时钟同步误差；待多阵地回放/台架标定 |
| 多传感关联识别 | 0.10 / 0.24 / 0.55 s | SAPIENT 公开架构明确 DMM 对节点消息做高层融合与推理，产生融合航迹、告警并反向任务传感节点 | 公开 ICD 没给 C-UAS DMM 时延，当前值是工程预算；必须通过脱敏回放测 P50/P95/P99 |
| 人工批次授权 | 0.20 / 0.55 / 1.20 s | FAA 人因研究显示，复杂空管偏差识别和指令可能是数秒至十余秒；另有数据链确认延迟约 11 s 的研究工况 | 这些 FAA 任务比“一键批准已压缩批次方案”复杂，不能直接移植；反过来也说明 0.2–1.2 s 是**乐观的预案化假设**。逐目标授权必须作为压力工况展示 |
| HPM / HEL 效应相对关系 | HPM 0.06/0.15/0.32 s；HEL 0.55/1.25/2.50 s | GAO 说明定向能传播快，但效果取决于距离、目标部位和作用时间；HEL 通常单目标窄波束，HPM 宽波束可影响多个目标 | 公开资料支持相对排序与并发差异，不支持当前绝对秒数；绝对值待台架标定，不得称为装备性能 |
| 瞄准与射界 | 各效应器独立分布 | GAO 指出距离、天气、指向部位与作用时间影响效果；HEL 受天气和目标驻留影响 | 当前把 cue/aim 与 effect delivery 分开，便于后续用伺服、转台、射界和天气数据替换 |
| 毁伤/失效评估 | 0.12 / 0.30 / 0.70 s | SAPIENT C-UAS 公开需求包括“网络化传感器确认威胁上的效果”；10 Hz 航迹更新给出重复确认量级 | 取约 1–7 次更新并计入融合；真实 BDA 判据和复核次数尚未确定 |

## 3. 公开来源

1. UK Dstl, *SAPIENT Interface Control Document v7.0*（Protobuf、Data Agent、DMM、层级部署）：<https://assets.publishing.service.gov.uk/media/6419a2068fa8f547c68029d3/SAPIENT_Interface_Control_Document_v7_FINAL__fixed2_.pdf>。
2. UK DASA, *Countering Drones—Finding and neutralising small UAS threats*（多传感融合、传感任务、效果确认与带宽约束）：<https://www.gov.uk/government/publications/countering-drones-finding-and-neutralising-small-uas-threats/competition-document-countering-drones-finding-and-neutralising-small-uas-threats>。
3. Echodyne, *EchoGuard Government Brochure*（10 Hz、最多 20 航迹；原厂公开参数）：<https://www.echodyne.com/media/s4onszmh/brochure-gov-echodyne_5se.pdf>。
4. ITU-R, *Minimum technical performance requirements for IMT-2020*（URLLC/eMBB 用户面与控制面量级）：<https://www.itu.int/en/ITU-R/study-groups/rsg5/rwp5d/imt-2020/Documents/S01-1_Requirements%20for%20IMT-2020_Rev.pdf>。
5. ITU-T Y.3147 (04/2025), *Deterministic communications for remote device control*（端到端时延、可靠性和同步精度示例）：<https://www.itu.int/epublications/publication/itu-t-y-3147-2025-04-quality-of-service-requirements-and-framework-of-deterministic-communications-for-remote-device-control-services-over-imt-2020-an>。
6. FAA, *A Human Factors Simulation of Required Navigation Performance Converging Approach Procedures*（复杂态势下控制员识别与发出指令用时）：<https://hf.tc.faa.gov/publications/2007-a-human-factors-simulation/full_text.pdf>。
7. FAA, DOT/FAA/AM-01/8, *Data-linked pilot reply time on controller workload and communication*：<https://www.faa.gov/data_research/research/med_humanfacs/oamtechreports/2000s/2001/0108>。
8. U.S. GAO-23-106717, *Science & Tech Spotlight: Directed Energy Weapons*：<https://www.gao.gov/products/gao-23-106717>。

## 4. 必须保留的答辩边界

- 可以说：“参数量级受到公开标准、政府报告和原厂资料约束，全部分布可查询并支持替换。”
- 不可以说：“这些分布来自真实机场、真实席位或真实效应器标定。”
- 可以说：“20 机主场景采用单批次授权；逐目标授权、竞争链路和跨阵地协调已作为失效压力工况。”
- 不可以说：“完整闭环小于 5 秒已由现场验证。”
