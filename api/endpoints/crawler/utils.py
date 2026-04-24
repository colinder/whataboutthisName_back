# api/endpoints/crawler/utils.py

import calendar
from datetime import date
from typing import List, Set


def parse_date_ranges(date_strings: List[str]) -> Set[date]:
    """
    날짜 문자열 리스트를 파싱하여 실제 날짜 set 반환

    Args:
        date_strings: ["2008-01", "2008-01-02", "2008-02-04"]

    Returns:
        {date(2008,1,1), date(2008,1,2), ..., date(2008,2,4)}

    로직:
        1. "2008-01" → 2008-01-01 ~ 2008-01-31
        2. "2008-01-02" → 무시 (이미 2008-01에 포함)
        3. "2008-02-04" → 2008-02-04
    """
    monthly_ranges = []  # 월 단위
    daily_dates = []  # 일 단위

    # 1단계: 월/일 분리
    for date_str in date_strings:
        if len(date_str) == 7:  # YYYY-MM
            monthly_ranges.append(date_str)
        elif len(date_str) == 10:  # YYYY-MM-DD
            daily_dates.append(date_str)

    # 2단계: 월 범위 → 날짜 set
    monthly_dates = set()
    for month_str in monthly_ranges:
        year, month = map(int, month_str.split("-"))
        # 해당 월의 마지막 날 계산
        last_day = calendar.monthrange(year, month)[1]

        for day in range(1, last_day + 1):
            monthly_dates.add(date(year, month, day))

    # 3단계: 개별 날짜 → set
    individual_dates = set()
    for date_str in daily_dates:
        year, month, day = map(int, date_str.split("-"))
        individual_dates.add(date(year, month, day))

    # 4단계: 중복 제거 (월 범위가 우선)
    # 개별 날짜 중 월 범위에 포함되지 않은 것만
    unique_dates = monthly_dates.union(individual_dates - monthly_dates)

    return unique_dates


def is_last_day_of_month(target_date: date) -> bool:
    """해당 날짜가 월의 마지막 날인지 확인"""
    last_day = calendar.monthrange(target_date.year, target_date.month)[1]
    return target_date.day == last_day


# 테스트 코드
if __name__ == "__main__":
    # 테스트 1: 중복 제거
    dates = parse_date_ranges(["2008-01", "2008-01-02", "2008-02-04"])
    print(f"총 {len(dates)}일")
    print(f"처음 5개: {sorted(dates)[:5]}")

    # 테스트 2: 마지막 날 확인
    test_date = date(2008, 2, 29)
    print(f"2008-02-29 마지막 날? {is_last_day_of_month(test_date)}")

    test_date2 = date(2008, 2, 28)
    print(f"2008-02-28 마지막 날? {is_last_day_of_month(test_date2)}")
