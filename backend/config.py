"""
FacPark - Configuration Module
Centralizes all configuration settings for the application.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ==========================================================================
    # APPLICATION
    # ==========================================================================
    APP_NAME: str = "FacPark"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_32_CHARS_MIN"
    
    # ==========================================================================
    # PATHS
    # ==========================================================================
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    MODELS_DIR: Path = BASE_DIR / "models"
    DATA_DIR: Path = BASE_DIR / "data"
    DOCS_DIR: Path = DATA_DIR / "docs"
    FAISS_INDEX_PATH: Path = DATA_DIR / "faiss_index"
    
    # ==========================================================================
    # DATABASE (MySQL via XAMPP)
    # ==========================================================================
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""  # XAMPP default
    DB_NAME: str = "facpark"
    
    @property
    def DATABASE_URL(self) -> str:
        # Ajout de charset=utf8mb4 pour le support Arabe correct
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
    
    # ==========================================================================
    # JWT AUTH
    # ==========================================================================
    JWT_SECRET_KEY: str = "JWT_SECRET_CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ==========================================================================
    # LLM CONFIGURATION
    # ==========================================================================
    # Gemini (Primary LLM)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    # Groq (Fallback LLM)
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama3-70b-8192"
    
    # LLM Settings
    LLM_MAX_TOKENS: int = 1024
    LLM_TEMPERATURE: float = 0.3
    LLM_TIMEOUT: int = 30
    
    # ==========================================================================
    # RAG CONFIGURATION
    # ==========================================================================
    # Embeddings
    EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIMENSION: int = 384
    
    # Chunking
    CHUNK_MAX_SIZE: int = 1500
    CHUNK_OVERLAP_RATIO: float = 0.15
    
    # Retrieval
    RAG_TOP_K: int = 5
    RAG_TOP_N_VECTOR: int = 30
    RAG_TOP_N_BM25: int = 30
    RAG_RRF_K: int = 60  # RRF constant
    RAG_SCORE_THRESHOLD: float = 0.001  # Minimum relevance score (Low for RRF: 1/61=0.016)
    
    # Reranker (optional)
    RERANKER_ENABLED: bool = False
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKER_TOP_N: int = 20
    
    # ==========================================================================
    # VISION MODELS (consolidated in models/ directory)
    # ==========================================================================
    YOLO_MODEL_PATH: Path = MODELS_DIR / "smartalpr_hybrid_640_yolo11l_v2_best.pt"
    OCR_MODEL_PATH: Path = MODELS_DIR / "SmartALPR_LPRNet_v10_seed456_best.pth"
    VOCABULARY_PATH: Path = MODELS_DIR / "vocabulary.json"
    
    YOLO_CONFIDENCE: float = 0.5
    YOLO_IMG_SIZE: int = 640
    
    # ==========================================================================
    # SECURITY
    # ==========================================================================
    # Anti-injection patterns (compiled at runtime)
    INJECTION_PATTERNS: list = [
        r"ignore\s+(all\s+)?previous\s+instructions?",
        r"you\s+are\s+now\s+",
        r"forget\s+(everything|all)",
        r"disregard\s+(all|your)\s+",
        r"system\s*:\s*",
        r"assistant\s*:\s*",
        r"user\s*:\s*",
        r"\[INST\]",
        r"<\|system\|>",
        r"<\|user\|>",
        r"jailbreak",
        r"pretend\s+to\s+be",
        r"act\s+as\s+if\s+you\s+were",
        r"roleplay\s+as",
        r"bypass\s+(security|restrictions?)",
        r"override\s+",
        r"admin\s+mode",
        r"developer\s+mode",
        r"execute\s+(code|command)",
        r"run\s+(shell|bash|cmd)",
    ]
    
    INJECTION_SCORE_THRESHOLD: float = 0.5
    
    # ==========================================================================
    # BUSINESS RULES
    # ==========================================================================
    MAX_VEHICLES_PER_STUDENT: int = 3
    MAX_SLOTS_PER_STUDENT: int = 1
    
    # Subscription durations (days)
    SUBSCRIPTION_DURATIONS: dict = {
        "MENSUEL": 30,
        "SEMESTRIEL": 180,
        "ANNUEL": 365
    }
    
    # ==========================================================================
    # DECISION ENGINE REF CODES
    # ==========================================================================
    REF_CODES: dict = {
        "ALLOW": "REF-00",
        "PLATE_NOT_FOUND": "REF-01",
        "PLATE_NOT_REGISTERED": "REF-02",
        "NO_ACTIVE_SUBSCRIPTION": "REF-03",
        "STUDENT_SUSPENDED": "REF-04",
        "SUBSCRIPTION_EXPIRED": "REF-05",
        "NO_SLOT_ASSIGNED": "REF-06",
        "OUTSIDE_HOURS": "REF-07",
        "SYSTEM_ERROR": "REF-99"
    }
    
    # Parking hours
    PARKING_OPEN_HOUR: int = 7
    PARKING_CLOSE_HOUR: int = 22
    PARKING_OPEN_DAYS: list = [0, 1, 2, 3, 4, 5]  # Monday to Saturday
    
    # Demo mode: set to True to skip hours check (for demos outside 7h-22h)
    DEMO_MODE: bool = True  # ⚠️ Set to False in production!
    
    # ==========================================================================
    # LOGGING
    # ==========================================================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience access
settings = get_settings()
