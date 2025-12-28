import os
from pathlib import Path
from dotenv import load_dotenv
import json

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent.parent
INBOX_PATH = Path(os.getenv("INBOX_PATH", "./inbox")).resolve()
OUTPUT_PATH = Path(os.getenv("OUTPUT_PATH", "./output")).resolve()
CHROMA_DB_PATH = Path(os.getenv("CHROMA_DB_PATH", "./chroma_db")).resolve()
CONFIG_PATH = Path(os.getenv("CONFIG_PATH", "./config")).resolve()

# Create directories if they don't exist
INBOX_PATH.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
CONFIG_PATH.mkdir(parents=True, exist_ok=True)

# Model Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma3:4b")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.70))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 500))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))

# TDS Configuration
TDS_RATES_STR = os.getenv("TDS_RATES", '{"rent": 10, "salary": 5, "professional": 10, "contract": 5}')
TDS_RATES = json.loads(TDS_RATES_STR)
TDS_APPLICABLE_CATEGORIES = ["rent", "salary", "professional", "contract"]

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")

# Supported file extensions
SUPPORTED_FORMATS = [".pdf", ".xlsx", ".txt"]

# Output files
EXCEL_OUTPUT_PATH = OUTPUT_PATH / "autobooks_ledger.xlsx"
RULES_PATH = CONFIG_PATH / "learned_rules.json"
DEDUP_CACHE_PATH = CONFIG_PATH / "invoice_cache.json"
