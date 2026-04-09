from database import get_db
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.endpoints.search.service import SearchService

search_router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> SearchService:
    return SearchService(db)


@search_router.get("")
def search(
    q: str = Query(..., description="검색어 (이름, 패턴, 초성)"),
    city: str | None = Query(None),
    gender: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    service: SearchService = Depends(get_service),
):
    return service.search(q, city, gender, limit)


@search_router.get("/ranking")
def ranking(
    date: str | None = Query(None),
    city: str | None = Query(None),
    gender: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    service: SearchService = Depends(get_service),
):
    return service.ranking(date, city, gender, limit)


@search_router.get("/trend/{name}")
def trend(
    name: str,
    city: str | None = Query(None),
    gender: str | None = Query(None),
    service: SearchService = Depends(get_service),
):
    return service.trend(name, city, gender)


@search_router.get("/statistics")
def statistics(
    year: int | None = Query(None),
    month: int | None = Query(None),
    gender: str | None = Query(None),
    limit: int = Query(200, ge=1, le=200),
    service: SearchService = Depends(get_service),
):
    return service.statistics(year, month, gender, limit)


@search_router.get("/daily")
def daily_statistics(
    date: str = Query(..., description="날짜 (YYYY-MM-DD)"),
    city: str | None = Query(None, description="도시"),
    gender: str | None = Query(None, description="성별 (전체/남자/여자)"),
    service: SearchService = Depends(get_service),
):
    """일별 통계"""
    return service.daily_statistics(date, city, gender)
