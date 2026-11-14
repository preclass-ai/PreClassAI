from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import install_error_handlers
from app.routers import api_router

DESCRIPTION = """\
PreClass AI backend: teachers import sources, AI drafts a Worksheet/Flashcards, the system links every block to \
its source and flags problems, the teacher approves block by block and publishes an immutable snapshot; \
students answer first, then see the approved explanation.

**Contract status: v0 (draft) — frozen as v1.0.0 on 16/11 morning.** After the freeze fields are only added.

**Conventions**
- Base path `/v1`. JSON is camelCase. Ids are UUIDs. Times are ISO-8601 with offset.
- Auth: server-side session cookie `preclass_session` (HttpOnly). Use `credentials: "include"` and send header \
`X-PreClass-CSRF: 1` on every non-GET request (missing → 403 `CSRF`). Same origin in production (Caddy); in dev use \
Next.js `rewrites` to `/v1`.
- Errors: RFC 9457 `application/problem+json` with a stable `code`. Wrong role → 403 `FORBIDDEN_ROLE`; someone \
else's resource (or another class) → 404.
- Edits carry `version` (optimistic lock) → 409 `VERSION_CONFLICT`. Approvals carry `contentHash` → 409 \
`STALE_REVIEW`.
- Lists are `{items, nextCursor}`; `nextCursor` is always null in v1.
- Handlers currently answer 501 `NOT_IMPLEMENTED`: use the examples (Prism mock) until phases 4-9 land.
"""

TAGS = [
    {"name": "auth", "description": "Login, logout, current user."},
    {"name": "classes", "description": "Teacher's classes, assignments and progress."},
    {"name": "sources", "description": "S01 Source Library: text/DOCX → anchors."},
    {"name": "lessons", "description": "Lessons and revisions."},
    {"name": "generation", "description": "S02 Generate: async AI draft job."},
    {"name": "blocks", "description": "S03 Editor: content blocks."},
    {"name": "provenance", "description": "S03 Source Inspector: block ↔ source links, history, validation."},
    {"name": "validation", "description": "Validation rules VAL-01..09."},
    {"name": "review", "description": "S04 Review Queue and hash-bound approvals."},
    {"name": "publish", "description": "S05 Publish Gate, new revision, withdraw, assignments."},
    {"name": "student", "description": "S07 Student view and attempts (whitelist DTOs)."},
    {"name": "admin", "description": "Audit log (read-only)."},
    {"name": "system", "description": "Health."},
]

app = FastAPI(title="PreClass AI API", version="0.1.0-v0", description=DESCRIPTION, openapi_tags=TAGS)
install_error_handlers(app)

# Same-origin via Caddy in staging/prod; CORS only matters for split-origin dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/v1/health", tags=["system"], operation_id="getHealth", openapi_extra={"security": []})
async def health() -> dict[str, str]:
    return {"status": "ok"}


def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema is None:
        from fastapi.openapi.utils import get_openapi

        schema = get_openapi(title=app.title, version=app.version, description=app.description,
                             routes=app.routes, tags=TAGS)
        schema.setdefault("components", {})["securitySchemes"] = {
            "cookieAuth": {"type": "apiKey", "in": "cookie", "name": "preclass_session"}
        }
        # No global `security`: mock servers (Prism) would demand the HttpOnly cookie a browser cannot set.
        # Which routes need the session is documented in the description and in API_GUIDE.
        app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]
