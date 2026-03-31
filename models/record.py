# models/stat.py
import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utils import UUIDType

from database import Base
from models.name import Name

from .utils import created_at, updated_at


class Record(Base):
    __tablename__ = "records"

    id: Mapped[UUIDType] = mapped_column(UUIDType, default=uuid.uuid4, primary_key=True)
    name_id: Mapped[UUIDType] = mapped_column(
        UUIDType, ForeignKey("names.id"), nullable=False, comment="이름 FK"
    )
    city: Mapped[str] = mapped_column(String(255), nullable=False, comment="도시")
    record_date: Mapped[date] = mapped_column(Date, nullable=False, comment="기록일자")

    gender: Mapped[str] = mapped_column(String(255), nullable=False, comment="성별")
    count: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="성별 전체 건수"
    )

    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    # 연결관계
    name: Mapped["Name"] = relationship("Name", back_populates="records")
