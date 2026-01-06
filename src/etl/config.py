# src/etl/config.py
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Config:
    """Central configuration"""
    
    # Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", 5432)
    DB_NAME = os.getenv("DB_NAME", "etl_db")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
    
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Data paths
    DATA_RAW_PATH = Path("data/raw")
    DATA_BRONZE_PATH = Path("data/bronze")
    DATA_SILVER_PATH = Path("data/silver")
    DATA_GOLD_PATH = Path("data/gold")
    
    # ETL
    BATCH_SIZE = 1000
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    PREFECT_API_URL = os.getenv("PREFECT_API_URL", "http://127.0.0.1:4200/api")
    
    # MinIO (S3-compatible)
    MINIO_ENABLED = os.getenv("MINIO_ENABLED", "false").lower() == "true"
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET = os.getenv("MINIO_BUCKET", "etl-data")
    
    # API
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", 8000))
    JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-prod")
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30

config = Config()
