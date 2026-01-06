import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Paths
    DATA_RAW_PATH = Path("data/raw")
    DATA_BRONZE_PATH = Path("data/bronze")
    DATA_SILVER_PATH = Path("data/silver")
    DATA_GOLD_PATH = Path("data/gold")
    
    # Database (DuckDB)
    DB_PATH = os.getenv("DB_PATH", "data/etl.db")
    
    # ETL
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", 1000))
    
    # API
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", 8000))
    JWT_SECRET = os.getenv("JWT_SECRET", "secret-key")

config = Config()