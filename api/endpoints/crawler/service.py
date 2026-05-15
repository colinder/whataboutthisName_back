# api/endpoints/crawler/service.py

import asyncio
from datetime import date
from typing import Set

from sqlalchemy.orm import Session

from api.endpoints.crawler.court_crawler import CourtNameCrawler
from api.endpoints.crawler.utils import is_last_day_of_month
from models.crawl_log import CrawlLog
from models.enums import CITY_CODE_MAP
from models.name import Name
from models.record import Record


class CrawlerService:
    """크롤러 서비스"""

    def __init__(self, db: Session):
        self.db = db
        self.crawler = CourtNameCrawler()

    async def run_crawl(self, dates: Set[date]):
        """
        여러 날짜 크롤링 실행

        Args:
            dates: 수집할 날짜 set
        """
        sorted_dates = sorted(dates)
        print(f"\n{'=' * 60}")
        print(f"📊 총 {len(sorted_dates)}일 수집 시작")
        print(f"{'=' * 60}\n")

        for target_date in sorted_dates:
            print(f"\n{'=' * 60}")
            print(f"📅 {target_date} 수집 중...")
            print(f"{'=' * 60}")

            await self.crawl_date(target_date)

            print(f"✅ {target_date} 완료\n")

        print(f"\n{'=' * 60}")
        print(f"🎉 모든 수집 완료!")
        print(f"{'=' * 60}\n")

        self.crawler.print_failed_summary()  # ← 여기 한 줄만 추가

    async def crawl_date(self, target_date: date):
        """
        특정 날짜의 데이터 수집

        1. 시도별 × 성별 (24개 × 2 = 48개)
        2. 마지막 날이면 월 전체 (2개 추가)
        """
        tasks = []

        # 1. 시도별 × 성별 수집 (48개)
        print(f"  🔍 시도별 데이터 수집 시작...")

        for city_enum, city_code in CITY_CODE_MAP.items():
            for gender_code in ["1", "2"]:  # 남자, 여자
                tasks.append(
                    self._crawl_regional_data(
                        target_date=target_date,
                        city_code=city_code,
                        city_name=city_enum.value,
                        gender_code=gender_code,
                    )
                )

        # 모든 시도별 데이터 수집
        # await asyncio.gather(*tasks)
        for task in tasks:
            await task

        # 2. 마지막 날이면 월 전체도 수집
        if is_last_day_of_month(target_date):
            print(f"\n  📊 월 마지막 날! 월 전체 수집 시작...")

            monthly_tasks = []
            for gender_code in ["0", "1", "2"]:
                monthly_tasks.append(
                    self._crawl_monthly_data(
                        year=target_date.year,
                        month=target_date.month,
                        gender_code=gender_code,
                        record_date=target_date,  # 마지막 날 기준으로 저장
                    )
                )

            # await asyncio.gather(*monthly_tasks)
            for task in monthly_tasks:
                await task

    async def _crawl_regional_data(
        self, target_date: date, city_code: str, city_name: str, gender_code: str
    ):
        """시도별 데이터 수집"""
        gender_name = "남자" if gender_code == "1" else "여자"

        # API 호출
        data = self.crawler.fetch_data_by_date(
            target_date=target_date, city_code=city_code, gender_code=gender_code
        )

        if data and "data" in data and len(data["data"]) > 0:
            # ✅ 실제 건수 계산
            total_count = sum(item["건수"] for item in data["data"])
            name_count = len(data["data"])

            # 데이터 있음
            await self._save_to_db(
                record_date=target_date,
                city=city_name,
                gender=gender_name,
                data=data["data"],
                is_success=True,
                has_result=True,
            )
            print(
                f"    ✅ {city_name} × {gender_name}: {name_count}개 이름, 총 {total_count}건"
            )
        else:
            # 데이터 없음 (이력만 기록)
            await self._save_empty_log(
                record_date=target_date, city=city_name, gender=gender_name
            )
            print(f"    ⚠️ {city_name} × {gender_name}: 데이터 없음")

    async def _crawl_monthly_data(
        self,
        year: int,
        month: int,
        gender_code: str,
        record_date: date,
    ):
        """월 전체 데이터 수집 (24개 시도 모두 포함)"""
        if gender_code == "0":
            gender_name = "전체"
        elif gender_code == "1":
            gender_name = "남자"
        else:
            gender_name = "여자"

        # API 호출
        data = self.crawler.fetch_data_by_month(
            year=year, month=month, gender_code=gender_code
        )

        if data and "data" in data and len(data["data"]) > 0:
            total_count = sum(item["건수"] for item in data["data"])
            name_count = len(data["data"])

            ## 데이터 있음
            await self._save_to_db(
                record_date=record_date,
                city="전체",
                gender=gender_name,  # ✅ "전체" 가능
                data=data["data"],
                is_success=True,
                has_result=True,
            )
            print(
                f"    ✅ {year}년 {month}월 전체 × {gender_name}: {name_count}개 이름, 총 {total_count}건"
            )
        else:
            # 데이터 없음
            await self._save_empty_log(
                record_date=record_date, city="전체", gender=gender_name
            )
            print(f"    ⚠️ {year}년 {month}월 전체 × {gender_name}: 데이터 없음")

    async def _save_to_db(
        self,
        record_date: date,
        city: str,
        gender: str,
        data: list,
        is_success: bool,
        has_result: bool,
    ):
        """DB 저장"""

        # 1. crawl_log 생성 또는 조회
        crawl_log = (
            self.db.query(CrawlLog)
            .filter(
                CrawlLog.record_date == record_date,
                CrawlLog.city == city,
                CrawlLog.gender == gender,
            )
            .first()
        )

        if crawl_log:
            # 이미 존재하면 업데이트
            crawl_log.is_success = is_success
            crawl_log.has_result = has_result
            crawl_log.total_count = sum(item["건수"] for item in data)
        else:
            # 새로 생성
            crawl_log = CrawlLog(
                record_date=record_date,
                city=city,
                gender=gender,
                is_success=is_success,
                has_result=has_result,
                total_count=sum(item["건수"] for item in data),
            )
            self.db.add(crawl_log)

        self.db.flush()  # ID 생성

        # 2. 기존 records 삭제 (재수집 시)
        self.db.query(Record).filter(Record.crawl_log_id == crawl_log.id).delete()

        # 3. records 저장
        for item in data:
            name_text = item["이름"]
            count = item["건수"]

            # name 조회 또는 생성
            name = self.db.query(Name).filter(Name.name == name_text).first()
            if not name:
                name = Name(name=name_text)
                self.db.add(name)
                self.db.flush()

            # record 생성
            record = Record(crawl_log_id=crawl_log.id, name_id=name.id, count=count)
            self.db.add(record)

        # 4. 커밋
        self.db.commit()

    async def _save_empty_log(self, record_date: date, city: str, gender: str):
        """데이터 없음 이력만 기록"""

        crawl_log = (
            self.db.query(CrawlLog)
            .filter(
                CrawlLog.record_date == record_date,
                CrawlLog.city == city,
                CrawlLog.gender == gender,
            )
            .first()
        )

        if crawl_log:
            # 이미 존재하면 업데이트
            crawl_log.is_success = True
            crawl_log.has_result = False
            crawl_log.total_count = 0
        else:
            # 새로 생성
            crawl_log = CrawlLog(
                record_date=record_date,
                city=city,
                gender=gender,
                is_success=True,
                has_result=False,  # ✅ 데이터 없음
                total_count=0,
            )
            self.db.add(crawl_log)

        self.db.commit()
