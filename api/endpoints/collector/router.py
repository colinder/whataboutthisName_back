from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.endpoints.collector.service import CollectorService
from models.Enums import CityEnum, GenderEnum

collector_router = APIRouter()


class CrawlRequest(BaseModel):
    target_date: date
    city: CityEnum
    gender: GenderEnum = GenderEnum.ALL


@collector_router.post("")
async def crawl(
    body: CrawlRequest,
    service: CollectorService = Depends(CollectorService),
):
    await service.crawl(
        start_date=body.target_date,
        end_date=body.target_date,
        city=body.city.value,
        gender=body.gender,
    )

    return {"message": "ok"}
