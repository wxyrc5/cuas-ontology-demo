"""Access the audited metric snapshot bundled with the Streamlit app."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


METRICS_PATH = Path(__file__).resolve().parents[1] / "data" / "current_metrics.json"


@lru_cache(maxsize=1)
def load_current_metrics() -> dict:
    if not METRICS_PATH.is_file():
        raise FileNotFoundError(
            "缺少 current_metrics.json；请先运行 06_部署脚本/export_current_metrics.py。"
        )
    payload = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 2 or payload.get("not_field_test") is not True:
        raise ValueError("current_metrics.json 结构或证据范围无效")
    return payload
