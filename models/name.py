from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from .record import Record


class Name(Base):
    __tablename__ = "names"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="이름 항목")
    count: Mapped[str] = mapped_column(String(255), nullable=False, comment="건수")

    # 연결관계
    records: Mapped[list["Record"]] = relationship(
        "Record",
        back_populates="name",
    )
