import calendar
from datetime import date, timedelta

from models.name import Name
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from api.endpoints.search.repository import SearchRepository


def parse_date_input(date_str: str) -> list[date]:
    """
    날짜 입력 파싱
    - 2008 → 2008-01-01 ~ 2008-12-31
    - 2008-01 → 2008-01-01 ~ 2008-01-31
    - 2008-01-05 → 2008-01-05
    """
    parts = date_str.strip().split("-")

    if len(parts) == 1:
        # 연도만 (2008)
        year = int(parts[0])
        start = date(year, 1, 1)
        end = date(year, 12, 31)
    elif len(parts) == 2:
        # 연월 (2008-01)
        year, month = int(parts[0]), int(parts[1])
        start = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end = date(year, month, last_day)
    else:
        # 정확한 날짜 (2008-01-05)
        return [date.fromisoformat(date_str)]

    dates = []
    current = start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    return dates


CHOSUNG = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"

CHOSUNG_MAP = {}
for i, ch in enumerate(CHOSUNG):
    start = 0xAC00 + i * 21 * 28
    end = start + 21 * 28 - 1
    CHOSUNG_MAP[ch] = (chr(start), chr(end))


class SearchService:
    def __init__(self, db: Session):
        self.repo = SearchRepository(db)

    def name_gender_stats(self, name: str) -> dict:
        results = self.repo.get_name_gender_stats(name)

        if not results:
            return {"name": name, "found": False, "data": []}

        data = []
        for row in results:
            label = "남아" if row.gender == "남자" else "여아"
            data.append(
                {
                    "name": label,
                    "value": int(row.total_count),
                }
            )

        # 남아 또는 여아 데이터가 없으면 0으로 추가
        labels = [d["name"] for d in data]
        if "남아" not in labels:
            data.insert(0, {"name": "남아", "value": 0})
        if "여아" not in labels:
            data.append({"name": "여아", "value": 0})

        # 남아가 먼저 오도록 정렬
        data.sort(key=lambda x: 0 if x["name"] == "남아" else 1)

        return {
            "name": name,
            "found": True,
            "data": data,
        }

    def name_yearly_trend(self, name: str) -> dict:
        """이름의 연도별 추이 - 남자+여자 합산으로 전체 계산"""
        male_data = self.repo.get_trend(name, None, "남자") or []
        female_data = self.repo.get_trend(name, None, "여자") or []

        if not male_data and not female_data:
            return {"name": name, "found": False, "data": []}

        # 연도별 합산
        def aggregate_by_year(data):
            year_map = {}
            for row in data:
                year = str(row.record_date)[:4]
                year_map[year] = year_map.get(year, 0) + int(row.daily_count)
            return year_map

        male_map = aggregate_by_year(male_data)
        female_map = aggregate_by_year(female_data)

        all_years = sorted(set(list(male_map.keys()) + list(female_map.keys())))

        data = []
        for year in all_years:
            male_count = male_map.get(year, 0)
            female_count = female_map.get(year, 0)

            data.append(
                {
                    "year": int(year),
                    "전체": male_count + female_count,
                    "남아": male_count,
                    "여아": female_count,
                }
            )

        return {
            "name": name,
            "found": True,
            "data": data,
        }

    def name_yearly_rank(self, name: str) -> dict:
        rank_data = self.repo.get_name_yearly_rank(name)
        total_data = self.repo.get_yearly_total_by_gender()

        if not rank_data:
            return {"name": name, "found": False, "data": []}

        # 연도별 전체 출생아 수
        total_map = {}
        for row in total_data:
            year = int(row.year)
            if year not in total_map:
                total_map[year] = {}
            total_map[year][row.gender] = int(row.total_count)

        # 연도별 순위/건수
        rank_map = {}
        for row in rank_data:
            year = int(row.year)
            if year not in rank_map:
                rank_map[year] = {}
            rank_map[year][row.gender] = {
                "rank": int(row.rank),
                "count": int(row.total_count),
            }

        all_years = sorted(
            set(list(total_map.keys()) + list(rank_map.keys())),
            reverse=True,
        )

        data = []
        for year in all_years:
            male = rank_map.get(year, {}).get("남자", {"rank": None, "count": 0})
            female = rank_map.get(year, {}).get("여자", {"rank": None, "count": 0})

            data.append(
                {
                    "year": year,
                    "male": {
                        "total": total_map.get(year, {}).get("남자", 0),
                        "rank": male["rank"],
                        "count": male["count"],
                    },
                    "female": {
                        "total": total_map.get(year, {}).get("여자", 0),
                        "rank": female["rank"],
                        "count": female["count"],
                    },
                }
            )

        return {
            "name": name,
            "found": True,
            "data": data,
        }

    def crawl_status(self, year: int) -> dict:
        results = self.repo.get_crawl_status_by_year(year)

        # 전체 도시 × 성별 조합 수
        from models.Enums import CityEnum, GenderEnum

        expected = len(list(CityEnum)) * len(list(GenderEnum))

        data = []
        for row in results:
            date_str = str(row.record_date)
            count = row.log_count
            # 수집 완료 비율에 따라 level 결정
            if count >= expected and row.all_success:
                level = 4  # 완전 수집
            elif count >= expected * 0.7:
                level = 3
            elif count >= expected * 0.3:
                level = 2
            elif count > 0:
                level = 1
            else:
                level = 0

            data.append(
                {
                    "date": date_str,
                    "count": count,
                    "level": level,
                }
            )

        return {
            "year": year,
            "expected_per_day": expected,
            "total_days": len(data),
            "data": data,
        }

    def search(self, q: str, city: str | None, gender: str | None, limit: int) -> dict:
        is_pattern = "*" in q or any(c in CHOSUNG for c in q)

        if is_pattern:
            name_filter = self._build_name_filter(q)
            results = self.repo.search_by_pattern(name_filter, city, gender, limit)
            search_type = "pattern"
        else:
            results = self.repo.search_by_name(q, city, gender, limit)
            search_type = "name"

        return {
            "type": search_type,
            "query": q,
            "count": len(results),
            "data": [
                {"name": row.name, "total_count": int(row.total_count)}
                for row in results
            ],
        }

    def ranking(
        self, date: str | None, city: str | None, gender: str | None, limit: int
    ) -> dict:
        results = self.repo.get_ranking(date, city, gender, limit)

        return {
            "filters": {"date": date, "city": city, "gender": gender},
            "count": len(results),
            "data": [
                {"rank": i + 1, "name": row.name, "total_count": int(row.total_count)}
                for i, row in enumerate(results)
            ],
        }

    def trend(self, name: str, city: str | None, gender: str | None) -> dict:
        results = self.repo.get_trend(name, city, gender)

        if results is None:
            return {"name": name, "found": False, "data": []}

        return {
            "name": name,
            "found": True,
            "data": [
                {"date": str(row.record_date), "count": int(row.daily_count)}
                for row in results
            ],
        }

    def _build_name_filter(self, pattern: str):
        chars = list(pattern)
        filters = [func.char_length(Name.name) == len(chars)]

        for i, char in enumerate(chars):
            if char == "*":
                continue
            elif char in CHOSUNG_MAP:
                start, end = CHOSUNG_MAP[char]
                char_at = func.substr(Name.name, i + 1, 1)
                filters.append(char_at >= start)
                filters.append(char_at <= end)
            else:
                char_at = func.substr(Name.name, i + 1, 1)
                filters.append(char_at == char)

        return and_(*filters)

    def statistics(
        self,
        year: int | None,
        month: int | None,
        gender: str | None,
        limit: int,
    ) -> dict:
        years, months, _ = self.repo.get_statistics_with_filters(
            year, month, gender, limit
        )

        results = self.repo.get_statistics_combined(year, month, gender, limit)

        return {
            "filters": {
                "year": year,
                "month": month,
                "gender": gender or "전체",
                "options": {
                    "years": years,
                    "months": months,
                    "genders": ["남자", "여자"],
                },
            },
            "count": len(results),
            "data": [
                {
                    "rank": i + 1,
                    "name": row.name,
                    "total_count": int(row.total_count),
                }
                for i, row in enumerate(results)
            ],
        }

    def yearly_statistics(self) -> dict:
        results = self.repo.get_yearly_statistics()

        # 연도별로 그룹핑
        year_map = {}
        for row in results:
            year = int(row.year)
            if year not in year_map:
                year_map[year] = {"year": year, "전체": 0, "남아": 0, "여아": 0}

            if row.gender == "전체":
                year_map[year]["전체"] = int(row.total_count)
            elif row.gender == "남자":
                year_map[year]["남아"] = int(row.total_count)
            elif row.gender == "여자":
                year_map[year]["여아"] = int(row.total_count)

        data = sorted(year_map.values(), key=lambda x: x["year"])

        return {
            "count": len(data),
            "data": data,
        }
