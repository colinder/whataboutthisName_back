from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.endpoints.collector.service import CollectorService
from database import get_db
from models.crawl_log import CrawlLog
from models.Enums import CityEnum, GenderEnum

from ..utils import parse_date_input

collector_router = APIRouter()


class CrawlRangeRequest(BaseModel):
    target_date: list[str]
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
    """기존 크롤링 API (변경 없음)"""
    all_dates = []
    for part in body.target_date:
        all_dates.extend(parse_date_input(part.strip()))
    all_dates = sorted(set(all_dates))

    background_tasks.add_task(
        CollectorService.run_crawl,
        dates=all_dates,
        cities=body.city,
        genders=body.gender,
    )

    return {"message": "ok"}


@collector_router.post("/auto")
async def auto_crawl(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    service: CollectorService = Depends(CollectorService),
):
    """
    자동 크롤링 (2일 전 데이터)

    - 매일 자동 실행용
    - 2일 전 날짜 자동 계산
    - 중복 크롤링 방지
    - 전체 도시, 전체 성별 크롤링
    """

    # 1. 2일 전 날짜 계산
    target_date = datetime.now().date() - timedelta(days=2)

    # 2. 전체 도시, 전체 성별
    cities = [city for city in CityEnum]
    genders = [gender for gender in GenderEnum]

    # 3. 중복 체크
    duplicates = []
    new_tasks = []

    for city in cities:
        city_value = city.value

        for gender in genders:
            gender_value = gender.value

            existing = (
                db.query(CrawlLog)
                .filter(
                    CrawlLog.record_date == target_date,
                    CrawlLog.city == city_value,
                    CrawlLog.gender == gender_value,
                    CrawlLog.is_success.is_(True),
                )
                .first()
            )

            if existing:
                duplicates.append(
                    {
                        "city": city_value,
                        "gender": gender_value,
                        "crawled_at": existing.crawled_at.strftime("%Y-%m-%d %H:%M:%S")
                        if existing.crawled_at
                        else None,
                    }
                )
            else:
                new_tasks.append({"city": city_value, "gender": gender_value})

    # 4. 모두 중복인 경우
    if not new_tasks:
        return {
            "status": "skipped",
            "message": f"{target_date.strftime('%Y-%m-%d')} 데이터는 이미 크롤링되었습니다",
            "target_date": target_date.strftime("%Y-%m-%d"),
            "duplicate_count": len(duplicates),
            "new_tasks": 0,
        }

    # 5. 백그라운드 크롤링 실행
    background_tasks.add_task(
        CollectorService.run_crawl,
        dates=[target_date],
        cities=None,  # 전체
        genders=None,  # 전체
    )

    return {
        "status": "started",
        "message": f"{target_date.strftime('%Y-%m-%d')} 크롤링 시작",
        "target_date": target_date.strftime("%Y-%m-%d"),
        "new_tasks": len(new_tasks),
        "duplicate_count": len(duplicates),
    }


@collector_router.post("/validate")
async def validate_crawl(
    body: CrawlRangeRequest,
    db: Session = Depends(get_db),
):
    """
    크롤링 검증 (실제 실행 없음)

    - 중복 여부 확인
    - 날짜 유효성 확인
    - 실행 전 미리보기
    """

    # 1. 날짜 파싱
    all_dates = []
    for part in body.target_date:
        all_dates.extend(parse_date_input(part.strip()))
    all_dates = sorted(set(all_dates))

    if not all_dates:
        raise HTTPException(status_code=400, detail="유효한 날짜가 없습니다")

    # 2. 날짜 검증 (2일 전까지만)
    today = datetime.now().date()
    max_date = today - timedelta(days=2)

    invalid_dates = []
    valid_dates = []

    for date in all_dates:
        if date > max_date:
            invalid_dates.append(date.strftime("%Y-%m-%d"))
        else:
            valid_dates.append(date)

    # 3. 중복 체크
    cities = body.city if body.city else [city for city in CityEnum]
    genders = body.gender if body.gender else [gender for gender in GenderEnum]

    duplicates = []
    new_tasks = []

    for target_date in valid_dates:
        for city in cities:
            city_value = city.value if isinstance(city, CityEnum) else city

            for gender in genders:
                gender_value = (
                    gender.value if isinstance(gender, GenderEnum) else gender
                )

                existing = (
                    db.query(CrawlLog)
                    .filter(
                        CrawlLog.record_date == target_date,
                        CrawlLog.city == city_value,
                        CrawlLog.gender == gender_value,
                        CrawlLog.is_success.is_(True),
                    )
                    .first()
                )

                if existing:
                    duplicates.append(
                        {
                            "date": target_date.strftime("%Y-%m-%d"),
                            "city": city_value,
                            "gender": gender_value,
                            "crawled_at": existing.crawled_at.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                            if existing.crawled_at
                            else None,
                        }
                    )
                else:
                    new_tasks.append(
                        {
                            "date": target_date.strftime("%Y-%m-%d"),
                            "city": city_value,
                            "gender": gender_value,
                        }
                    )

    return {
        "valid_dates": [d.strftime("%Y-%m-%d") for d in valid_dates],
        "invalid_dates": invalid_dates,
        "new_tasks_count": len(new_tasks),
        "duplicate_count": len(duplicates),
        "new_tasks": new_tasks[:10]
        if len(new_tasks) > 10
        else new_tasks,  # 최대 10개만 표시
        "duplicates": duplicates[:10]
        if len(duplicates) > 10
        else duplicates,  # 최대 10개만 표시
        "total_new_tasks": len(new_tasks),
        "total_duplicates": len(duplicates),
        "can_proceed": len(new_tasks) > 0,
    }


@collector_router.get("/status/{date}")
async def get_crawl_status(date: str, db: Session = Depends(get_db)):
    """특정 날짜의 크롤링 상태 조회"""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 날짜 형식 (YYYY-MM-DD)")

    logs = (
        db.query(CrawlLog)
        .filter(CrawlLog.record_date == target_date)
        .order_by(CrawlLog.crawled_at.desc())
        .all()
    )

    if not logs:
        return {
            "date": date,
            "status": "not_crawled",
            "message": "크롤링 기록이 없습니다",
            "total": 0,
            "success": 0,
            "failed": 0,
            "details": [],
        }

    total = len(logs)
    success = sum(1 for log in logs if log.is_success)

    return {
        "date": date,
        "status": "completed" if success == total else "partial",
        "total": total,
        "success": success,
        "failed": total - success,
        "details": [
            {
                "city": log.city,
                "gender": log.gender,
                "is_success": log.is_success,
                "has_result": log.has_result,
                "total_count": log.total_count,
                "crawled_at": log.crawled_at.strftime("%Y-%m-%d %H:%M:%S")
                if log.crawled_at
                else None,
            }
            for log in logs
        ],
    }
