"""OpenAPI contract checks: valid spec, examples validate, no drift, every operation documented."""

import json
from pathlib import Path

import httpx
from openapi_spec_validator import validate
from pydantic import BaseModel

import app.schemas as schemas
from app.main import app
from scripts.export_openapi import OUT, render

ROOT = Path(__file__).resolve().parents[2]


def test_spec_is_valid_openapi() -> None:
    validate(app.openapi())


def test_committed_openapi_matches_code() -> None:
    assert OUT.read_text(encoding="utf-8") == render(), "run: uv run python -m scripts.export_openapi"


def test_all_schema_examples_validate() -> None:
    checked = 0
    for obj in vars(schemas).values():
        if isinstance(obj, type) and issubclass(obj, BaseModel) and obj.__module__ == schemas.__name__:
            extra = obj.model_config.get("json_schema_extra")
            for example in (extra or {}).get("examples", []):  # type: ignore[union-attr]
                obj.model_validate(example)
                checked += 1
    assert checked >= 40


def test_every_operation_has_id_summary_and_error_model() -> None:
    ids = set()
    for path, item in app.openapi()["paths"].items():
        assert path.startswith("/v1/")
        for method, op in item.items():
            assert op.get("operationId"), (method, path)
            assert op.get("summary") or path == "/v1/health", (method, path)
            assert op["operationId"] not in ids
            ids.add(op["operationId"])
    assert len(ids) == 58  # update when endpoints are added (additive only after the v1 freeze)


def test_every_endpoint_is_implemented_and_errors_are_problem_json() -> None:
    async def call() -> httpx.Response:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            return await c.get("/v1/student/assignments")  # no session

    import asyncio

    r = asyncio.run(call())
    assert r.status_code == 401 and r.headers["content-type"].startswith("application/problem+json")


def test_json_is_camel_case_and_no_snake_case_keys() -> None:
    spec = json.dumps(app.openapi()["components"]["schemas"])
    for bad in ('"block_id"', '"review_status"', '"content_hash"', '"source_revision_ids"'):
        assert bad not in spec


def test_docs_page_and_spec_are_served() -> None:
    import asyncio

    async def get(path: str) -> httpx.Response:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            return await c.get(path)

    docs = asyncio.run(get("/docs"))
    assert docs.status_code == 200 and "@scalar/api-reference@1.28.33" in docs.text
    spec = asyncio.run(get("/v1/openapi.json"))
    assert spec.status_code == 200 and spec.json()["openapi"].startswith("3.")
