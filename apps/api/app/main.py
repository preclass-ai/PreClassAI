from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import install_error_handlers

app = FastAPI(title="PreClass AI API", version="0.1.0", root_path="")
install_error_handlers(app)

# Same-origin via Caddy in staging/prod; CORS only matters for split-origin dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/v1/health", tags=["system"], operation_id="getHealth")
async def health() -> dict[str, str]:
    return {"status": "ok"}
