from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./nasa_deep_zoom.db"
    
    # Redis Cache
    redis_url: str = "redis://localhost:6379"
    
    # AWS S3 (optional)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket: Optional[str] = None
    
    # ML Models
    models_dir: str = "models"
    gpu_enabled: bool = False
    batch_size: int = 4
    
    # Tile Configuration
    tile_size: int = 512
    max_zoom: int = 20
    cache_ttl: int = 3600  # 1 hour
    
    # NASA API
    nasa_api_key: Optional[str] = None
    
    # Development
    debug: bool = False
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore" # Don't crash on extra env vars

settings = Settings()
