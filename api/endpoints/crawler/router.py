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

@crawler_router.post("/recrawl")
async def recrawl_specific_dates(
    background_tasks: BackgroundTasks,
    body: CrawlRequest,  # 기존 스키마 재사용
    db: Session = Depends(get_db)
):
    """
    특정 날짜 재크롤링
    
    기존 데이터를 삭제하고 새로 크롤링합니다.
    
    Request:
    {
        "target_date": ["2009-02-12", "2009-02-13"]
    }
    """
    from api.endpoints.crawler.utils import parse_date_ranges
    from api.endpoints.crawler.service import CrawlerService
    from models.crawl_log import CrawlLog
    from models.record import Record
    
    # 날짜 파싱
    dates = parse_date_ranges(body.target_date)
    sorted_dates = sorted(dates)
    
    print(f"\n{'='*60}")
    print(f"🔄 재크롤링 요청")
    print(f"{'='*60}")
    print(f"날짜: {sorted_dates}")
    print(f"{'='*60}\n")
    
    # 기존 데이터 삭제
    for target_date in sorted_dates:
        print(f"🗑️ {target_date} 기존 데이터 삭제 중...")
        
        # 해당 날짜의 crawl_log_id 조회
        crawl_log_ids = db.query(CrawlLog.id).filter(
            CrawlLog.record_date == target_date
        ).all()
        
        crawl_log_ids = [row.id for row in crawl_log_ids]
        
        if crawl_log_ids:
            # records 삭제
            deleted_records = db.query(Record).filter(
                Record.crawl_log_id.in_(crawl_log_ids)
            ).delete(synchronize_session=False)
            
            # crawl_logs 삭제
            deleted_logs = db.query(CrawlLog).filter(
                CrawlLog.record_date == target_date
            ).delete(synchronize_session=False)
            
            db.commit()
            
            print(f"  ✅ crawl_logs: {deleted_logs}개 삭제")
            print(f"  ✅ records: {deleted_records}개 삭제")
        else:
            print(f"  ⚠️ 기존 데이터 없음")
    
    # 백그라운드 작업으로 재크롤링
    service = CrawlerService(db)
    background_tasks.add_task(
        service.run_crawl,
        dates=dates
    )
    
    return {
        "message": "재크롤링 시작",
        "total_dates": len(dates),
        "dates": [d.strftime("%Y-%m-%d") for d in sorted_dates]
    }