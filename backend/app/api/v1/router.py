from fastapi import APIRouter

from app.api.v1.endpoints import auth, billing, convert, health

api_v1_router = APIRouter()

# Служебные маршруты Slice 0
api_v1_router.include_router(health.router, tags=["health"])

# Маршруты конвертации Slice 1
api_v1_router.include_router(convert.router, prefix="/convert", tags=["convert"])

# Маршруты аутентификации Slice 2
api_v1_router.include_router(auth.router)

# Маршруты биллинга и B2B Slice 3
api_v1_router.include_router(billing.router)
