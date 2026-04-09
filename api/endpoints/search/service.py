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

    def daily_statistics(
        self,
        date: str,
        city: str | None,
        gender: str | None,
    ) -> dict:
        results = self.repo.get_daily_statistics(date, city, gender)

        data = [
            {
                "rank": i + 1,
                "name": row.name,
                "count": int(row.total_count),
            }
            for i, row in enumerate(results)
        ]

        return {
            "date": date,
            "city": city or "전체",
            "gender": gender or "전체",
            "count": len(data),
            "total": sum(item["count"] for item in data),
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
        years, months, results = self.repo.get_statistics_with_filters(
            year, month, gender, limit
        )

        return {
            "filters": {
                "year": year,
                "month": month,
                "gender": gender,
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
                    "gender": row.gender,
                    "count": int(row.total_count),
                }
                for i, row in enumerate(results)
            ],
        }
