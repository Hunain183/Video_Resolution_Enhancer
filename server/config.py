"""
Server Configuration
"""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Directories
    BASE_DIR: str = str(Path(__file__).parent.parent)
    UPLOAD_DIR: str = str(Path(__file__).parent.parent / "temp" / "uploads")
    OUTPUT_DIR: str = str(Path(__file__).parent.parent / "temp" / "outputs")
    TEMP_DIR: str = str(Path(__file__).parent.parent / "temp" / "processing")
    MODELS_DIR: str = str(Path(__file__).parent.parent / "models")
    
    # File limits
    MAX_FILE_SIZE: int = 2 * 1024 * 1024 * 1024  # 2GB
    ALLOWED_EXTENSIONS: set = {".mp4", ".mov", ".webm", ".gif", ".avi", ".mkv"}
    FILE_RETENTION_HOURS: int = 2
    
    # Processing
    MAX_WORKERS: int = 4
    CHUNK_SIZE: int = 100  # Frames per chunk for batch processing
    
    # Video encoding
    VIDEO_CODEC: str = "libx265"
    AUDIO_CODEC: str = "aac"
    PIXEL_FORMAT: str = "yuv420p"
    
    # Bitrate targets (Mbps)
    BITRATE_1080P: str = "15M"
    BITRATE_1440P: str = "25M"
    BITRATE_4K: str = "40M"
    
    # Model paths
    ESRGAN_MODEL: str = "realesrgan-x4plus-anime"
    ESRGAN_FP16: bool = True
    ESRGAN_TILE: int = 200
    ESRGAN_TILE_PAD: int = 10
    
    class Config:
        env_file = ".env"


settings = Settings()
