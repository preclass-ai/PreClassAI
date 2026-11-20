from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import csrf_middleware, current_user
from app.config import get_settings
from app.db.session import get_db
from app.errors import ApiError, install_error_handlers
from app.generation import recover_after_restart
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
- All routes are implemented; Prism (`openapi/openapi.json`) is only for frontend work without a running API.
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

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await recover_after_restart()  # RUNNING jobs cannot survive a restart
    yield


app = FastAPI(
    lifespan=lifespan,
    title="PreClass AI API", version="0.1.0-v0", description=DESCRIPTION, openapi_tags=TAGS,
    docs_url=None, redoc_url=None, openapi_url=None,  # /docs (Scalar) and /v1/openapi.json are our own guarded routes (below)
)
install_error_handlers(app)
app.middleware("http")(csrf_middleware)


@app.middleware("http")
async def security_headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    path = request.url.path
    if path.startswith("/v1/") and path not in ("/v1/health", "/v1/openapi.json"):
        resp.headers["Cache-Control"] = "no-store"  # responses carry user data: never cached by browsers or proxies
    return resp


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


@app.head("/v1/health", include_in_schema=False)  # UptimeRobot (free) probes with HEAD; kept out of the schema: one operationId
async def health_head() -> Response:
    return Response(status_code=200)


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


SCALAR_VERSION = "1.28.33"  # pinned CDN version
_DOCS_HTML = (
    '<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>PreClass API</title>'
    '<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
    '<script id="api-reference" data-url="/v1/openapi.json"></script>'
    f'<script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference@{SCALAR_VERSION}"></script></body></html>'
)


async def docs_guard(request: Request, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
    """DOCS_ACCESS: open (anyone), staff (logged-in TEACHER/REVIEWER/ADMIN), off (404)."""
    mode = get_settings().docs_mode
    if mode == "off":
        raise ApiError(404, "NOT_FOUND", "Không tìm thấy")
    if mode == "staff":
        user = await current_user(request, db)
        if user.role not in ("TEACHER", "REVIEWER", "ADMIN"):
            raise ApiError(404, "NOT_FOUND", "Không tìm thấy")


@app.get("/v1/openapi.json", include_in_schema=False, dependencies=[Depends(docs_guard)])
async def openapi_json() -> JSONResponse:
    return JSONResponse(app.openapi())


@app.get("/docs", include_in_schema=False, dependencies=[Depends(docs_guard)])
async def docs() -> HTMLResponse:
    return HTMLResponse(_DOCS_HTML)
