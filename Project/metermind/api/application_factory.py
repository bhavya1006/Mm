"""Builds the service. Nothing else in the platform builds an application."""

from fastapi import FastAPI

from config import constants
from metermind.api import schemas
from metermind.api.middleware import FixedWindowRateLimiter, RequestLogMiddleware, \
    add_cross_origin_policy
from metermind.api.repository import InMemoryReadingRepository
from metermind.api.routers import assistant as assistant_router
from metermind.api.routers import readings as readings_router
from metermind.api.routers import screening as screening_router
from metermind.api.routers import user_accounts as user_accounts_router
from metermind.api.sql_repository import SqlReadingRepository

API_PREFIX = "/api/v1"
SERVICE_NAME = "metermind"


def read_health():
    return schemas.HealthReply(service=SERVICE_NAME, status="up")


def choose_reading_repository(database_path):
    if database_path:
        return SqlReadingRepository(database_path)
    return InMemoryReadingRepository()


def build_application(database_path=""):
    application = FastAPI(title=SERVICE_NAME)

    @application.get(f"{API_PREFIX}/health", response_model=schemas.HealthReply, tags=["health"])
    def health_route():
        return read_health()

    readings_router.reading_repository = choose_reading_repository(database_path)

    application.include_router(readings_router.router, prefix=API_PREFIX)
    application.include_router(user_accounts_router.router, prefix=API_PREFIX)
    application.include_router(screening_router.router, prefix=API_PREFIX)
    application.include_router(assistant_router.router, prefix=API_PREFIX)

    application.add_middleware(RequestLogMiddleware)
    application.add_middleware(FixedWindowRateLimiter)
    add_cross_origin_policy(application)

    return application


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(build_application(constants.ORM_DATABASE_PATH), host="127.0.0.1", port=8000)
