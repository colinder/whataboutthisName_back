# api/endpoints/crawler/schemas.py

from typing import List

from pydantic import BaseModel, field_validator


class CrawlRequest(BaseModel):
    """크롤링 요청 모델"""

    target_date: List[str]  # ["2008-01", "2008-01-02", "2008-02-04"]

    @field_validator("target_date")
    @classmethod
    def validate_dates(cls, v):
        """날짜 형식 검증: YYYY-MM 또는 YYYY-MM-DD"""
        if not v:
            raise ValueError("target_date는 필수입니다")

        for date_str in v:
            if len(date_str) not in [4, 7, 10]:
                raise ValueError(
                    f"날짜 형식 오류: {date_str} (YYYY-MM 또는 YYYY-MM-DD)"
                )

            # YYYY-MM 형식 체크
            if len(date_str) == 7:
                try:
                    year, month = date_str.split("-")
                    int(year)
                    int(month)
                except:
                    raise ValueError(f"잘못된 월 형식: {date_str}")

            # YYYY-MM-DD 형식 체크
            if len(date_str) == 10:
                try:
                    year, month, day = date_str.split("-")
                    int(year)
                    int(month)
                    int(day)
                except:
                    raise ValueError(f"잘못된 날짜 형식: {date_str}")

        return v


class CrawlResponse(BaseModel):
    """크롤링 응답 모델"""

    message: str
    total_dates: int
    dates: List[str]  # 처음 10개만

    class Config:
        json_schema_extra = {
            "example": {
                "message": "크롤링 시작",
                "total_dates": 32,
                "dates": ["2008-01-01", "2008-01-02", "..."],
            }
        }
