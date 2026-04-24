import calendar
import re

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from models.crawl_log import CrawlLog
from models.name import Name
from models.record import Record


class SearchRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_data_overview(self) -> dict:
        """메인 화면 데이터 현황 조회"""

        # 최근 크롤링 날짜
        last_date_stmt = select(func.max(CrawlLog.record_date))
        last_crawl = self.db.execute(last_date_stmt).scalar()

        # 남아 (전체 합산)
        male_stmt = (
            select(func.sum(Record.count))
            .join(CrawlLog, Record.crawl_log_id == CrawlLog.id)
            .where(CrawlLog.gender == "남자")
        )
        male_count = self.db.execute(male_stmt).scalar() or 0

        # 여아 (전체 합산)
        female_stmt = (
            select(func.sum(Record.count))
            .join(CrawlLog, Record.crawl_log_id == CrawlLog.id)
            .where(CrawlLog.gender == "여자")
        )
        female_count = self.db.execute(female_stmt).scalar() or 0

        # 전체 (남 + 여)
        total_records = male_count + female_count  # ✅ 계산

        return {
            "total_records": total_records,
            "last_update_date": last_crawl.strftime("%Y.%m.%d") if last_crawl else None,
            "total_male_count": male_count,
            "total_female_count": female_count,
        }

    def get_statistics_combined(
        self,
        year: int | None,
        month: int | None,
        gender: str | None,
        limit: int,
        exclude_etc: bool = True,
    ):
        """
        우선순위 조회:
        1. city='전체' 데이터 우선 (gender에 따라 '전체', '남자', '여자')
        2. 전체에 없는 이름만 시도별 합산
        """

        # ============================================================
        # Step 1: city='전체' 데이터 조회
        # ============================================================

        if not gender or gender == "전체":
            # ✅ gender='전체' 사용 (대법원 공식값)
            stmt_all = (
                select(
                    Name.name,
                    func.sum(Record.count).label("total_count"),
                )
                .join(Record, Record.name_id == Name.id)
                .join(CrawlLog, CrawlLog.id == Record.crawl_log_id)
                .where(CrawlLog.city == "전체")
                .where(CrawlLog.gender == "전체")  # ✅ 핵심 변경!
            )
        else:
            # 특정 성별 (남자 또는 여자)
            stmt_all = (
                select(
                    Name.name,
                    func.sum(Record.count).label("total_count"),
                )
                .join(Record, Record.name_id == Name.id)
                .join(CrawlLog, CrawlLog.id == Record.crawl_log_id)
                .where(CrawlLog.city == "전체")
                .where(CrawlLog.gender == gender)  # '남자' 또는 '여자'
            )

        # 공통 필터
        if year:
            stmt_all = stmt_all.where(
                func.extract("year", CrawlLog.record_date) == year
            )
        if month:
            stmt_all = stmt_all.where(
                func.extract("month", CrawlLog.record_date) == month
            )
        if exclude_etc:
            stmt_all = stmt_all.where(Name.name != "기타")

        stmt_all = stmt_all.group_by(Name.name)

        # city='전체' 결과
        results_all = self.db.execute(stmt_all).all()

        # 전체 데이터에 있는 이름들
        names_in_all = {row.name for row in results_all}

        # ============================================================
        # Step 2: 시도별 합산 (전체에 없는 이름만)
        # ============================================================

        if not gender or gender == "전체":
            # 남자 + 여자 합산
            stmt_regional = (
                select(
                    Name.name,
                    func.sum(Record.count).label("total_count"),
                )
                .join(Record, Record.name_id == Name.id)
                .join(CrawlLog, CrawlLog.id == Record.crawl_log_id)
                .where(CrawlLog.city != "전체")
                .where(CrawlLog.gender.in_(["남자", "여자"]))
            )
        else:
            # 특정 성별
            stmt_regional = (
                select(
                    Name.name,
                    func.sum(Record.count).label("total_count"),
                )
                .join(Record, Record.name_id == Name.id)
                .join(CrawlLog, CrawlLog.id == Record.crawl_log_id)
                .where(CrawlLog.city != "전체")
                .where(CrawlLog.gender == gender)
            )

        # 공통 필터
        if year:
            stmt_regional = stmt_regional.where(
                func.extract("year", CrawlLog.record_date) == year
            )
        if month:
            stmt_regional = stmt_regional.where(
                func.extract("month", CrawlLog.record_date) == month
            )
        if exclude_etc:
            stmt_regional = stmt_regional.where(Name.name != "기타")

        # ✅ 전체에 없는 이름만 필터링
        if names_in_all:
            stmt_regional = stmt_regional.where(Name.name.notin_(names_in_all))

        stmt_regional = stmt_regional.group_by(Name.name)

        # 시도별 결과
        results_regional = self.db.execute(stmt_regional).all()

        # ============================================================
        # Step 3: 병합 및 정렬
        # ============================================================

        # 결과 병합
        combined_results = list(results_all) + list(results_regional)

        # 건수 기준 내림차순 정렬
        combined_results.sort(key=lambda x: x.total_count, reverse=True)

        # limit 적용
        final_results = combined_results[:limit]

        return final_results

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
        """
        연도별 성별 전체 출생아 수

        - city='전체', gender='남자/여자'만 집계
        - 각 연도별로 한 번만 집계되도록 함
        """
        stmt = (
            select(
                func.extract("year", CrawlLog.record_date).label("year"),
                CrawlLog.gender,
                func.sum(Record.count).label("total_count"),
            )
            .join(Record, Record.crawl_log_id == CrawlLog.id)
            .where(CrawlLog.city == "전체")  # 도시 중복 방지
            .where(CrawlLog.gender.in_(["남자", "여자"]))  # 전체 제외
            .where(CrawlLog.is_success.is_(True))  # 성공한 크롤링만
            .group_by(func.extract("year", CrawlLog.record_date), CrawlLog.gender)
            .order_by(func.extract("year", CrawlLog.record_date).desc())
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

    def search_names(self, query: str):
        """
        이름 검색 (패턴 지원)

        - 글자 수: *, **, ***
        - 초성: ㄱ, ㄴㄷ, ㅁㅂㅅ (자음만)
        - 와일드카드: ㄷ*, *ㄴ*, *ㅅ**
        - 일반 검색: 민준, 서연, 도 (완성된 한글)

        반환값:
        {
            "type": "pattern" | "normal",
            "results": [{"name": "민준"}, {"name": "민서"}, ...]
        }
        """

        # 1. 글자 수 검색 (*, **, ***)
        if re.fullmatch(r"\*+", query):
            length = len(query)
            stmt = (
                select(Name.name)
                .where(func.char_length(Name.name) == length)
                .distinct()
            )
            results = self.db.execute(stmt).scalars().all()
            return {"type": "pattern", "results": [{"name": name} for name in results]}

        # 2. 초성 검색 또는 와일드카드 검색 (자음만 포함된 경우)
        if self._is_chosung_or_wildcard(query):
            pattern = self._convert_to_sql_pattern(query)

            stmt = (
                select(Name.name)
                .where(Name.name.op("~")(pattern))  # PostgreSQL POSIX 정규식
                .distinct()
            )
            results = self.db.execute(stmt).scalars().all()
            return {"type": "pattern", "results": [{"name": name} for name in results]}

        # 3. 일반 검색 (완성된 한글 포함)
        stmt = select(Name.name).where(Name.name.like(f"%{query}%")).distinct()
        results = self.db.execute(stmt).scalars().all()
        return {"type": "normal", "results": [{"name": name} for name in results]}

    def _is_chosung_or_wildcard(self, query: str) -> bool:
        """
        초성 또는 와일드카드 검색인지 확인

        - ㄱ-ㅎ (자음만 있음) → True
        - * 포함 → True
        - 가-힣 (완성된 한글) → False
        """
        # 완성된 한글이 포함되어 있으면 일반 검색
        if re.search(r"[가-힣]", query):
            # 단, *가 포함되어 있으면 와일드카드 검색
            if "*" in query:
                return True
            return False

        # 자음(ㄱ-ㅎ) 또는 * 만 있으면 패턴 검색
        return bool(re.search(r"[ㄱ-ㅎ*]", query))

    def _convert_to_sql_pattern(self, query: str) -> str:
        """
        검색 쿼리를 PostgreSQL 정규식 패턴으로 변환

        예시:
        - ㄷ → ^[다-딯]
        - ㅈㄱ → ^[자-짛][가-깋]
        - ㄷ* → ^[다-딯].
        - *ㄴ* → ^.[나-닣].
        - *ㅅ** → ^..[사-싷]..
        - 도* → ^도.  (완성된 한글 + 와일드카드)
        """

        # 초성 → 한글 범위 매핑
        chosung_map = {
            "ㄱ": "[가-깋]",
            "ㄲ": "[까-낗]",
            "ㄴ": "[나-닣]",
            "ㄷ": "[다-딯]",
            "ㄸ": "[따-띻]",
            "ㄹ": "[라-맇]",
            "ㅁ": "[마-밓]",
            "ㅂ": "[바-빟]",
            "ㅃ": "[빠-삫]",
            "ㅅ": "[사-싷]",
            "ㅆ": "[싸-앃]",
            "ㅇ": "[아-잏]",
            "ㅈ": "[자-짛]",
            "ㅉ": "[짜-찧]",
            "ㅊ": "[차-칳]",
            "ㅋ": "[카-킿]",
            "ㅌ": "[타-팋]",
            "ㅍ": "[파-핗]",
            "ㅎ": "[하-힣]",
        }

        pattern = "^"  # 시작

        for char in query:
            if char == "*":
                pattern += "."  # 아무 글자 1개
            elif char in chosung_map:
                pattern += chosung_map[char]  # 초성 범위
            else:
                # 완성된 한글 또는 일반 문자
                pattern += re.escape(char)

        pattern += "$"  # 끝

        return pattern

    def get_crawl_calendar(self, year: int | None = None) -> list[dict]:
        """
        캘린더용 날짜별 수집 개수 조회

        Args:
            year: 연도 필터 (선택사항)

        Returns:
            [
                {"date": "2008-01-01", "count": 48, "level": 4},
                {"date": "2008-01-02", "count": 48, "level": 4},
                ...
            ]
        """
        # 날짜별 수집 개수 조회
        stmt = select(
            CrawlLog.record_date, func.count(CrawlLog.id).label("count")
        ).group_by(CrawlLog.record_date)

        if year:
            stmt = stmt.where(extract("year", CrawlLog.record_date) == year)

        stmt = stmt.order_by(CrawlLog.record_date)

        results = self.db.execute(stmt).all()

        # 캘린더 데이터 변환
        calendar_data = []
        for row in results:
            count = row.count
            record_date = row.record_date

            # 월말 여부 확인
            last_day = calendar.monthrange(record_date.year, record_date.month)[1]
            is_last_day = record_date.day == last_day

            # 레벨 계산
            if is_last_day:
                # 월말: 48(시도별) + 3(전체 남/여/전체) = 51개
                if count >= 51:
                    level = 4  # 완전 수집
                elif count >= 1:
                    level = 3  # 부분 수집
                else:
                    level = 0  # 미수집
            else:
                # 평일: 48개(시도별 남/여)
                if count >= 48:
                    level = 4  # 완전 수집
                elif count >= 1:
                    level = 3  # 부분 수집
                else:
                    level = 0  # 미수집

            calendar_data.append(
                {
                    "date": record_date.strftime("%Y-%m-%d"),
                    "count": count,
                    "display_count": 1,
                    "level": level,
                }
            )

        return calendar_data
