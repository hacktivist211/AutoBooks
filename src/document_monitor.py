from pathlib import Path
from typing import Callable, Optional, Dict, List
import time
import hashlib
from datetime import datetime
from logger import get_logger

logger = get_logger(__name__)

class DocumentMonitor:
    """Monitor inbox folder for document changes (simulating Pathway behavior)."""
    
    def __init__(self, inbox_path: Path, poll_interval: int = 2):
        self.inbox_path = Path(inbox_path)
        self.poll_interval = poll_interval
        self.known_files: Dict[str, str] = {}  # filename -> hash mapping
        self.supported_formats = [".pdf", ".xlsx", ".txt"]
    
    def get_file_hash(self, file_path: Path) -> str:
        """Generate hash of file."""
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"Error hashing file {file_path}: {str(e)}")
            return ""
    
    def scan_inbox(self) -> Dict[str, str]:
        """Scan inbox and return file changes."""
        
        if not self.inbox_path.exists():
            logger.warning(f"Inbox path does not exist: {self.inbox_path}")
            return {}
        
        changes = {
            "added": [],
            "modified": [],
            "deleted": [],
            "files": {}  # Current state
        }
        
        # Get current files
        current_files = {}
        for file_path in self.inbox_path.glob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                file_hash = self.get_file_hash(file_path)
                current_files[file_path.name] = file_hash
        
        # Detect added files
        for filename, file_hash in current_files.items():
            if filename not in self.known_files:
                logger.info(f"New file detected: {filename}")
                changes["added"].append(filename)
        
        # Detect modified and deleted files
        for filename, known_hash in self.known_files.items():
            if filename not in current_files:
                logger.info(f"File deleted: {filename}")
                changes["deleted"].append(filename)
            elif current_files[filename] != known_hash:
                logger.info(f"File modified: {filename}")
                changes["modified"].append(filename)
        
        # Update known files
        self.known_files = current_files
        changes["files"] = current_files
        
        return changes
    
    def start_monitoring(self, callback: Callable, stop_event = None):
        """Start real-time monitoring loop."""
        logger.info(f"Started monitoring inbox: {self.inbox_path}")
        
        try:
            while True:
                if stop_event and stop_event.is_set():
                    logger.info("Stopping monitor")
                    break
                
                changes = self.scan_inbox()
                
                if changes["added"] or changes["modified"] or changes["deleted"]:
                    callback(changes)
                
                time.sleep(self.poll_interval)
        
        except KeyboardInterrupt:
            logger.info("Monitor interrupted")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {str(e)}")
            raise
    
    def get_files(self) -> List[Path]:
        """Get list of all valid files in inbox."""
        files = []
        if self.inbox_path.exists():
            for file_path in self.inbox_path.glob("*"):
                if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                    files.append(file_path)
        return files
