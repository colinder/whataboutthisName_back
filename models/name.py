from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from database import Base
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.record import Record


class Name(Base):
    __tablename__ = "names"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, comment="이름"
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now, onupdate=datetime.now
    )

    # 관계
    records: Mapped[list[Record]] = relationship("Record", back_populates="name")

    def __repr__(self) -> str:
        return f"<Name(id={self.id}, name={self.name})>"
