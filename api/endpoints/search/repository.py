from models.crawl_log import CrawlLog
from models.name import Name
from models.record import Record
from sqlalchemy import func, select
from sqlalchemy.orm import Session


class SearchRepository:
    def __init__(self, db: Session):
        self.db = db

    def _apply_gender_filter(self, stmt, gender: str | None):
        """공통 성별 필터"""
        if not gender or gender == "전체":
            stmt = stmt.where(CrawlLog.gender == "전체")
        else:
            stmt = stmt.where(CrawlLog.gender == gender)
        return stmt

    def get_daily_statistics(
        self,
        date: str,
        city: str | None,
        gender: str | None,
    ):
        stmt = (
            select(
                Name.name,
                func.sum(Record.count).label("total_count"),
            )
            .join(Record, Record.name_id == Name.id)
            .join(CrawlLog, CrawlLog.id == Record.crawl_log_id)
            .where(CrawlLog.record_date == date)
        )

        if city:
            stmt = stmt.where(CrawlLog.city == city)

        stmt = self._apply_gender_filter(stmt, gender)

        stmt = stmt.group_by(Name.name).order_by(func.sum(Record.count).desc())

        return self.db.execute(stmt).all()

    def get_statistics(
        self,
        year: int | None,
        month: int | None,
        gender: str | None,
        limit: int,
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

        if city:
            stmt = stmt.where(CrawlLog.city == city)

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

        if city:
            stmt = stmt.where(CrawlLog.city == city)

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
        if city:
            stmt = stmt.where(CrawlLog.city == city)
        if gender:
            stmt = stmt.where(CrawlLog.gender == gender)

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

        if city:
            stmt = stmt.where(CrawlLog.city == city)
        if gender:
            stmt = stmt.where(CrawlLog.gender == gender)

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
