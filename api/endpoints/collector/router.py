from datetime import date

from fastapi import APIRouter, Depends
from models.Enums import CityEnum, GenderEnum
from pydantic import BaseModel

from api.endpoints.collector.service import CollectorService

collector_router = APIRouter()


class CrawlRequest(BaseModel):
    target_date: list[date]
    city: list[CityEnum] | None = None
    gender: list[GenderEnum] | None = None


@collector_router.post("")
async def crawl(
    body: CrawlRequest,
    service: CollectorService = Depends(CollectorService),
):
    await service.crawl(
        dates=body.target_date,
        cities=body.city,
        genders=body.gender,
    )

    return {"message": "ok"}
