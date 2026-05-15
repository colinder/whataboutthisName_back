import re
from typing import List

from dotenv.main import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = ""
    ALLOWED_ORIGINS: str = ""
    APP_ENV: str = "development"
    SECRET: str = ""

    @property
    def allowed_origins_list(self) -> List[str]:
        """환경변수에서 명시적으로 지정된 origin 리스트"""
        if not self.ALLOWED_ORIGINS:
            if self.APP_ENV == "development":
                return [
                    "http://localhost:5173",
                    "http://localhost:3000",
                    "http://127.0.0.1:5173",
                ]
            return []

        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    def is_allowed_origin(self, origin: str) -> bool:
        """
        오리진이 허용되는지 확인
        - 환경변수에 명시된 origin
        - Vercel 배포 URL 패턴
        - 프로덕션 Vercel URL
        """
        if not origin:
            return False

        try:
            # 1. 환경변수에 명시적으로 허용된 origin
            if origin in self.allowed_origins_list:
                return True

            # 2. Vercel 프리뷰/배포 URL 패턴
            vercel_preview_pattern = re.compile(
                r"^https://whataboutthisname-[a-z0-9]+-selforofficial-[a-z0-9]+-projects\.vercel\.app$"
            )
            if vercel_preview_pattern.match(origin):
                return True

            # 3. Vercel 프로덕션 URL
            if origin in [
                "https://whataboutthisname.vercel.app",
                "https://www.whataboutthisname.vercel.app",
            ]:
                return True

            # 4. 개발 환경
            if self.APP_ENV == "development":
                if origin.startswith("http://localhost") or origin.startswith(
                    "http://127.0.0.1"
                ):
                    return True

            return False
        except Exception as e:
            print(f"⚠️ CORS check error: {e}")
            return False


settings = Settings()

# 시작 시 설정 출력 (안전하게)
try:
    print("=" * 50)
    print(f"🔧 Environment: {settings.APP_ENV}")
    print(f"🔒 Explicit CORS Origins: {settings.allowed_origins_list}")
    print(f"✅ Vercel Pattern Matching: Enabled")
    print("=" * 50)
except Exception as e:
    print(f"⚠️ Settings print error: {e}")
