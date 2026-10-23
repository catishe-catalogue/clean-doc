from fastapi import APIRouter

from app.api.v1.endpoints import health

api_v1_router = APIRouter()

# Служебные маршруты Slice 0
api_v1_router.include_router(health.router, tags=["health"])

# Точка расширения Slice 1:
# from app.api.v1.endpoints import convert
# api_v1_router.include_router(convert.router, prefix="/convert", tags=["convert"])
