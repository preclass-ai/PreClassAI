from fastapi import APIRouter

from app.routers import account, guest, habit, lessons, publishing, sources, student

api_router = APIRouter(prefix="/v1")
for _m in (account, guest, sources, lessons, publishing, student, habit):
    api_router.include_router(_m.router)
