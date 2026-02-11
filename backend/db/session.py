"""
FacPark - Database Session Management
Provides SQLAlchemy engine, session factory, and dependency injection.
"""

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
import logging

from backend.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# BASE CLASS FOR MODELS
# =============================================================================
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# =============================================================================
# ENGINE CONFIGURATION
# =============================================================================
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,        # Réduit pour XAMPP
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=280,   # Recyclage rapide (4m) pour éviter les timeouts MySQL par défaut (souvent 8h mais instable sur XAMPP local)
    echo=False,         # Moins de logs
    connect_args={
        "charset": "utf8mb4"
    }
)


# =============================================================================
# SESSION FACTORY
# =============================================================================
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session.
    Ensures proper cleanup after request completes.
    
    Usage in FastAPI:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions outside of FastAPI.
    
    Usage:
        with get_db_context() as db:
            db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================
def init_db() -> None:
    """
    Initialize the database by creating all tables.
    Called once at application startup.
    """
    # Import models to register them with Base
    from backend.db import models  # noqa: F401
    
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")


def check_db_connection() -> bool:
    """
    Verify database connectivity.
    Returns True if connection is successful.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("Database connection verified.")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


# =============================================================================
# CONNECTION EVENT LISTENERS
# =============================================================================
@event.listens_for(engine, "connect")
def set_mysql_session_variables(dbapi_connection, connection_record):
    """
    Set MySQL session variables for each new connection.
    Ensures consistent behavior across all connections.
    """
    cursor = dbapi_connection.cursor()
    try:
        # Set timezone to UTC for consistent timestamps
        cursor.execute("SET time_zone = '+00:00'")
        # Set character set for proper French text support
        cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
        # Set SQL mode for strict data validation
        cursor.execute(
            "SET sql_mode = 'STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'"
        )
    finally:
        cursor.close()


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log when a connection is checked out from the pool."""
    if settings.DEBUG:
        logger.debug("Connection checked out from pool.")


@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log when a connection is returned to the pool."""
    if settings.DEBUG:
        logger.debug("Connection returned to pool.")
