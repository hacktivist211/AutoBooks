from pathlib import Path
from typing import Dict
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# TDS Rate Constants
TDS_RENT = 10.0
TDS_SALARY = 5.0
TDS_CONSULTANCY = 10.0
TDS_CONTRACT = 5.0

# Confidence Threshold Constants
CONFIDENCE_HIGH = 0.75
CONFIDENCE_MEDIUM = 0.50

class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    # File paths
    inbox_path: Path = Field(default=Path("./inbox"))
    archive_path: Path = Field(default=Path("./archive"))
    chroma_db_path: Path = Field(default=Path("./chroma_db"))
    output_path: Path = Field(default=Path("./output"))
    config_path: Path = Field(default=Path("./config"))

    # Model configuration
    embedding_model: str = Field(default="BAAI/bge-m3")
    llm_model: str = Field(default="gemma3:4b")

    # Confidence thresholds
    confidence_threshold: float = Field(default=0.70)
    confidence_high: float = Field(default=CONFIDENCE_HIGH)
    confidence_medium: float = Field(default=CONFIDENCE_MEDIUM)

    # Text chunking
    chunk_size: int = Field(default=500)
    chunk_overlap: int = Field(default=50)

    # TDS configuration
    tds_rates: Dict[str, float] = Field(default={
        "rent": TDS_RENT,
        "salary": TDS_SALARY,
        "consultancy": TDS_CONSULTANCY,
        "contract": TDS_CONTRACT
    })
    tds_applicable_categories: list[str] = Field(default=["rent", "salary", "professional", "contract"])

    # Logging
    log_level: str = Field(default="DEBUG")

    # Supported file formats
    supported_formats: list[str] = Field(default=[".pdf", ".xlsx", ".txt"])

# Singleton instance
_settings: Settings | None = None

def get_settings() -> Settings:
    """Get the singleton settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
        # Ensure directories exist
        _settings.inbox_path.mkdir(parents=True, exist_ok=True)
        _settings.archive_path.mkdir(parents=True, exist_ok=True)
        _settings.chroma_db_path.mkdir(parents=True, exist_ok=True)
        _settings.output_path.mkdir(parents=True, exist_ok=True)
        _settings.config_path.mkdir(parents=True, exist_ok=True)
    return _settings

# Initialize settings
settings = get_settings()

# Backward compatibility - expose as module-level constants
BASE_DIR = Path(__file__).parent.parent
INBOX_PATH = settings.inbox_path.resolve()
ARCHIVE_PATH = settings.archive_path.resolve()
OUTPUT_PATH = settings.output_path.resolve()
CHROMA_DB_PATH = settings.chroma_db_path.resolve()
CONFIG_PATH = settings.config_path.resolve()

EMBEDDING_MODEL = settings.embedding_model
LLM_MODEL = settings.llm_model
CONFIDENCE_THRESHOLD = settings.confidence_threshold
CONFIDENCE_HIGH = settings.confidence_high
CONFIDENCE_MEDIUM = settings.confidence_medium
CHUNK_SIZE = settings.chunk_size
CHUNK_OVERLAP = settings.chunk_overlap

TDS_RATES = settings.tds_rates
TDS_APPLICABLE_CATEGORIES = settings.tds_applicable_categories

LOG_LEVEL = settings.log_level
SUPPORTED_FORMATS = settings.supported_formats

# Derived paths
EXCEL_OUTPUT_PATH = OUTPUT_PATH / "autobooks_ledger.xlsx"
RULES_PATH = CONFIG_PATH / "learned_rules.json"
DEDUP_CACHE_PATH = CONFIG_PATH / "invoice_cache.json"
