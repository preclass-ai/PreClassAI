from fastapi import APIRouter

from app.routers import account, guest, habit, insights, lesson_plans, lessons, personalization, publishing, sources, student

api_router = APIRouter(prefix="/v1")
for _m in (account, guest, sources, lessons, publishing, student, habit, personalization, insights, lesson_plans):
    api_router.include_router(_m.router)
