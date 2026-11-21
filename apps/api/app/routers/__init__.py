from fastapi import APIRouter

from app.routers import account, guest, habit, insights, lessons, personalization, publishing, sources, student

api_router = APIRouter(prefix="/v1")
for _m in (account, guest, sources, lessons, publishing, student, habit, personalization, insights):
    api_router.include_router(_m.router)
