from fastapi import APIRouter

from api.endpoints import collector_router, search_router

api_router = APIRouter()

api_router.include_router(
    collector_router,
    prefix="/collections",
    tags=["Collector"],
)

api_router.include_router(
    search_router,
    prefix="/search",
    tags=["Search"],
)
