from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadinessChecks(BaseModel):
    database: bool
    redis: bool
    storage: bool


class ReadinessResponse(BaseModel):
    status: Literal["ok", "unhealthy"]
    checks: ReadinessChecks
