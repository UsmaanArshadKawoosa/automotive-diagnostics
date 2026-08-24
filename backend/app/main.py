from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import router as api_v1_router
from app.config import settings
from app.services.diagnostic import DiagnosticServiceError
from app.services.llm import LLMProviderError


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
)


# Allow the frontend to run on any localhost port during local development.
# This means Vite can use 5173, 5174, 5175, etc. without requiring
# changes to the backend CORS configuration.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DiagnosticServiceError)
async def diagnostic_service_error_handler(
    request: Request,
    exc: DiagnosticServiceError,
) -> JSONResponse:
    detail = str(exc) if settings.debug else "Diagnostic service error"
    return JSONResponse(
        status_code=503,
        content={"detail": detail},
    )


@app.exception_handler(LLMProviderError)
async def llm_provider_error_handler(
    request: Request,
    exc: LLMProviderError,
) -> JSONResponse:
    detail = str(exc) if settings.debug else "LLM provider error"
    return JSONResponse(
        status_code=503,
        content={"detail": detail},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    if exc.status_code == 503 and not settings.debug:
        return JSONResponse(
            status_code=503,
            content={"detail": "Service temporarily unavailable"},
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


app.include_router(api_v1_router, prefix="/api")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": settings.app_name,
    }


@app.get("/ready")
def readiness_check() -> dict[str, str]:
    from app.db.database import get_db

    db = next(get_db())

    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return {"status": "not ready"}
    finally:
        db.close()