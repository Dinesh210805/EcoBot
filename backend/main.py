import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend.config import get_settings
from backend.db.sqlite_db import init_schema
from backend.middleware.rate_limit import limiter
from backend.api import classify_router, chat_router, facilities_router, health_router

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("ecobot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("EcoBot starting up — classifier_mode=%s", settings.classifier_mode)
    init_schema()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    yield
    logger.info("EcoBot shutting down")


app = FastAPI(
    title="EcoBot API",
    description=(
        "Multimodal AI waste classification assistant for India. "
        "Supports text, image, and voice input with bin-color guidance, "
        "RAG-powered disposal instructions, and nearby facility lookup."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for uploaded images (image preview URLs)
upload_dir = Path(settings.upload_dir)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

# API routers
API_PREFIX = "/api/v1"
app.include_router(classify_router, prefix=API_PREFIX)
app.include_router(chat_router, prefix=API_PREFIX)
app.include_router(facilities_router, prefix=API_PREFIX)
app.include_router(health_router, prefix=API_PREFIX)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.error("Unhandled error: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again."},
    )


@app.get("/", tags=["root"])
async def root():
    return {
        "name": "EcoBot API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
