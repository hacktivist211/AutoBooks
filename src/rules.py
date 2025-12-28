import json
import threading
from pathlib import Path
from typing import List, Optional
from src.models import Rule
from src.config import get_settings
from src.logger import get_logger

logger = get_logger(__name__)

class RulesManager:
    """Rule learning and persistence system for AutoBooks."""

    def __init__(self):
        self.settings = get_settings()
        self.rules_file = self.settings.config_path / "rules.json"
        self._lock = threading.Lock()  # Thread-safe operations
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create rules.json file if it doesn't exist."""
        if not self.rules_file.exists():
            self.rules_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.rules_file, 'w') as f:
                json.dump({"rules": []}, f, indent=2)
            logger.info(f"Created new rules file: {self.rules_file}")

    def load_rules(self) -> List[Rule]:
        """
        Load all learned rules from JSON file.

        Returns:
            List of Rule objects
        """
        with self._lock:
            try:
                with open(self.rules_file, 'r') as f:
                    data = json.load(f)

                rules = []
                for rule_data in data.get("rules", []):
                    try:
                        rule = Rule(**rule_data)
                        rules.append(rule)
                    except Exception as e:
                        logger.warning(f"Failed to load rule: {e}")

                logger.info(f"Loaded {len(rules)} rules from {self.rules_file}")
                return rules

            except FileNotFoundError:
                logger.warning(f"Rules file not found: {self.rules_file}")
                return []
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in rules file: {e}")
                return []

    def save_rule(self, rule: Rule):
        """
        Append a new rule to the JSON file atomically.

        Args:
            rule: Rule object to save
        """
        with self._lock:
            # Load existing rules
            rules = self.load_rules()

            # Check if rule already exists (by exact vendor match)
            for existing_rule in rules:
                if existing_rule.vendor.lower() == rule.vendor.lower():
                    logger.info(f"Rule for vendor '{rule.vendor}' already exists, skipping save")
                    return

            # Add new rule
            rules.append(rule)

            # Save atomically using temp file
            temp_file = self.rules_file.with_suffix('.tmp')
            try:
                with open(temp_file, 'w') as f:
                    data = {"rules": [rule.model_dump() for rule in rules]}
                    json.dump(data, f, indent=2, default=str)

                # Atomic rename
                temp_file.replace(self.rules_file)
                logger.info(f"Saved new rule for vendor '{rule.vendor}' to {self.rules_file}")

            except Exception as e:
                # Clean up temp file if it exists
                if temp_file.exists():
                    temp_file.unlink()
                logger.error(f"Failed to save rule: {e}")
                raise

    def find_matching(self, vendor: str, keywords: Optional[List[str]] = None) -> Optional[Rule]:
        """
        Find a matching rule for the given vendor and optionally keywords.

        Args:
            vendor: Vendor name to match
            keywords: Optional list of keywords to match (for fuzzy matching)

        Returns:
            Matching Rule object or None
        """
        rules = self.load_rules()

        # First, try exact vendor match
        vendor_lower = vendor.lower()
        for rule in rules:
            if rule.vendor.lower() == vendor_lower:
                return rule

        # If no exact vendor match and keywords provided, try keyword matching
        if keywords:
            keywords_lower = [kw.lower() for kw in keywords]
            for rule in rules:
                rule_keywords_lower = [kw.lower() for kw in rule.keywords]
                # Require at least 2 matching keywords for fuzzy match
                matches = sum(1 for kw in keywords_lower if kw in rule_keywords_lower)
                if matches >= 2:
                    logger.debug(f"Fuzzy match found for vendor '{vendor}' with {matches} keyword matches")
                    return rule

        return None

    def get_all_rules(self) -> List[Rule]:
        """
        Return all learned rules.

        Returns:
            List of all Rule objects
        """
        return self.load_rules()

    def increment_usage(self, vendor: str):
        """
        Increment the applied count for a vendor's rule.

        Args:
            vendor: Vendor name whose rule was applied
        """
        with self._lock:
            rules = self.load_rules()

            for rule in rules:
                if rule.vendor.lower() == vendor.lower():
                    rule.applied_count += 1
                    break

            # Save updated rules
            temp_file = self.rules_file.with_suffix('.tmp')
            try:
                with open(temp_file, 'w') as f:
                    data = {"rules": [rule.model_dump() for rule in rules]}
                    json.dump(data, f, indent=2, default=str)

                temp_file.replace(self.rules_file)
                logger.debug(f"Incremented usage count for vendor '{vendor}'")

            except Exception as e:
                if temp_file.exists():
                    temp_file.unlink()
                logger.error(f"Failed to increment usage: {e}")