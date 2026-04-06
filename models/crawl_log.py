from datetime import date, datetime

from database import Base
from sqlalchemy import Boolean, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class CrawlLog(Base):
    __tablename__ = "crawl_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="수집 대상 날짜"
    )
    city: Mapped[str] = mapped_column(String(255), nullable=False, comment="도시")
    gender: Mapped[str] = mapped_column(String(255), nullable=False, comment="성별")
    is_success: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="수집 성공 여부"
    )
    has_result: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="데이터 존재 여부"
    )
    total_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="수집 건수"
    )
    crawled_at: Mapped[datetime] = mapped_column(
        default=datetime.now, comment="수집 실행 시각"
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    # 관계
    records: Mapped[list["Record"]] = relationship(
        "Record", back_populates="crawl_log", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CrawlLog(id={self.id}, date={self.record_date}, city={self.city}, gender={self.gender})>"


from models.record import Record  # noqa: E402, F401
