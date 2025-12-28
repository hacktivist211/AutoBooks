import json
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from models import ExtractedFields, ExtractionResult, TransactionEntry
from field_extractor import FieldExtractor
from ledger_classifier import LedgerClassifier
from embedding_manager import EmbeddingManager
from llm_manager import LLMManager
from logger import get_logger

logger = get_logger(__name__)

class SelfRAGAgent:
    """Self-Reflective RAG agent for intelligent document classification with user feedback."""
    
    def __init__(self, rules_path: Path, embedding_manager: EmbeddingManager, llm_manager: LLMManager = None, confidence_threshold: float = 0.70):
        self.rules_path = rules_path
        self.embedding_manager = embedding_manager
        self.llm_manager = llm_manager or LLMManager()
        self.confidence_threshold = confidence_threshold
        self.learned_rules: Dict = self._load_rules()
    
    def _load_rules(self) -> Dict:
        """Load learned rules from disk."""
        if self.rules_path.exists():
            try:
                with open(self.rules_path, "r") as f:
                    rules = json.load(f)
                logger.info(f"Loaded {len(rules)} learned rules")
                return rules
            except Exception as e:
                logger.warning(f"Could not load rules: {str(e)}")
        return {}
    
    def _save_rules(self):
        """Persist learned rules to disk."""
        try:
            self.rules_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.rules_path, "w") as f:
                json.dump(self.learned_rules, f, indent=2)
            logger.info(f"Saved {len(self.learned_rules)} learned rules")
        except Exception as e:
            logger.error(f"Could not save rules: {str(e)}")
    
    def process_document(
        self,
        text: str,
        document_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Full processing pipeline: extract → validate → classify → SELF-RAG → decide."""
        
        logger.info(f"Processing document: {document_id}")
        
        # Step 1: Extract fields
        extraction_result = FieldExtractor.extract_fields(text, metadata)
        logger.info(f"Extraction confidence: {extraction_result.confidence_score:.2%}")
        
        # Step 2: Validate extracted fields
        validation_errors = self._validate_fields(extraction_result.fields)
        extraction_result.is_validated = len(validation_errors) == 0
        extraction_result.validation_errors = validation_errors
        
        if validation_errors:
            logger.warning(f"Validation errors: {validation_errors}")
        
        # Step 3: Classify to ledger accounts
        ledger_classification = LedgerClassifier.classify_ledger_accounts(
            extraction_result.fields,
            self.learned_rules
        )
        
        # Step 4: SELF-RAG - Check confidence threshold
        if ledger_classification["confidence"] < self.confidence_threshold:
            logger.info(f"Low confidence ({ledger_classification['confidence']:.2%}) - Triggering SELF-RAG")
            
            # Query ChromaDB for similar context
            similar_chunks = self._retrieve_context(extraction_result.fields)
            
            # Try to reason with context
            refined_decision = self._reason_with_context(
                extraction_result.fields,
                ledger_classification,
                similar_chunks
            )
            
            # If still uncertain, mark for user review
            if refined_decision["confidence"] < self.confidence_threshold:
                logger.info("Confidence still low after context retrieval - Flagging for user")
                refined_decision["status"] = "needs_review"
            
            ledger_classification = refined_decision
        
        # Step 5: Generate transaction entry
        transaction = self._create_transaction_entry(
            document_id,
            extraction_result.fields,
            ledger_classification
        )
        
        return {
            "document_id": document_id,
            "extraction": extraction_result,
            "ledger_classification": ledger_classification,
            "transaction": transaction,
            "status": ledger_classification.get("status", "approved")
        }
    
    def _validate_fields(self, fields: ExtractedFields) -> List[str]:
        """Validate extracted fields."""
        errors = []
        
        if not fields.invoice_id:
            errors.append("Missing invoice ID")
        
        if not fields.invoice_date:
            errors.append("Missing invoice date")
        
        if not fields.vendor_name:
            errors.append("Missing vendor name")
        
        if fields.amount is None or fields.amount <= 0:
            errors.append("Invalid or missing amount")
        
        # Validate TDS if present
        if fields.tds_amount and fields.tds_amount > 0:
            if not fields.tds_category:
                errors.append("TDS amount present but category missing")
            
            if fields.tds_category and fields.tds_category not in ["rent", "salary", "professional", "contract"]:
                errors.append(f"Invalid TDS category: {fields.tds_category}")
        
        return errors
    
    def _retrieve_context(self, fields: ExtractedFields) -> Dict:
        """Query ChromaDB for similar invoices."""
        
        # Build query from available fields
        query_parts = []
        if fields.vendor_name:
            query_parts.append(f"vendor {fields.vendor_name}")
        if fields.tds_category:
            query_parts.append(f"TDS category {fields.tds_category}")
        if fields.description:
            query_parts.append(fields.description)
        
        query_text = " ".join(query_parts) or "expense invoice transaction"
        
        logger.debug(f"Querying similar chunks: {query_text}")
        
        similar = self.embedding_manager.query_similar_chunks(
            query_text=query_text,
            n_results=3
        )
        
        return similar
    
    def _reason_with_context(
        self,
        fields: ExtractedFields,
        classification: Dict,
        similar_chunks: Dict
    ) -> Dict:
        """Reason about classification using similar context."""
        
        if not similar_chunks["ids"]:
            logger.debug("No similar context found")
            return classification
        
        # Analyze similar documents
        logger.info(f"Found {len(similar_chunks['ids'])} similar documents")
        
        # Try to infer from similar documents' metadata
        similar_categories = []
        for metadata in similar_chunks["metadatas"]:
            if "category" in metadata:
                similar_categories.append(metadata["category"])
        
        if similar_categories:
            # Use majority category from similar documents
            from collections import Counter
            most_common = Counter(similar_categories).most_common(1)[0][0]
            
            if classification["debit_account"] != most_common:
                logger.info(f"Refining classification based on context: {most_common}")
                classification["debit_account"] = most_common
                classification["debit_code"] = LedgerClassifier.EXPENSE_ACCOUNTS.get(most_common, "5099")
                classification["confidence"] = min(0.85, classification["confidence"] + 0.15)
                classification["applied_rule"] = "context_based_reasoning"
        
        return classification
    
    def _create_transaction_entry(
        self,
        document_id: str,
        fields: ExtractedFields,
        classification: Dict
    ) -> TransactionEntry:
        """Create structured transaction entry."""
        
        # Calculate net amount (considering TDS)
        net_amount = fields.amount
        if fields.tds_amount:
            net_amount = fields.amount - fields.tds_amount
        
        transaction = TransactionEntry(
            transaction_id=f"TXN_{document_id}_{datetime.now().timestamp()}",
            document_id=document_id,
            date=fields.invoice_date or datetime.now().strftime("%Y-%m-%d"),
            debit_account=classification.get("debit_account", "unknown"),
            debit_amount=fields.amount or 0,
            credit_account=classification.get("credit_account", "unknown"),
            credit_amount=net_amount or 0,
            tds_account="2006" if fields.tds_amount else None,  # TDS payable account
            tds_amount=fields.tds_amount,
            description=fields.description or f"Invoice {fields.invoice_id}",
            gst_amount=fields.gst_amount,
            confidence_score=classification.get("confidence", 0.0),
            rule_applied=classification.get("applied_rule"),
            status=classification.get("status", "approved")
        )
        
        return transaction
    
    def learn_from_correction(
        self,
        vendor_name: str,
        correction: Dict
    ):
        """Learn from user correction and store as rule."""
        
        if not vendor_name:
            logger.warning("Cannot learn rule without vendor name")
            return
        
        rule = {
            "vendor_name": vendor_name,
            "debit_account": correction.get("debit_account"),
            "debit_code": correction.get("debit_code"),
            "credit_account": correction.get("credit_account"),
            "credit_code": correction.get("credit_code"),
            "learned_at": datetime.now().isoformat(),
            "correction_reason": correction.get("reason", "user_feedback")
        }
        
        self.learned_rules[vendor_name] = rule
        self._save_rules()
        
        logger.info(f"Learned rule for vendor: {vendor_name}")
