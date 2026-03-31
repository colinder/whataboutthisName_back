from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

from .utils import created_at, updated_at

if TYPE_CHECKING:
    from .record import Record


class Name(Base):
    __tablename__ = "names"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="이름 항목")
    count: Mapped[int] = mapped_column(Integer, nullable=False, comment="건수")

    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    # 연결관계
    records: Mapped[list["Record"]] = relationship(
        "Record",
        back_populates="name",
    )
