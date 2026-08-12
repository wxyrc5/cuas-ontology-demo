"""Validate runtime Action bundles against the versioned JSON contract."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator


SCHEMA_PATH = Path(__file__).resolve().parent.parent / "data" / "action_contract.schema.json"


def load_action_schema(path: Path = SCHEMA_PATH) -> dict[str, Any]:
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


def validate_action_bundle(bundle: Mapping[str, Any], path: Path = SCHEMA_PATH) -> None:
    """Raise jsonschema.ValidationError when the bundle violates the contract."""
    Draft202012Validator(load_action_schema(path)).validate(dict(bundle))
