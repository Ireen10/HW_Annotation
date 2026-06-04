"""Optional JSON Schema validation (requires jsonschema package)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"


def _load_schema(name: str) -> dict[str, Any]:
    return json.loads((_SCHEMA_DIR / name).read_text(encoding="utf-8"))


def validate_instance(instance: Any, schema_name: str) -> list[str]:
    try:
        import jsonschema
    except ImportError:
        return [f"jsonschema not installed; skipped {schema_name}"]

    schema = _load_schema(schema_name)
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)
    return [f"{list(e.path)}: {e.message}" for e in errors]
