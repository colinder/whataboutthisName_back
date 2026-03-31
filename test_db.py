from sqlalchemy import text

from database import engine

with engine.connect() as conn:
    result = conn.execute(text("SELECT count(*) FROM names"))
    print("연결 성공! names 테이블 행 수:", result.scalar())

    result = conn.execute(text("SELECT count(*) FROM records"))
    print("records 테이블 행 수:", result.scalar())
