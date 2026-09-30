from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import chat, conversations, data
from app.services.errors import (
    ConfigError,
    ConflictError,
    LLMError,
    NoDataError,
    NotFoundError,
    RateLimitError,
)

app = FastAPI(
    title="주말 박스오피스 AI 비서 API",
    version="1.0.0",
    description="KOBIS 주말 박스오피스 데이터를 요약해 GPT 컨텍스트로 주입하는 API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(conversations.router)
app.include_router(chat.router)


def _error(status: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail})


@app.exception_handler(NotFoundError)
async def _not_found(_: Request, exc: NotFoundError):
    return _error(404, str(exc))


@app.exception_handler(ConflictError)
async def _conflict(_: Request, exc: ConflictError):
    return _error(409, str(exc))


@app.exception_handler(NoDataError)
async def _no_data(_: Request, exc: NoDataError):
    return _error(404, str(exc))


@app.exception_handler(LLMError)
async def _llm(_: Request, exc: LLMError):
    return _error(502, "AI 응답을 만드는 데 실패했어요. 잠시 후 다시 시도해 주세요.")


@app.exception_handler(ConfigError)
async def _config(_: Request, exc: ConfigError):
    return _error(503, str(exc))


@app.exception_handler(RateLimitError)
async def _rate(_: Request, exc: RateLimitError):
    return _error(429, str(exc))


@app.get("/health", tags=["system"], summary="헬스체크 (Render 콜드스타트 깨우기용)")
def health():
    return {"status": "ok"}
