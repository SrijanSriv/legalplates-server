from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from app.routers import upload, template, draft
from app.db.base import init_db
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
    yield


app = FastAPI(
    lifespan=lifespan,
    title="LegalPlates API",
    description="API for legal document template generation and management",
    version="1.0.0"
)

# Exception handler for standardized error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom exception handler to ensure all HTTP exceptions follow
    the standardized response format: {error, message, body}
    """
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "body": None
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler for unexpected errors.
    """
    logger.error(f"Unexpected error: {exc} - Path: {request.url.path}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "An unexpected error occurred. Please try again later.",
            "body": None
        }
    )


allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
api_version = os.getenv("API_VERSION", "1")
api_prefix = f"/api/v{api_version}"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix=api_prefix)
app.include_router(template.router, prefix=api_prefix)
app.include_router(draft.router, prefix=api_prefix)


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {
        "error": False,
        "message": "LegalPlates API is running",
        "body": {
            "version": api_version,
            "status": "healthy"
        }
    }
