"""
DB 저장 서비스
- 크롤링 결과를 crawl_logs, names, records에 저장
"""

from datetime import date, datetime

from sqlalchemy import select

from database import SessionLocal
from models.crawl_log import CrawlLog
from models.name import Name
from models.record import Record


def save_crawl_results(all_results: list[dict]):
    """
    크롤링 결과를 한 번에 DB에 저장

    all_results 형태:
    [
        {
            "name": "서준",
            "count": "3",
            "city": "서울특별시",
            "gender": "남자",
            "record_date": date(2025, 3, 5),
        },
        ...
    ]
    """

    if not all_results:
        return

    # 저장할 데이터 출력
    print("\n========== DB 저장 데이터 확인 ==========")
    print(f"총 {len(all_results)}건")

    db = SessionLocal()
    try:
        # 1. 크롤링 로그별로 그룹핑 (날짜+도시+성별)
        log_groups = {}
        for item in all_results:
            key = (item["record_date"], item["city"], item["gender"])
            if key not in log_groups:
                log_groups[key] = []
            log_groups[key].append(item)

        # 저장되는 데이터 출력
        for (record_date, city, gender), items in log_groups.items():
            total = sum(int(item["count"]) for item in items if item["count"])
            print(f"\n[crawl_log] {record_date} / {city} / {gender}")
            print(f"  이름 수: {len(items)}개, 총 건수: {total}")
            for item in items:
                print(f"  [record] {item['name']:10s} → {item['count']}건")

        print("==========================================\n")

        # 2. 이름 캐시: 전체 이름을 한 번에 처리
        all_names = list(set(item["name"] for item in all_results))
        name_cache = {}

        # 기존 이름 조회
        existing_names = (
            db.execute(select(Name).where(Name.name.in_(all_names))).scalars().all()
        )
        for n in existing_names:
            name_cache[n.name] = n

        # 새 이름 생성
        new_names = [n for n in all_names if n not in name_cache]
        for name_str in new_names:
            name_obj = Name(name=name_str)
            db.add(name_obj)
        db.flush()  # id 생성

        # 캐시 갱신
        if new_names:
            new_name_objs = (
                db.execute(select(Name).where(Name.name.in_(new_names))).scalars().all()
            )
            for n in new_name_objs:
                name_cache[n.name] = n

        # 3. 크롤링 로그 + 레코드 저장
        for (record_date, city, gender), items in log_groups.items():
            # 기존 로그 확인 (중복 방지)
            existing_log = db.execute(
                select(CrawlLog).where(
                    CrawlLog.record_date == record_date,
                    CrawlLog.city == city,
                    CrawlLog.gender == gender,
                )
            ).scalar_one_or_none()

            if existing_log:
                # 기존 로그가 있으면 records 삭제 후 재삽입
                db.query(Record).filter(Record.crawl_log_id == existing_log.id).delete()
                crawl_log = existing_log
                crawl_log.is_success = True
                crawl_log.has_result = len(items) > 0
                crawl_log.total_count = len(items)
                crawl_log.crawled_at = datetime.now()
            else:
                # 새 로그 생성
                crawl_log = CrawlLog(
                    record_date=record_date,
                    city=city,
                    gender=gender,
                    is_success=True,
                    has_result=len(items) > 0,
                    total_count=len(items),
                    crawled_at=datetime.now(),
                )
                db.add(crawl_log)
                db.flush()  # id 생성

            # 레코드 저장
            for item in items:
                name_obj = name_cache[item["name"]]
                count = int(item["count"]) if item["count"] else 0
                record = Record(
                    crawl_log_id=crawl_log.id,
                    name_id=name_obj.id,
                    count=count,
                )
                db.add(record)

        db.commit()
        print(f"DB 저장 완료: {len(log_groups)}개 로그, {len(all_results)}개 레코드")

    except Exception as e:
        db.rollback()
        print(f"DB 저장 실패: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


def save_empty_crawl_log(record_date: date, city: str, gender: str):
    """
    데이터가 없는 경우에도 크롤링 이력을 남김
    """
    db = SessionLocal()
    try:
        existing = db.execute(
            select(CrawlLog).where(
                CrawlLog.record_date == record_date,
                CrawlLog.city == city,
                CrawlLog.gender == gender,
            )
        ).scalar_one_or_none()

        if not existing:
            crawl_log = CrawlLog(
                record_date=record_date,
                city=city,
                gender=gender,
                is_success=True,
                has_result=False,
                total_count=0,
                crawled_at=datetime.now(),
            )
            db.add(crawl_log)
        else:
            existing.is_success = True
            existing.has_result = False
            existing.total_count = 0
            existing.crawled_at = datetime.now()

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"빈 로그 저장 실패: {e}")
    finally:
        db.close()
