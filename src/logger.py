import logging
import sys
import os
from pathlib import Path

def get_logger(name: str) -> logging.Logger:
    """Get or create a logger instance."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Get log level from env, default to DEBUG
        log_level = os.getenv("LOG_LEVEL", "DEBUG")
        logger.setLevel(getattr(logging, log_level, logging.DEBUG))
    
    return logger
