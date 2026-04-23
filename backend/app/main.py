import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.routes.bugs import router as bugs_router
from app.routes.workflow import router as workflow_router
from app.routes.suggestions import router as suggestions_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import create_tables
    create_tables()
    logger.info("Bug Tracking API started.")
    yield

app = FastAPI(title="Bug Tracking API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time-ms"] = f"{(time.perf_counter()-start)*1000:.2f}"
    return response

@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"success": False, "message": "Validation error", "errors": [{"field": "->".join(map(str,e["loc"])), "message": e["msg"]} for e in exc.errors()]})

@app.exception_handler(Exception)
async def global_handler(request: Request, exc: Exception):
    logger.error("Unhandled error: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"success": False, "message": "Internal server error"})

app.include_router(bugs_router, prefix="/api/v1")
app.include_router(workflow_router, prefix="/api/v1")
app.include_router(suggestions_router, prefix="/api/v1")

@app.get("/health", tags=["System"])
def health(): return {"status": "ok"}

@app.get("/", tags=["System"])
def root(): return {"message": "Bug Tracking API running", "docs": "/docs"}
