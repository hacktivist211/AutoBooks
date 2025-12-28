from typing import Dict, Tuple, List, Optional
from models import ExtractedFields
from logger import get_logger

logger = get_logger(__name__)

class LedgerClassifier:
    """Classify extracted fields to ledger accounts with confidence scoring."""
    
    # Ledger account mappings
    EXPENSE_ACCOUNTS = {
        "rent": "5001",
        "utilities": "5002",
        "office_supplies": "5003",
        "professional_fees": "5004",
        "catering": "5005",
        "equipment": "5006",
        "travel": "5007",
        "maintenance": "5008",
        "advertising": "5009",
        "other_expenses": "5099"
    }
    
    PARTY_ACCOUNTS = {
        "landlord": "4001",
        "utilities_vendor": "4002",
        "supplier": "4003",
        "professional": "4004",
        "contractor": "4005",
        "employee": "4006",
    }
    
    # Category keywords for classification
    CATEGORY_KEYWORDS = {
        "rent": ["rent", "lease", "accommodation", "premises"],
        "salary": ["salary", "wages", "remuneration", "compensation"],
        "professional": ["professional", "consultancy", "consulting", "fees", "services"],
        "contract": ["contract", "catering", "supply", "services"],
        "utilities": ["electricity", "water", "gas", "internet", "phone"],
        "office_supplies": ["stationery", "supplies", "office", "equipment"],
        "travel": ["travel", "flight", "hotel", "transport", "cab"],
        "maintenance": ["maintenance", "repair", "cleaning", "service"],
    }
    
    @staticmethod
    def classify_category(vendor_name: str, description: str = "") -> Tuple[str, float]:
        """Classify transaction category based on vendor and description."""
        
        combined_text = f"{vendor_name} {description}".lower()
        scores = {}
        
        for category, keywords in LedgerClassifier.CATEGORY_KEYWORDS.items():
            # Count keyword matches
            matches = sum(1 for kw in keywords if kw in combined_text)
            scores[category] = matches / len(keywords) if keywords else 0
        
        if not scores or max(scores.values()) == 0:
            return "other_expenses", 0.3
        
        best_category = max(scores, key=scores.get)
        confidence = scores[best_category]
        
        logger.debug(f"Classified '{vendor_name}' as '{best_category}' (confidence: {confidence:.2%})")
        return best_category, confidence
    
    @staticmethod
    def classify_ledger_accounts(
        fields: ExtractedFields,
        learned_rules: Optional[Dict] = None
    ) -> Dict[str, any]:
        """Classify document to ledger accounts with confidence."""
        
        learned_rules = learned_rules or {}
        result = {
            "debit_account": None,
            "debit_code": None,
            "credit_account": None,
            "credit_code": None,
            "confidence": 0.0,
            "applied_rule": None,
            "flags": []
        }
        
        # Check if we have a learned rule for this vendor
        if fields.vendor_name and fields.vendor_name in learned_rules:
            rule = learned_rules[fields.vendor_name]
            result["debit_code"] = rule["debit_code"]
            result["debit_account"] = rule["debit_account"]
            result["credit_code"] = rule["credit_code"]
            result["credit_account"] = rule["credit_account"]
            result["confidence"] = 0.99  # High confidence for learned rules
            result["applied_rule"] = f"learned_rule_{fields.vendor_name}"
            logger.info(f"Applied learned rule for vendor: {fields.vendor_name}")
            return result
        
        # Classify based on vendor name and TDS category
        category = fields.tds_category
        vendor_confidence = 0.0
        
        if not category:
            # Try to infer from vendor name
            category, vendor_confidence = LedgerClassifier.classify_category(
                fields.vendor_name or "Unknown",
                fields.description or ""
            )
        else:
            # TDS category is explicit
            vendor_confidence = 0.90
        
        # Map to debit account (expense account)
        if category in LedgerClassifier.EXPENSE_ACCOUNTS:
            result["debit_code"] = LedgerClassifier.EXPENSE_ACCOUNTS[category]
            result["debit_account"] = category
        else:
            result["debit_code"] = LedgerClassifier.EXPENSE_ACCOUNTS["other_expenses"]
            result["debit_account"] = "other_expenses"
            result["flags"].append(f"Category '{category}' mapped to 'other_expenses'")
        
        # Map to credit account (party account)
        # Determine party type from category
        party_type = LedgerClassifier._get_party_type(category)
        if party_type in LedgerClassifier.PARTY_ACCOUNTS:
            result["credit_code"] = LedgerClassifier.PARTY_ACCOUNTS[party_type]
            result["credit_account"] = party_type
        else:
            result["credit_code"] = LedgerClassifier.PARTY_ACCOUNTS["supplier"]
            result["credit_account"] = "supplier"
            result["flags"].append(f"Party type '{party_type}' mapped to 'supplier'")
        
        # Overall confidence
        result["confidence"] = vendor_confidence
        
        if result["confidence"] < 0.7:
            result["flags"].append("Low confidence - SELF-RAG retrieval recommended")
        
        return result
    
    @staticmethod
    def _get_party_type(category: str) -> str:
        """Get party type based on expense category."""
        mapping = {
            "rent": "landlord",
            "salary": "employee",
            "professional": "professional",
            "contract": "contractor",
            "utilities": "utilities_vendor",
            "office_supplies": "supplier",
            "travel": "supplier",
            "maintenance": "contractor",
        }
        return mapping.get(category, "supplier")
