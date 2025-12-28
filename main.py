#!/usr/bin/env python3
"""
AutoBooks - Intelligent Accounting Document Processing System
Main orchestrator that watches inbox folder and processes invoices
"""

import sys
import time
import hashlib
import signal
from pathlib import Path
from typing import Set

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent import SelfRAGAgent
from excel_writer import ExcelLedger
from config import get_settings
from logger import get_logger

logger = get_logger(__name__)

class AutoBooksOrchestrator:
    """Main orchestrator for AutoBooks processing pipeline."""

    def __init__(self):
        """Initialize the orchestrator."""
        self.settings = get_settings()
        self.agent = SelfRAGAgent()
        self.excel_writer = ExcelLedger(str(self.settings.output_path / "autobooks_ledger.xlsx"))

        # Setup folders
        self.inbox_path = self.settings.inbox_path
        self.archive_path = self.settings.archive_path
        self.inbox_path.mkdir(parents=True, exist_ok=True)
        self.archive_path.mkdir(parents=True, exist_ok=True)

        # Track processed files
        self.processed_hashes: Set[str] = set()
        self.stats = {
            "files_processed": 0,
            "auto_posted": 0,
            "user_confirmed": 0,
            "pattern_matched": 0,
            "errors": 0
        }

        # Handle graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info("AutoBooks Orchestrator initialized")

    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        logger.info("Received shutdown signal, saving state...")
        self._print_final_stats()
        sys.exit(0)

    def _calculate_file_hash(self, filepath: Path) -> str:
        """Calculate SHA256 hash of file for deduplication."""
        hash_sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _move_to_archive(self, filepath: Path):
        """Move processed file to archive folder."""
        try:
            archive_name = f"{filepath.stem}_processed{filepath.suffix}"
            archive_path = self.archive_path / archive_name
            filepath.rename(archive_path)
            logger.info(f"Moved {filepath.name} to archive")
        except Exception as e:
            logger.error(f"Failed to move {filepath.name} to archive: {e}")

    def _process_file(self, filepath: Path):
        """Process a single invoice file."""
        try:
            logger.info(f"Processing: {filepath.name}")

            # Process with agent
            transaction = self.agent.process_invoice(str(filepath))

            # Write to Excel
            self.excel_writer.append_transaction(transaction)

            # Update stats
            self.stats["files_processed"] += 1
            if "AUTO_POSTED" in transaction.status:
                self.stats["auto_posted"] += 1
            elif "USER_CONFIRMED" in transaction.status:
                self.stats["user_confirmed"] += 1
            elif "PATTERN_MATCHED" in transaction.status:
                self.stats["pattern_matched"] += 1

            # Print summary
            print(f"✓ Processed: {transaction.vendor} | ₹{transaction.debit_amount:,.2f} | {transaction.debit_account} | {transaction.status}")

            # Move to archive
            self._move_to_archive(filepath)

        except Exception as e:
            logger.error(f"Error processing {filepath.name}: {e}")
            self.stats["errors"] += 1
            print(f"✗ Failed: {filepath.name} - {str(e)}")

    def _scan_inbox(self) -> list[Path]:
        """Scan inbox for new PDF and TXT files."""
        new_files = []
        for pattern in ["*.pdf", "*.txt"]:
            for file_path in self.inbox_path.glob(pattern):
                if file_path.is_file():
                    file_hash = self._calculate_file_hash(file_path)
                    if file_hash not in self.processed_hashes:
                        self.processed_hashes.add(file_hash)
                        new_files.append(file_path)

        return new_files

    def _print_banner(self):
        """Print startup banner."""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                    🤖 AUTOBOOKS v1.0                        ║
║          Intelligent Accounting Document Processing         ║
║                                                              ║
║  Watches inbox folder for PDF invoices                      ║
║  Extracts data with OCR + AI                                ║
║  Learns from user corrections                               ║
║  Outputs Tally-compatible Excel                             ║
║                                                              ║
║  Press Ctrl+C to stop and save state                        ║
╚══════════════════════════════════════════════════════════════╝
        """
        print(banner)

    def _print_stats(self):
        """Print current statistics."""
        summary = self.excel_writer.get_summary()
        print(f"\n📊 Stats: {self.stats['files_processed']} processed | "
              f"🤖 {self.stats['auto_posted']} auto | "
              f"👤 {self.stats['user_confirmed']} manual | "
              f"🔍 {self.stats['pattern_matched']} matched | "
              f"❌ {self.stats['errors']} errors")
        print(f"💰 Totals: ₹{summary['total_debit']:,.2f} debit | ₹{summary['total_credit']:,.2f} credit | ₹{summary['total_tds']:,.2f} TDS")

    def _print_final_stats(self):
        """Print final statistics on shutdown."""
        print("\n" + "="*60)
        print("AUTOBOOKS SESSION COMPLETE")
        print("="*60)
        self._print_stats()
        print(f"\n📁 Excel saved: {self.settings.output_path / 'autobooks_ledger.xlsx'}")
        print(f"📁 Archive: {self.archive_path}")
        print("="*60)

    def run(self):
        """Main processing loop."""
        self._print_banner()

        logger.info(f"Watching inbox: {self.inbox_path}")
        print(f"📂 Watching: {self.inbox_path}")
        print("Drop PDF invoices here to process them...")
        # Initial scan
        initial_files = self._scan_inbox()
        if initial_files:
            print(f"📄 Found {len(initial_files)} existing files, processing...")
            for file_path in initial_files:
                self._process_file(file_path)

        self._print_stats()

        # Continuous monitoring
        print("🔄 Monitoring for new files... (Ctrl+C to stop)")

        try:
            while True:
                time.sleep(2)  # Poll every 2 seconds

                new_files = self._scan_inbox()
                if new_files:
                    print(f"\n📄 Detected {len(new_files)} new file(s)")
                    for file_path in new_files:
                        self._process_file(file_path)

                    self._print_stats()

        except KeyboardInterrupt:
            pass

        self._print_final_stats()

def main():
    """Main entry point."""
    try:
        orchestrator = AutoBooksOrchestrator()
        orchestrator.run()
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
