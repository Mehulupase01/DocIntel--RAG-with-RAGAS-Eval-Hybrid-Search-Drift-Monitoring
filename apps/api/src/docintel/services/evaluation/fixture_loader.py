from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[6]
FIXTURES_DIR = ROOT_DIR / "fixtures"
DEFAULT_FIXTURE_PATH = FIXTURES_DIR / "eu_ai_act_qa_v1.json"
DEFAULT_SCHEMA_PATH = FIXTURES_DIR / "eu_ai_act_qa_v1.schema.json"


class FixtureValidationError(ValueError):
    """Raised when the eval fixture does not match the expected schema."""


@dataclass(frozen=True, slots=True)
class FixtureCase:
    id: str
    question: str
    ground_truth: str
    expected_articles: list[str]
    category: str


@dataclass(frozen=True, slots=True)
class FixtureSuite:
    version: str
    source_doc_sha256: str
    cases: list[FixtureCase]


def load_fixture(
    *,
    suite_version: str = "v1",
    fixture_path: Path | None = None,
    schema_path: Path | None = None,
) -> FixtureSuite:
    resolved_fixture_path = fixture_path or _fixture_path_for_suite(suite_version)
    resolved_schema_path = schema_path or DEFAULT_SCHEMA_PATH
    payload = json.loads(resolved_fixture_path.read_text(encoding="utf-8"))
    schema = json.loads(resolved_schema_path.read_text(encoding="utf-8"))
    _validate_schema_value(payload, schema, path="$")
    return FixtureSuite(
        version=str(payload["version"]),
        source_doc_sha256=str(payload["source_doc_sha256"]),
        cases=[
            FixtureCase(
                id=str(case["id"]),
                question=str(case["question"]),
                ground_truth=str(case["ground_truth"]),
                expected_articles=[str(article) for article in case["expected_articles"]],
                category=str(case["category"]),
            )
            for case in payload["cases"]
        ],
    )


def _fixture_path_for_suite(suite_version: str) -> Path:
    if suite_version != "v1":
        raise FixtureValidationError(f"Unsupported suite_version: {suite_version}")
    return DEFAULT_FIXTURE_PATH


def _validate_schema_value(value: Any, schema: dict[str, Any], *, path: str) -> None:
    schema_type = schema.get("type")
    if schema_type == "object":
        if not isinstance(value, dict):
            raise FixtureValidationError(f"{path} must be an object")
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                raise FixtureValidationError(f"{path}.{key} is required")
        properties = schema.get("properties", {})
        for key, property_schema in properties.items():
            if key in value:
                _validate_schema_value(value[key], property_schema, path=f"{path}.{key}")
        return

    if schema_type == "array":
        if not isinstance(value, list):
            raise FixtureValidationError(f"{path} must be an array")
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            raise FixtureValidationError(f"{path} must contain at least {min_items} items")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                _validate_schema_value(item, item_schema, path=f"{path}[{index}]")
        return

    if schema_type == "string":
        if not isinstance(value, str):
            raise FixtureValidationError(f"{path} must be a string")
        min_length = schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            raise FixtureValidationError(f"{path} must be at least {min_length} characters")
        enum_values = schema.get("enum")
        if enum_values and value not in enum_values:
            raise FixtureValidationError(f"{path} must be one of {enum_values}")
        return

    if schema_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise FixtureValidationError(f"{path} must be a number")
        return

    if schema_type == "boolean":
        if not isinstance(value, bool):
            raise FixtureValidationError(f"{path} must be a boolean")
        return

    raise FixtureValidationError(f"{path} uses unsupported schema type: {schema_type}")
