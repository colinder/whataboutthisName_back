from fastapi import APIRouter, BackgroundTasks, Depends
from models.Enums import CityEnum, GenderEnum
from pydantic import BaseModel

from api.endpoints.collector.service import CollectorService

from ..utils import parse_date_input

collector_router = APIRouter()


class CrawlRangeRequest(BaseModel):
    target_date: list[str]  # date → str로 변경
    city: list[CityEnum] | None = None
    gender: list[GenderEnum] | None = None


@collector_router.get("")
async def hello():
    return {"message": "ok"}


@collector_router.post("")
async def crawl(
    background_tasks: BackgroundTasks,
    body: CrawlRangeRequest,
    service: CollectorService = Depends(CollectorService),
):
    all_dates = []
    for part in body.target_date:
        all_dates.extend(parse_date_input(part.strip()))
    all_dates = sorted(set(all_dates))
    print(all_dates)
    background_tasks.add_task(
        CollectorService.run_crawl,
        dates=all_dates,
        cities=body.city,
        genders=body.gender,
    )

    return {"message": "ok"}
