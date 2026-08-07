"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import captures, documents, questions, responses, sessions, templates, transcriptions
from .config import settings
from .models.base import AsyncSessionLocal, close_db, init_db
from .services.template_loader import load_bundled_templates

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting up application...")
    for storage_path in (
        settings.audio_storage_path,
        settings.session_storage_path,
        settings.template_storage_path,
    ):
        Path(storage_path).expanduser().mkdir(parents=True, exist_ok=True)
    await init_db()
    logger.info("Database initialized")
    async with AsyncSessionLocal() as db:
        loaded_templates = await load_bundled_templates(db)
    if loaded_templates:
        logger.info("Loaded %s bundled template(s)", loaded_templates)
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Interactive Document Creator - Generate documents through conversational Q&A",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version
    }


# Include routers
app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(templates.router, prefix="/api/templates", tags=["Templates"])
app.include_router(responses.router, prefix="/api/responses", tags=["Responses"])
app.include_router(questions.router, prefix="/api/questions", tags=["Questions"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(
    transcriptions.router,
    prefix="/api/transcriptions",
    tags=["Transcriptions"],
)
app.include_router(captures.router, prefix="/api/captures", tags=["Captures"])


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Interactive Document Creator API",
        "docs": "/api/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

# Made with Bob
