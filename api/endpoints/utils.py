import calendar
from datetime import date, timedelta


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
