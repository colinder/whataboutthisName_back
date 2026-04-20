from typing import List

from dotenv.main import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = ""
    ALLOWED_ORIGINS: str = ""  # 쉼표로 구분된 문자열
    APP_ENV: str = "development"

    @property
    def allowed_origins_list(self) -> List[str]:
        """ALLOWED_ORIGINS를 리스트로 변환"""
        if not self.ALLOWED_ORIGINS:
            # 개발 환경 기본값
            if self.APP_ENV == "development":
                return [
                    "http://localhost:5173",
                    "http://localhost:8080",
                    "http://127.0.0.1:5173",
                ]
            return []

        # 쉼표로 분리하고 공백 제거
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()
