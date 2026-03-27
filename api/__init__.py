from fastapi import APIRouter

from api.endpoints.collector.router import collector_router

api_router = APIRouter()

api_router.include_router(
    collector_router,
    prefix="/collections",
    tags=["Collector"],
)
