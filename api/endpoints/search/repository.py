from models.crawl_log import CrawlLog
from models.name import Name
from models.record import Record
from sqlalchemy import func, select
from sqlalchemy.orm import Session


class SearchRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_statistics_combined(
        self,
        year: int | None,
        month: int | None,
        gender: str | None,
        limit: int,
        exclude_etc: bool = True,
    ):
        """전체 선택 시 남자+여자 합산"""
        if not gender or gender == "전체":
            # 남자 + 여자 합산
            stmt = (
                select(
                    Name.name,
                    func.sum(Record.count).label("total_count"),
                )
                .join(Record, Record.name_id == Name.id)
                .join(CrawlLog, CrawlLog.id == Record.crawl_log_id)
                .where(CrawlLog.gender.in_(["남자", "여자"]))
            )
        else:
            stmt = (
                select(
                    Name.name,
                    func.sum(Record.count).label("total_count"),
                )
                .join(Record, Record.name_id == Name.id)
                .join(CrawlLog, CrawlLog.id == Record.crawl_log_id)
                .where(CrawlLog.gender == gender)
            )

        stmt = self._apply_city_filter(stmt, None)

        if year:
            stmt = stmt.where(func.extract("year", CrawlLog.record_date) == year)
        if month:
            stmt = stmt.where(func.extract("month", CrawlLog.record_date) == month)
        if exclude_etc:
            stmt = stmt.where(Name.name != "기타")

        stmt = (
            stmt.group_by(Name.name)
            .order_by(func.sum(Record.count).desc())
            .limit(limit)
        )

        return self.db.execute(stmt).all()

    def get_name_gender_stats(self, name: str):
        """특정 이름의 성별 전체 건수"""
        stmt = (
            select(
                CrawlLog.gender,
                func.sum(Record.count).label("total_count"),
            )
            .select_from(Record)
            .join(Name, Name.id == Record.name_id)
            .join(CrawlLog, CrawlLog.id == Record.crawl_log_id)
            .where(Name.name == name)
            .where(CrawlLog.city == "전체")
            .where(CrawlLog.gender.in_(["남자", "여자"]))
            .group_by(CrawlLog.gender)
        )

        return self.db.execute(stmt).all()

    def get_name_yearly_rank(self, name: str):
        """특정 이름의 연도별 순위를 한 번의 쿼리로 계산"""

        # 서브쿼리: 연도/성별별 이름 순위
        subq = (
            select(
                func.extract("year", CrawlLog.record_date).label("year"),
                CrawlLog.gender,
                Name.name,
                func.sum(Record.count).label("total_count"),
                func.rank()
                .over(
                    partition_by=[
                        func.extract("year", CrawlLog.record_date),
                        CrawlLog.gender,
                    ],
                    order_by=func.sum(Record.count).desc(),
                )
                .label("rank"),
            )
            .select_from(Record)
            .join(Name, Name.id == Record.name_id)
            .join(CrawlLog, CrawlLog.id == Record.crawl_log_id)
            .where(CrawlLog.city == "전체")
            .where(Name.name != "기타")
            .group_by(
                func.extract("year", CrawlLog.record_date),
                CrawlLog.gender,
                Name.name,
            )
        ).subquery()

        # 해당 이름만 필터
        stmt = (
            select(
                subq.c.year,
                subq.c.gender,
                subq.c.total_count,
                subq.c.rank,
            )
            .where(subq.c.name == name)
            .order_by(subq.c.year.desc(), subq.c.gender)
        )

        return self.db.execute(stmt).all()

    def get_yearly_total_by_gender(self):
        """연도별/성별 전체 출생아 수 (기타 포함)"""
        stmt = (
            select(
                func.extract("year", CrawlLog.record_date).label("year"),
                CrawlLog.gender,
                func.sum(Record.count).label("total_count"),
            )
            .select_from(Record)
            .join(CrawlLog, CrawlLog.id == Record.crawl_log_id)
            .where(CrawlLog.city == "전체")
            .group_by(
                func.extract("year", CrawlLog.record_date),
                CrawlLog.gender,
            )
            .order_by(func.extract("year", CrawlLog.record_date))
        )

        return self.db.execute(stmt).all()

    def get_name_rank_in_year(self, name: str, year: int, gender: str):
        """특정 연도/성별에서 해당 이름의 순위"""
        stmt = (
            select(
                Name.name,
                func.sum(Record.count).label("total_count"),
            )
            .select_from(Record)
            .join(Name, Name.id == Record.name_id)
            .join(CrawlLog, CrawlLog.id == Record.crawl_log_id)
            .where(func.extract("year", CrawlLog.record_date) == year)
            .where(CrawlLog.gender == gender)
            .where(CrawlLog.city == "전체")
            .where(Name.name != "기타")
            .group_by(Name.name)
            .order_by(func.sum(Record.count).desc())
        )

        results = self.db.execute(stmt).all()

        for i, row in enumerate(results):
            if row.name == name:
                return i + 1

        return None

    def get_yearly_statistics(self):
        """연도별 전체/남자/여자 출생아 수"""
        stmt = (
            select(
                func.extract("year", CrawlLog.record_date).label("year"),
                CrawlLog.gender,
                func.sum(Record.count).label("total_count"),
            )
            .select_from(Record)
            .join(CrawlLog, CrawlLog.id == Record.crawl_log_id)
            .where(CrawlLog.city == "전체")
            .group_by(
                func.extract("year", CrawlLog.record_date),
                CrawlLog.gender,
            )
            .order_by(func.extract("year", CrawlLog.record_date))
        )

        return self.db.execute(stmt).all()

    def get_crawl_status_by_year(self, year: int):
        """연도별 수집 현황 (날짜별 수집 완료 여부)"""
        stmt = (
            select(
                CrawlLog.record_date,
                func.count(CrawlLog.id).label("log_count"),
                func.bool_and(CrawlLog.is_success).label("all_success"),
            )
            .where(func.extract("year", CrawlLog.record_date) == year)
            .group_by(CrawlLog.record_date)
            .order_by(CrawlLog.record_date)
        )

        return self.db.execute(stmt).all()

    def _apply_city_filter(self, stmt, city: str | None):
        if not city or city == "전체":
            stmt = stmt.where(CrawlLog.city == "전체")
        else:
            stmt = stmt.where(CrawlLog.city == city)
        return stmt

    def _apply_gender_filter(self, stmt, gender: str | None):
        """공통 성별 필터"""
        if not gender or gender == "전체":
            stmt = stmt.where(CrawlLog.gender == "전체")
        else:
            stmt = stmt.where(CrawlLog.gender == gender)
        return stmt

    def get_statistics(
        self,
        year: int | None,
        month: int | None,
        gender: str | None,
        limit: int,
        exclude_etc: bool = True,
    ):
        stmt = (
            select(
                Name.name,
                func.sum(Record.count).label("total_count"),
            )
            .join(Record, Record.name_id == Name.id)
            .join(CrawlLog, CrawlLog.id == Record.crawl_log_id)
        )

        if year:
            stmt = stmt.where(func.extract("year", CrawlLog.record_date) == year)
        if month:
            stmt = stmt.where(func.extract("month", CrawlLog.record_date) == month)

        stmt = self._apply_gender_filter(stmt, gender)

        if exclude_etc:
            stmt = stmt.where(Name.name != "기타")

        stmt = (
            stmt.group_by(Name.name)
            .order_by(func.sum(Record.count).desc())
            .limit(limit)
        )

        return self.db.execute(stmt).all()

    def search_by_pattern(
        self, name_filter, city: str | None, gender: str | None, limit: int
    ):
        stmt = (
            select(
                Name.name,
                func.coalesce(func.sum(Record.count), 0).label("total_count"),
            )
            .join(Record, Record.name_id == Name.id)
            .join(CrawlLog, CrawlLog.id == Record.crawl_log_id)
            .where(name_filter)
        )

        stmt = self._apply_city_filter(stmt, city)
        stmt = self._apply_gender_filter(stmt, gender)

        stmt = (
            stmt.group_by(Name.id, Name.name)
            .order_by(func.sum(Record.count).desc().nullslast())
            .limit(limit)
        )

        return self.db.execute(stmt).all()

    def search_by_name(
        self, name: str, city: str | None, gender: str | None, limit: int
    ):
        stmt = (
            select(
                Name.name,
                func.coalesce(func.sum(Record.count), 0).label("total_count"),
            )
            .join(Record, Record.name_id == Name.id)
            .join(CrawlLog, CrawlLog.id == Record.crawl_log_id)
            .where(Name.name.ilike(f"%{name}%"))
        )

        stmt = self._apply_city_filter(stmt, city)
        stmt = self._apply_gender_filter(stmt, gender)

        stmt = (
            stmt.group_by(Name.id, Name.name)
            .order_by(func.sum(Record.count).desc().nullslast())
            .limit(limit)
        )

        return self.db.execute(stmt).all()

    def get_statistics_with_filters(
        self,
        year: int | None,
        month: int | None,
        gender: str | None,
        limit: int,
    ):
        # 필터 옵션
        years = self.get_available_years()
        months = self.get_available_months(year)

        # 통계 데이터
        data = self.get_statistics(year, month, gender, limit)

        return years, months, data

    def get_ranking(
        self, date: str | None, city: str | None, gender: str | None, limit: int
    ):
        stmt = (
            select(
                Name.name,
                func.sum(Record.count).label("total_count"),
            )
            .join(Record, Record.name_id == Name.id)
            .join(CrawlLog, CrawlLog.id == Record.crawl_log_id)
        )

        if date:
            stmt = stmt.where(CrawlLog.record_date == date)

        stmt = self._apply_city_filter(stmt, city)

        stmt = self._apply_gender_filter(stmt, gender)

        stmt = (
            stmt.group_by(Name.name)
            .order_by(func.sum(Record.count).desc())
            .limit(limit)
        )

        return self.db.execute(stmt).all()

    def get_trend(self, name: str, city: str | None, gender: str | None):
        name_obj = self.db.execute(
            select(Name).where(Name.name == name)
        ).scalar_one_or_none()

        if not name_obj:
            return None

        stmt = (
            select(
                CrawlLog.record_date,
                func.sum(Record.count).label("daily_count"),
            )
            .join(CrawlLog, CrawlLog.id == Record.crawl_log_id)
            .where(Record.name_id == name_obj.id)
        )

        stmt = self._apply_city_filter(stmt, city)
        stmt = self._apply_gender_filter(stmt, gender)

        stmt = stmt.group_by(CrawlLog.record_date).order_by(CrawlLog.record_date)

        return self.db.execute(stmt).all()

    def get_available_years(self):
        stmt = (
            select(func.extract("year", CrawlLog.record_date).label("year"))
            .distinct()
            .order_by(func.extract("year", CrawlLog.record_date).desc())
        )
        return [int(row.year) for row in self.db.execute(stmt).all()]

    def get_available_months(self, year: int | None):
        stmt = select(
            func.extract("month", CrawlLog.record_date).label("month")
        ).distinct()
        if year:
            stmt = stmt.where(func.extract("year", CrawlLog.record_date) == year)

        stmt = stmt.order_by(func.extract("month", CrawlLog.record_date))
        return [int(row.month) for row in self.db.execute(stmt).all()]
