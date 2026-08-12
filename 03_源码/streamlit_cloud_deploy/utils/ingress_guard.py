"""Closed-world ingress guards for adversarial or malformed track events.

These guards detect schema, time, CRS, kinematic and corroboration anomalies.
They cannot prove that a plausible, well-formed track is genuine; that boundary
is kept explicit in every returned decision.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .coordinate_normalization import normalize_point_wkt


REQUIRED_FIELDS = {
    "event_id", "source_id", "event_time_utc", "ingest_time_utc",
    "coordinate_reference_system", "target_coordinate_reference_system",
    "position_wkt", "position_accuracy_m", "velocity_enu_mps",
    "source_count", "signal", "observation",
}


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must carry a UTC offset")
    return parsed.astimezone(timezone.utc)


def evaluate_ingress_event(
    event: dict[str, Any],
    *,
    max_ingest_lag_s: float = 2.0,
    max_speed_mps: float = 120.0,
    max_position_accuracy_m: float = 100.0,
) -> dict[str, Any]:
    failures: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(event))
    if missing:
        return {
            "status": "QUARANTINE",
            "failed_gates": [f"missing_fields:{','.join(missing)}"],
            "normalized": None,
            "boundary": "结构门只能拒绝已知异常，不能证明语义上逼真的假航迹为真。",
        }

    try:
        event_time = _parse_utc(str(event["event_time_utc"]))
        ingest_time = _parse_utc(str(event["ingest_time_utc"]))
        lag = (ingest_time - event_time).total_seconds()
        if lag < 0.0 or lag > max_ingest_lag_s:
            failures.append(f"timestamp_lag:{lag:.3f}s")
    except (TypeError, ValueError) as exc:
        failures.append(f"timestamp:{exc}")

    try:
        normalized = normalize_point_wkt(
            str(event["position_wkt"]),
            str(event["coordinate_reference_system"]),
            str(event["target_coordinate_reference_system"]),
        )
    except (TypeError, ValueError) as exc:
        normalized = None
        failures.append(f"crs_or_position:{exc}")

    velocity = event.get("velocity_enu_mps", {})
    try:
        speed = sum(float(velocity[key]) ** 2 for key in ("east", "north", "up")) ** 0.5
        if speed > max_speed_mps:
            failures.append(f"kinematic_speed:{speed:.3f}mps")
    except (KeyError, TypeError, ValueError) as exc:
        failures.append(f"velocity:{exc}")

    try:
        if float(event["position_accuracy_m"]) > max_position_accuracy_m:
            failures.append("position_accuracy")
    except (TypeError, ValueError):
        failures.append("position_accuracy_type")

    if int(event.get("source_count", 0)) < 2:
        failures.append("single_source_requires_confirmation")
    signal = event.get("signal", {})
    try:
        if not 0.0 <= float(signal["confidence"]) <= 1.0:
            failures.append("signal_confidence")
    except (KeyError, TypeError, ValueError):
        failures.append("signal_confidence")

    return {
        "status": "ACCEPT" if not failures else "QUARANTINE",
        "failed_gates": failures,
        "normalized": normalized,
        "boundary": "结构、时间、坐标和运动学门不能识别所有语义逼真的欺骗；仍需多源关联和红蓝数据验证。",
    }
