"""Human-readable semantic event log derived from one simulation snapshot."""
from __future__ import annotations

from typing import Any


def build_semantic_event_log(sim: dict[str, Any], airport: dict[str, Any]) -> list[dict[str, Any]]:
    phases = {row["phase"]: row for row in sim["ooda_phases"]}
    threat = "Threat_09" if int(sim["n_uavs"]) >= 9 else "Threat_01"
    protected = airport["assets"][0]["name"]
    effect = sim["ooda_effector"]
    rows = [
        (0.0, "Observe", "Radar_007", "observes", threat, "观测事件写入时空上下文；先通过 Schema、时间和 CRS 门。"),
        (phases["Observe"]["end"], "Orient", threat, "threatens", protected, "多源关联后生成 Threat→Asset 关系并计算优先级。"),
        (phases["Orient"]["end"], "Decide", "Mission_001", "requires", "TechnicalCapability", "运行态闭世界规则形成能力请求；不是在线 HermiT。"),
        (phases["Decide"]["end"], "Decide", "Action_WTA", "allocates", effect, f"在容量、射界和授权门下编排 {effect}。"),
        (phases["Act"]["end"], "Act", effect, "causesEffect", threat, "效应到达；结果仍是参数化仿真而非实装命中。"),
        (phases["Feedback"]["end"], "Feedback", "EffectMetric", "validates", "Mission_001", "效果证据写回数字线程，供下一批贝叶斯更新和复盘。"),
    ]
    return [
        {
            "时间": f"T+{time_s:.3f}s",
            "阶段": phase,
            "语义事件": f"{subject} —{predicate}→ {obj}",
            "评委可读解释": explanation,
        }
        for time_s, phase, subject, predicate, obj, explanation in rows
    ]
