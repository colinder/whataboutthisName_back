from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.endpoints.search.service import SearchService
from database import get_db

search_router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> SearchService:
    return SearchService(db)


@search_router.get("")
async def search_names(
    q: str = Query(..., min_length=1, description="검색어"),
    service: SearchService = Depends(get_service),
):
    """
    이름 검색

    지원 패턴:
    - 글자 수: *, **, ***
    - 초성: ㄷ, ㅈㄱ, ㅅㅎㅁ
    - 와일드카드: ㄷ*, *ㄴ*, *ㅅ**
    - 일반: 민준, 서연
    """
    data = service.search_names(q)

    return {
        "query": q,
        "type": data["type"],
        "count": len(data["results"]),
        "results": data["results"],
    }


# @search_router.get("")
# def search(
#     q: str = Query(..., description="검색어 (이름, 패턴, 초성)"),
#     city: str | None = Query(None),
#     gender: str | None = Query(None),
#     limit: int = Query(50, ge=1, le=200),
#     service: SearchService = Depends(get_service),
# ):
#     return service.search(q, city, gender, limit)


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


@search_router.get("/crawl-status")
def crawl_status(
    year: int = Query(..., description="연도"),
    service: SearchService = Depends(get_service),
):
    """연도별 수집 현황"""
    return service.crawl_status(year)


@search_router.get("/yearly")
def yearly_statistics(
    service: SearchService = Depends(get_service),
):
    """연도별 출생아 수 추이"""
    return service.yearly_statistics()


@search_router.get("/name-rank/{name}")
def name_yearly_rank(
    name: str,
    service: SearchService = Depends(get_service),
):
    """특정 이름의 연도별 순위 및 동명이인 수"""
    return service.name_yearly_rank(name)


@search_router.get("/name-trend/{name}")
def name_yearly_trend(
    name: str,
    service: SearchService = Depends(get_service),
):
    """특정 이름의 연도별 추이"""
    return service.name_yearly_trend(name)


@search_router.get("/name-gender/{name}")
def name_gender_stats(
    name: str,
    service: SearchService = Depends(get_service),
):
    """특정 이름의 성별 분포"""
    return service.name_gender_stats(name)


@search_router.get("/overview")
async def get_data_overview(
    service: SearchService = Depends(get_service),
):
    return service.get_data_overview()
