from fastapi import APIRouter

from app.routers import account, lessons, publishing, sources, student

api_router = APIRouter(prefix="/v1")
for _m in (account, sources, lessons, publishing, student):
    api_router.include_router(_m.router)
