from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api import api_router
from config import settings

load_dotenv()

app = FastAPI()


# === CORS 미들웨어 (동적 origin 체크) ===
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    """
    동적으로 origin을 확인하고 CORS 헤더 추가
    - Vercel 패턴 매칭 지원
    - 환경변수 ALLOWED_ORIGINS 지원
    """
    origin = request.headers.get("origin")

    # Preflight 요청 처리
    if request.method == "OPTIONS":
        if settings.is_allowed_origin(origin):
            return JSONResponse(
                content={},
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Max-Age": "3600",
                },
            )
        return JSONResponse(content={"detail": "Origin not allowed"}, status_code=403)

    # 일반 요청 처리
    response = await call_next(request)

    # 허용된 origin이면 CORS 헤더 추가
    if settings.is_allowed_origin(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, DELETE, OPTIONS"
        )
        response.headers["Access-Control-Allow-Headers"] = "*"

    return response


# === 라우터 등록 ===
app.include_router(api_router)
