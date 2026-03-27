import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import mapped_column
from sqlalchemy.sql import functions
from typing_extensions import Annotated

created_at = Annotated[
    datetime.datetime,
    mapped_column(nullable=False, server_default=functions.now()),
]

updated_at = Annotated[
    datetime.datetime,
    mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now()),
]
