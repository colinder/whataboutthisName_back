# api/endpoints/crawler/router.py

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from api.endpoints.crawler.schemas import CrawlRequest, CrawlResponse
from api.endpoints.crawler.service import CrawlerService
from api.endpoints.crawler.utils import parse_date_ranges
from database import get_db

crawler_router = APIRouter()


@crawler_router.post("", response_model=CrawlResponse)
async def crawl(
    background_tasks: BackgroundTasks,
    body: CrawlRequest,
    db: Session = Depends(get_db),
):
    """
        크롤링 API

        ## 요청 예시
    ```json
        {
          "target_date": ["2008-01", "2008-01-02", "2008-02-04"]
        }
    ```

        ## 처리 로직
        1. 날짜 파싱 및 중복 제거
           - "2008-01" → 2008-01-01 ~ 2008-01-31 (31일)
           - "2008-01-02" → 무시 (이미 2008-01에 포함)
           - "2008-02-04" → 2008-02-04 (1일)

        2. 각 날짜별 수집
           - 시도별 × 성별 (24개 × 2 = 48개)
           - 월 마지막 날이면 월 전체도 수집 (2개 추가)

        ## 반환
        - 백그라운드 작업으로 실행
        - 즉시 응답 반환
    """

    # 날짜 파싱 및 중복 제거
    dates = parse_date_ranges(body.target_date)
    sorted_dates = sorted(dates)

    print(f"\n{'=' * 60}")
    print(f"📊 크롤링 요청 수신")
    print(f"{'=' * 60}")
    print(f"요청: {body.target_date}")
    print(f"실제 수집: {len(dates)}일")
    print(f"미리보기: {sorted_dates[:5]}")
    print(f"{'=' * 60}\n")

    # 백그라운드 작업 등록
    service = CrawlerService(db)
    background_tasks.add_task(
        service.run_crawl,
        dates=dates,
    )

    return CrawlResponse(
        message="크롤링 시작",
        total_dates=len(dates),
        dates=[d.strftime("%Y-%m-%d") for d in sorted_dates],
    )


@crawler_router.get("/status")
async def get_crawl_status(db: Session = Depends(get_db)):
    """
    크롤링 상태 조회

    ## 반환
    - 총 수집 이력 수
    - 성공/실패 통계
    - 최근 수집 날짜
    """
    from sqlalchemy import func

    from models.crawl_log import CrawlLog

    total = db.query(func.count(CrawlLog.id)).scalar()
    success = (
        db.query(func.count(CrawlLog.id)).filter(CrawlLog.is_success.is_(True)).scalar()
    )
    has_data = (
        db.query(func.count(CrawlLog.id)).filter(CrawlLog.has_result.is_(True)).scalar()
    )

    latest = db.query(CrawlLog).order_by(CrawlLog.crawled_at.desc()).first()

    return {
        "total_logs": total,
        "success_count": success,
        "has_data_count": has_data,
        "latest_crawl": latest.crawled_at if latest else None,
        "latest_date": latest.record_date if latest else None,
    }
