from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from database import Base
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.crawl_log import CrawlLog
    from models.name import Name


class Record(Base):
    __tablename__ = "records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crawl_log_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crawl_logs.id", ondelete="CASCADE"),
        nullable=False,
        comment="크롤링 로그 FK",
    )
    name_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("names.id", ondelete="CASCADE"),
        nullable=False,
        comment="이름 FK",
    )
    count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="출생 건수"
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    # 관계
    crawl_log: Mapped[CrawlLog] = relationship("CrawlLog", back_populates="records")
    name: Mapped[Name] = relationship("Name", back_populates="records")

    def __repr__(self) -> str:
        return f"<Record(id={self.id}, crawl_log_id={self.crawl_log_id}, name_id={self.name_id}, count={self.count})>"
