import re
from typing import Dict, Optional, Tuple
from models import ExtractedFields, ExtractionResult
from logger import get_logger

logger = get_logger(__name__)

class FieldExtractor:
    """Deterministic regex-based field extraction from accounting documents."""
    
    # Regex patterns
    PATTERNS = {
        "invoice_id": [
            r"(?:Invoice|Invoice\s+(?:No|Number|#|ID))\s*[:=]?\s*([A-Z0-9\-/]+)",
            r"(?:Inv|INV)\s*(?:No|#|ID)\s*[:=]?\s*([A-Z0-9\-/]+)",
        ],
        "invoice_date": [
            r"(?:Invoice|Invoice\s+Date|Date)\s*[:=]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
            r"(?:Date|Dated)\s*[:=]?\s*(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})",
        ],
        "vendor_name": [
            r"(?:Bill|Billed|Invoice)\s+(?:To|from)\s*[:=]?\s*([A-Z][A-Za-z\s&.,]+?)(?=\n|Amount|Invoice|₹|\$)",
            r"(?:Vendor|Supplier|Company|Organization)\s*[:=]?\s*([A-Z][A-Za-z\s&.,]+?)(?=\n|Amount)",
        ],
        "amount": [
            r"(?:Total|Amount|Due|Grand\s+Total)\s*[:=]?\s*(?:₹|Rs|Rs\.|INR)?\s*(\d+(?:[,.]?\d+)*\.?\d*)",
            r"(?:Amount|Total|Net)\s+(?:Due|Payable)\s*[:=]?\s*(?:₹|Rs)?\s*(\d+(?:[,.]?\d+)*\.?\d*)",
        ],
        "gst_percent": [
            r"(?:SGST|CGST|GST)\s*@?\s*(\d+\.?\d*)%",
            r"(?:IGST|GST|Tax)\s*(?:Rate|@)\s*(\d+\.?\d*)%",
        ],
        "gst_amount": [
            r"(?:SGST|CGST|IGST|GST|Tax)\s*(?:Amount|Amt)?\s*[:=]?\s*(?:₹|Rs)?\s*(\d+(?:[,.]?\d+)*\.?\d*)",
        ],
        "tds_amount": [
            r"(?:TDS|Tax\s+Deducted)\s*[:=]?\s*(?:₹|Rs)?\s*(\d+(?:[,.]?\d+)*\.?\d*)",
            r"(?:Deduction|Withholding\s+Tax)\s*[:=]?\s*(?:₹|Rs)?\s*(\d+(?:[,.]?\d+)*\.?\d*)",
        ],
        "tds_category": [
            r"(?:TDS|Withholding)\s+(?:Category|Type|Section)\s*[:=]?\s*(rent|salary|professional|contract)",
        ],
    }
    
    @staticmethod
    def clean_amount(amount_str: str) -> Optional[float]:
        """Clean and convert amount string to float."""
        if not amount_str:
            return None
        
        # Remove currency symbols, spaces
        cleaned = re.sub(r'[₹Rs$,\s]', '', amount_str)
        
        try:
            return float(cleaned)
        except ValueError:
            logger.warning(f"Could not convert amount: {amount_str}")
            return None
    
    @staticmethod
    def extract_fields(text: str, metadata: Optional[Dict] = None) -> ExtractionResult:
        """Extract accounting fields from document text."""
        
        logger.info("Extracting fields from document")
        fields = ExtractedFields(raw_text=text)
        confidence_breakdown = {}
        
        # Extract each field
        # Invoice ID
        for pattern in FieldExtractor.PATTERNS["invoice_id"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields.invoice_id = match.group(1).strip()
                confidence_breakdown["invoice_id"] = 0.95
                logger.debug(f"Found invoice_id: {fields.invoice_id}")
                break
        if not fields.invoice_id:
            confidence_breakdown["invoice_id"] = 0.0
        
        # Invoice Date
        for pattern in FieldExtractor.PATTERNS["invoice_date"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields.invoice_date = match.group(1).strip()
                confidence_breakdown["invoice_date"] = 0.90
                logger.debug(f"Found invoice_date: {fields.invoice_date}")
                break
        if not fields.invoice_date:
            confidence_breakdown["invoice_date"] = 0.0
        
        # Vendor Name
        for pattern in FieldExtractor.PATTERNS["vendor_name"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields.vendor_name = match.group(1).strip()
                confidence_breakdown["vendor_name"] = 0.85
                logger.debug(f"Found vendor_name: {fields.vendor_name}")
                break
        if not fields.vendor_name:
            confidence_breakdown["vendor_name"] = 0.0
        
        # Amount
        for pattern in FieldExtractor.PATTERNS["amount"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields.amount = FieldExtractor.clean_amount(match.group(1))
                confidence_breakdown["amount"] = 0.92 if fields.amount else 0.0
                logger.debug(f"Found amount: {fields.amount}")
                break
        if not fields.amount:
            confidence_breakdown["amount"] = 0.0
        
        # GST Percent
        for pattern in FieldExtractor.PATTERNS["gst_percent"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    fields.gst_percent = float(match.group(1))
                    confidence_breakdown["gst_percent"] = 0.90
                    logger.debug(f"Found gst_percent: {fields.gst_percent}")
                except ValueError:
                    pass
                break
        if not fields.gst_percent:
            confidence_breakdown["gst_percent"] = 0.0
        
        # GST Amount
        for pattern in FieldExtractor.PATTERNS["gst_amount"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields.gst_amount = FieldExtractor.clean_amount(match.group(1))
                confidence_breakdown["gst_amount"] = 0.88 if fields.gst_amount else 0.0
                logger.debug(f"Found gst_amount: {fields.gst_amount}")
                break
        if not fields.gst_amount:
            confidence_breakdown["gst_amount"] = 0.0
        
        # TDS Amount
        for pattern in FieldExtractor.PATTERNS["tds_amount"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields.tds_amount = FieldExtractor.clean_amount(match.group(1))
                confidence_breakdown["tds_amount"] = 0.85 if fields.tds_amount else 0.0
                logger.debug(f"Found tds_amount: {fields.tds_amount}")
                break
        if not fields.tds_amount:
            confidence_breakdown["tds_amount"] = 0.0
        
        # TDS Category
        for pattern in FieldExtractor.PATTERNS["tds_category"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields.tds_category = match.group(1).lower()
                confidence_breakdown["tds_category"] = 0.88
                logger.debug(f"Found tds_category: {fields.tds_category}")
                break
        if not fields.tds_category:
            confidence_breakdown["tds_category"] = 0.0
        
        # Calculate overall confidence
        if confidence_breakdown:
            overall_confidence = sum(confidence_breakdown.values()) / len(confidence_breakdown)
        else:
            overall_confidence = 0.0
        
        result = ExtractionResult(
            fields=fields,
            confidence_score=overall_confidence,
            confidence_breakdown=confidence_breakdown
        )
        
        logger.info(f"Extraction complete. Overall confidence: {overall_confidence:.2%}")
        return result
