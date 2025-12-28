#!/usr/bin/env python3
"""
AutoBooks - Intelligent Accounting Document Processing System
Main entry point for demo and testing
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from orchestrator import AutoBooksOrchestrator
from logger import get_logger

logger = get_logger(__name__)

def main():
    """Main entry point."""
    
    try:
        # Initialize orchestrator
        orchestrator = AutoBooksOrchestrator()
        
        # Run demo
        results = orchestrator.run_demo()
        
        return 0
    
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
