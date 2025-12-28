from typing import List, Optional
from src.models import InvoiceFields, Rule
from src.config import get_settings
from src.logger import get_logger

logger = get_logger(__name__)

class ConfidenceScorer:
    """Rule-based confidence scoring for invoice classification."""

    # Category keywords for initial guessing
    CATEGORY_KEYWORDS = {
        "rent": ["rent", "lease", "accommodation", "premises", "rental"],
        "consultancy": ["consult", "professional", "consulting", "fees", "services", "advice"],
        "salary": ["salary", "wages", "remuneration", "compensation", "payroll"],
        "contract": ["contract", "catering", "supply", "maintenance", "repair"]
    }

    def __init__(self):
        self.settings = get_settings()

    @classmethod
    def guess_category(cls, text: str) -> str:
        """
        Guess invoice category based on keywords in text.

        Args:
            text: Raw invoice text

        Returns:
            Category string: "rent", "consultancy", "salary", "contract", or "SUSPENSE"
        """
        text_lower = text.lower()

        for category, keywords in cls.CATEGORY_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                logger.debug(f"Guessed category '{category}' from keywords: {[k for k in keywords if k in text_lower]}")
                return category

        logger.debug("No category keywords found, defaulting to SUSPENSE")
        return "SUSPENSE"

    def calculate(self, invoice: InvoiceFields, rules: List[Rule]) -> float:
        """
        Calculate confidence score for invoice classification.

        Args:
            invoice: Extracted invoice fields
            rules: List of learned rules

        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.0

        # 1. Vendor found in learned rules (+0.35)
        vendor_rules = [rule for rule in rules if rule.vendor.lower() == invoice.vendor.lower()]
        if vendor_rules:
            score += 0.35
            logger.debug(f"Vendor '{invoice.vendor}' found in {len(vendor_rules)} learned rules")

        # 2. Keywords match invoice text (+0.30)
        if vendor_rules:
            # Check if any rule keywords appear in invoice text
            invoice_text = f"{invoice.vendor} {invoice.raw_text}".lower()
            for rule in vendor_rules:
                rule_keywords = [kw.lower() for kw in rule.keywords]
                if any(keyword in invoice_text for keyword in rule_keywords):
                    score += 0.30
                    logger.debug(f"Keywords matched for rule: {rule_keywords}")
                    break

        # 3. Amount in expected range (±20% of historical) (+0.20)
        if vendor_rules and invoice.amount:
            # Check if amount is within ±20% of any rule's historical amounts
            # For now, we'll use a simple check - if amount is reasonable (>100, <1M)
            # TODO: Implement proper historical amount tracking
            if 100 <= invoice.amount <= 1000000:
                score += 0.20
                logger.debug(f"Amount {invoice.amount} in expected range")
            else:
                logger.debug(f"Amount {invoice.amount} outside expected range")

        # 4. TDS percentage correct for category (+0.15)
        guessed_category = self.guess_category(invoice.raw_text)
        expected_tds = self.settings.tds_rates.get(guessed_category, 0)

        if invoice.tds_percentage and abs(invoice.tds_percentage - expected_tds) < 0.1:  # Allow small tolerance
            score += 0.15
            logger.debug(f"TDS {invoice.tds_percentage}% matches expected {expected_tds}% for category '{guessed_category}'")
        elif not invoice.tds_percentage and expected_tds == 0:
            # No TDS expected and none found
            score += 0.15
            logger.debug(f"No TDS expected or found for category '{guessed_category}'")

        final_score = min(score, 1.0)
        logger.info(f"Calculated confidence score: {final_score:.2%} for vendor '{invoice.vendor}'")
        return final_score