# app/main.py

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


# ─────────────────────────────────────────────
# DEBUG SAFE ROUTER IMPORTS
# ─────────────────────────────────────────────

print("🔥 STARTING APP")

try:
    from app.routes.bugs import router as bugs_router
    print("✅ bugs router imported")
except Exception as e:
    print("❌ ERROR importing bugs router:", e)
    raise

try:
    from app.routes.workflow import router as workflow_router
    print("✅ workflow router imported")
except Exception as e:
    print("❌ ERROR importing workflow router:", e)
    raise

try:
    from app.routes.suggestions import router as suggestions_router
    print("✅ suggestions router imported")
except Exception as e:
    print("❌ ERROR importing suggestions router:", e)
    raise


# ─────────────────────────────────────────────
# Logging Configuration
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Lifespan Events
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Bug Tracking API...")
    yield
    logger.info("🛑 Shutting down Bug Tracking API...")


# ─────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────

app = FastAPI(
    title="Rule-Based Bug Tracking & Resolution API",
    description="Backend system for bug tracking, classification, prioritization, and fix suggestions.",
    version="1.0.0",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────
# CORS Middleware
# ─────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Request Timing Middleware
# ─────────────────────────────────────────────

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000
    response.headers["X-Process-Time-ms"] = f"{process_time:.2f}"
    return response


# ─────────────────────────────────────────────
# Global Exception Handlers
# ─────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {
            "field": " -> ".join(map(str, err["loc"])),
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation error",
            "errors": errors,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
        },
    )


# ─────────────────────────────────────────────
# Include Routers
# ─────────────────────────────────────────────

app.include_router(bugs_router, prefix="/api/v1")
app.include_router(workflow_router, prefix="/api/v1")
app.include_router(suggestions_router, prefix="/api/v1")


# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}


# ─────────────────────────────────────────────
# Root Endpoint
# ─────────────────────────────────────────────

@app.get("/", tags=["System"])
def root():
    return {
        "message": "Rule-Based Bug Tracking API is running 🚀",
        "docs": "/docs",
        "health": "/health",
    }