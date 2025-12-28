import re
from datetime import datetime
from typing import Optional, Tuple
from src.models import InvoiceFields
from src.logger import get_logger

logger = get_logger(__name__)

class InvoiceExtractor:
    """Extract structured fields from raw OCR text using regex patterns."""

    # Regex patterns for each field
    PATTERNS = {
        "vendor": [
            r"(?:Bill\s+to|From|Vendor|Supplier|Company)\s*[:\-]?\s*([A-Za-z\s&.,]+?)(?=\n|$|Amount|Total|Date)",
            r"(?:Billed\s+to|Invoice\s+from)\s*[:\-]?\s*([A-Za-z\s&.,]+?)(?=\n|$)",
        ],
        "amount": [
            r"(?:Total|Grand\s+Total|Amount|Net\s+Amount)\s*[:\-]?\s*(?:₹|Rs\.?|INR)?\s*(\d+(?:,\d+)*(?:\.\d{2})?)",
            r"(?:Total\s+Due|Amount\s+Due)\s*[:\-]?\s*(?:₹|Rs\.?|INR)?\s*(\d+(?:,\d+)*(?:\.\d{2})?)",
            r"(?:₹|Rs\.?|INR)\s*(\d+(?:,\d+)*(?:\.\d{2})?)\s*(?:Total|Grand|Net)",
        ],
        "date": [
            r"(?:Date|Invoice\s+Date|Bill\s+Date)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
            r"(?:Date|Invoice\s+Date|Bill\s+Date)\s*[:\-]?\s*(\d{4}[/-]\d{1,2}[/-]\d{1,2})",
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})\s*(?:Date|Invoice|Bill)",
            r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})\s*(?:Date|Invoice|Bill)",
        ],
        "tds_percentage": [
            r"(?:TDS|TDS\s+Rate)\s*[:\-]?\s*(\d+(?:\.\d+)?)%",
            r"(\d+(?:\.\d+)?)%\s*TDS",
        ],
        "tds_amount": [
            r"(?:TDS\s+Amount|TDS\s+Deducted)\s*[:\-]?\s*(?:₹|Rs\.?|INR)?\s*(\d+(?:,\d+)*(?:\.\d{2})?)",
            r"(?:₹|Rs\.?|INR)?\s*(\d+(?:,\d+)*(?:\.\d{2})?)\s*TDS",
        ],
    }

    @staticmethod
    def _clean_amount(amount_str: str) -> Optional[float]:
        """Clean and convert amount string to float."""
        if not amount_str:
            return None

        # Remove currency symbols and commas
        cleaned = re.sub(r'[₹Rs\.INR,\s]', '', amount_str)

        try:
            return float(cleaned)
        except ValueError:
            logger.warning(f"Could not parse amount: {amount_str}")
            return None

    @staticmethod
    def _parse_date(date_str: str) -> Optional[str]:
        """Parse date string to YYYY-MM-DD format."""
        if not date_str:
            return None

        # Try different formats
        formats = ['%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y', '%m-%d-%Y', '%Y-%m-%d', '%Y/%m/%d']
        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                return parsed.strftime('%Y-%m-%d')
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None

    @staticmethod
    def _extract_field(text: str, field_name: str) -> Tuple[Optional[str], bool]:
        """Extract a single field using regex patterns."""
        patterns = InvoiceExtractor.PATTERNS.get(field_name, [])

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                extracted = match.group(1).strip()
                logger.debug(f"Extracted {field_name}: {extracted}")
                return extracted, True

        logger.debug(f"Could not extract {field_name}")
        return None, False

    @classmethod
    def extract(cls, text: str) -> InvoiceFields:
        """
        Extract structured fields from raw OCR text.

        Args:
            text: Raw OCR text from PDF

        Returns:
            InvoiceFields model with extracted data
        """
        logger.info("Starting invoice field extraction")

        extracted_data = {}
        extracted_count = 0
        total_fields = len(cls.PATTERNS)

        # Extract each field
        for field_name in cls.PATTERNS.keys():
            raw_value, found = cls._extract_field(text, field_name)
            if found:
                extracted_count += 1

                # Parse based on field type
                if field_name == "amount":
                    parsed_value = cls._clean_amount(raw_value)
                elif field_name == "date":
                    parsed_value = cls._parse_date(raw_value)
                elif field_name in ["tds_percentage", "tds_amount"]:
                    parsed_value = cls._clean_amount(raw_value)
                else:
                    parsed_value = raw_value

                extracted_data[field_name] = parsed_value
            else:
                extracted_data[field_name] = None

        # Calculate confidence based on extraction success
        confidence = extracted_count / total_fields

        logger.info(f"Extraction complete: {extracted_count}/{total_fields} fields extracted, confidence: {confidence:.2%}")

        # Create InvoiceFields model
        return InvoiceFields(
            vendor=extracted_data.get("vendor", ""),
            amount=extracted_data.get("amount", 0.0),
            date=extracted_data.get("date", datetime.now().strftime('%Y-%m-%d')),
            tds_percentage=extracted_data.get("tds_percentage"),
            raw_text=text,
            confidence=confidence
        )