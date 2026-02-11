"""
FacPark - FastAPI Main Application
Entry point for the backend API.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from backend.config import settings
from backend.db.session import init_db, check_db_connection
from backend.api import auth, chat, vision, admin

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)
logger = logging.getLogger(__name__)


# =============================================================================
# LIFESPAN (Startup/Shutdown)
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Check database connection
    if not check_db_connection():
        logger.error("Database connection failed! Check XAMPP MySQL.")
    else:
        logger.info("Database connection verified.")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")


# =============================================================================
# APP INSTANCE
# =============================================================================
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    FacPark - Système de Gestion de Parking Universitaire
    
    ## Fonctionnalités
    - 🚗 Reconnaissance de plaques (YOLO + OCR)
    - 🤖 Assistant IA avec RAG
    - 🔐 Authentification JWT
    - 👥 Gestion étudiants/véhicules/abonnements
    """,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)


# =============================================================================
# CORS MIDDLEWARE
# =============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# REQUEST TIMING MIDDLEWARE
# =============================================================================
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to all responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response


# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Une erreur interne s'est produite.",
            "detail": str(exc) if settings.DEBUG else None
        }
    )


# =============================================================================
# ROUTERS
# =============================================================================
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat & RAG"])
app.include_router(vision.router, prefix="/api/vision", tags=["Vision & Plates"])
app.include_router(admin.router, prefix="/api/admin", tags=["Administration"])


# =============================================================================
# ROOT ENDPOINTS
# =============================================================================
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API info."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs" if settings.DEBUG else "disabled"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    db_ok = check_db_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "version": settings.APP_VERSION
    }


# =============================================================================
# RUN WITH UVICORN
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
