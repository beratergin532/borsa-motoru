from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "Autonomous Trading Engine"
    ENV: Literal["development", "paper_trading", "production"] = "paper_trading"
    DEBUG: bool = False
    
    GROQ_API_KEY: str = Field(default="", description="Groq API Key")
    GEMINI_API_KEY: str = Field(default="", description="Google AI Studio Gemini API Key")
    FINNHUB_API_KEY: str = Field(default="", description="Finnhub Financial Data API Key")
    OPENROUTER_API_KEY: str = Field(default="", description="OpenRouter API Key")

    MAX_POSITION_SIZE_PCT: float = 0.10
    DEFAULT_STOP_LOSS_PCT: float = 0.03
    
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: Path = BASE_DIR / "logs" / "app.log"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

def setup_logging(settings: Settings) -> None:
    settings.LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.remove()
    
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level=settings.LOG_LEVEL,
        colorize=True,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{function} - {message}"
    )
    
    logger.add(
        sink=settings.LOG_FILE_PATH,
        level=settings.LOG_LEVEL,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{function}:{line} - {message}"
    )

try:
    settings = Settings()
    setup_logging(settings)
    logger.info("Yapılandırma dosyası (config) başarıyla yüklendi.")
except Exception as e:
    print(f"KRİTİK HATA: Ayarlar yüklenemedi - {e}")
   