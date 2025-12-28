import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
from src.models import InvoiceFields, Transaction, Rule
from src.ocr_engine import extract_text_from_pdf
from src.invoice_extractor import InvoiceExtractor
from src.confidence_scorer import ConfidenceScorer
from src.vector_store import VectorStore
from src.rules import RulesManager
from src.config import get_settings
from src.logger import get_logger

logger = get_logger(__name__)

class SelfRAGAgent:
    """Self-RAG agent orchestrator - the brain of AutoBooks."""

    def __init__(self):
        self.settings = get_settings()
        self.extractor = InvoiceExtractor()
        self.confidence_scorer = ConfidenceScorer()
        self.vector_store = VectorStore(str(self.settings.chroma_db_path))
        self.rules_manager = RulesManager()

    def process_invoice(self, filepath: str) -> Transaction:
        """
        Main processing pipeline for invoice classification.

        Args:
            filepath: Path to PDF or TXT invoice file

        Returns:
            Transaction object with classification results
        """
        logger.info(f"Starting Self-RAG processing for: {filepath}")

        file_path = Path(filepath)
        file_ext = file_path.suffix.lower()

        # Step 1: Extract text based on file type
        logger.info("Step 1: Text extraction")
        if file_ext == '.pdf':
            ocr_result = extract_text_from_pdf(filepath)
            if not ocr_result["success"]:
                logger.error(f"OCR failed: {ocr_result['error']}")
                return self._create_error_transaction(filepath, "OCR_FAILED")
            raw_text = ocr_result["text"]
        elif file_ext == '.txt':
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    raw_text = f.read()
                logger.info(f"Text file read: {len(raw_text)} characters")
            except Exception as e:
                logger.error(f"Failed to read text file: {e}")
                return self._create_error_transaction(filepath, "READ_FAILED")
        else:
            logger.error(f"Unsupported file type: {file_ext}")
            return self._create_error_transaction(filepath, "UNSUPPORTED_FORMAT")

        logger.info(f"Text extraction successful: {len(raw_text)} characters")

        # Step 2: Extract structured fields
        logger.info("Step 2: Field extraction")
        invoice = self.extractor.extract(raw_text)
        logger.info(f"Extracted invoice: {invoice.vendor}, Amount: ₹{invoice.amount}, Confidence: {invoice.confidence:.1%}")

        # Step 3: Load existing rules
        rules = self.rules_manager.get_all_rules()
        logger.info(f"Loaded {len(rules)} existing rules")

        # Step 4: Calculate confidence
        logger.info("Step 4: Confidence scoring")
        confidence = self.confidence_scorer.calculate(invoice, rules)
        logger.info(f"Calculated confidence: {confidence:.2%}")

        # Step 5: Decision Tree
        if confidence >= self.settings.confidence_high:  # >= 0.75
            logger.info("High confidence - AUTO-POSTING")
            category = self.confidence_scorer.guess_category(invoice.raw_text)
            return self._create_transaction(invoice, category, "AUTO_POSTED")

        elif confidence >= self.settings.confidence_medium:  # >= 0.50
            logger.info("Medium confidence - Querying ChromaDB for similar patterns")

            # Query vector store for similar patterns
            similar_patterns = self.vector_store.query_similar(
                invoice.vendor,
                invoice.raw_text,
                n_results=3
            )

            # Check if any similar pattern has high similarity (>0.8)
            best_match = None
            for pattern in similar_patterns:
                if pattern["similarity_score"] > 0.8:
                    best_match = pattern
                    break

            if best_match:
                logger.info(f"Found similar pattern: {best_match['vendor']} -> {best_match['category']}")
                return self._create_transaction(invoice, best_match["category"], "PATTERN_MATCHED")
            else:
                logger.info("No good pattern match found - asking user")
                return self._ask_user_and_process(invoice, rules)

        else:  # < 0.50
            logger.info("Low confidence - asking user directly")
            return self._ask_user_and_process(invoice, rules)

    def _ask_user_and_process(self, invoice: InvoiceFields, rules: list[Rule]) -> Transaction:
        """
        Ask user for classification and learn from their input.

        Args:
            invoice: Extracted invoice fields
            rules: Existing rules list

        Returns:
            Transaction with user's classification
        """
        # Ask user for category
        category = self._ask_user(invoice)

        # Create transaction
        transaction = self._create_transaction(invoice, category, "USER_CONFIRMED")

        # Learn from user's choice
        self._learn_from_user_choice(invoice, category, rules)

        return transaction

    def _ask_user(self, invoice: InvoiceFields) -> str:
        """
        Interactive CLI prompt for user classification.

        Args:
            invoice: Invoice details to show user

        Returns:
            Selected category string
        """
        print("\n" + "="*60)
        print("AUTOBOOKS - MANUAL CLASSIFICATION REQUIRED")
        print("="*60)
        print(f"Vendor: {invoice.vendor}")
        print(f"Amount: ₹{invoice.amount:,.2f}")
        print(f"Date: {invoice.date}")
        print(f"TDS: {invoice.tds_percentage}%")
        print(f"Confidence: {invoice.confidence:.1%}")
        print("\nSelect category:")
        print("1. Rent (10% TDS)")
        print("2. Consultancy (10% TDS)")
        print("3. Salary (5% TDS)")
        print("4. Contract (5% TDS)")
        print("5. Other (no TDS)")
        print("="*60)

        category_map = {
            "1": "rent",
            "2": "consultancy",
            "3": "salary",
            "4": "contract",
            "5": "other"
        }

        while True:
            try:
                choice = input("Enter choice (1-5): ").strip()
                if choice in category_map:
                    selected = category_map[choice]
                    print(f"Selected: {selected}")
                    return selected
                else:
                    print("Invalid choice. Please enter 1-5.")
            except KeyboardInterrupt:
                print("\nOperation cancelled by user")
                sys.exit(1)
            except EOFError:
                print("\nNo input received")
                return "other"

    def _create_transaction(self, invoice: InvoiceFields, category: str, status: str) -> Transaction:
        """
        Create a Transaction object from invoice and category.

        Args:
            invoice: Extracted invoice fields
            category: Classified category
            status: Transaction status

        Returns:
            Transaction object
        """
        # Calculate TDS
        tds_amount = self._calculate_tds(invoice.amount, category)

        # Determine accounts based on category
        account_mapping = {
            "rent": {"debit": "Rent Expense", "credit": f"{invoice.vendor} (Payable)"},
            "consultancy": {"debit": "Professional Fees", "credit": f"{invoice.vendor} (Payable)"},
            "salary": {"debit": "Salary Expense", "credit": f"{invoice.vendor} (Payable)"},
            "contract": {"debit": "Contract Expense", "credit": f"{invoice.vendor} (Payable)"},
            "other": {"debit": "Miscellaneous Expense", "credit": f"{invoice.vendor} (Payable)"}
        }

        accounts = account_mapping.get(category, account_mapping["other"])

        # Create transaction
        transaction = Transaction(
            date=invoice.date,
            vendor=invoice.vendor,
            debit_account=accounts["debit"],
            debit_amount=invoice.amount,
            credit_account=accounts["credit"],
            credit_amount=invoice.amount - tds_amount,
            tds_account="TDS Payable" if tds_amount > 0 else None,
            tds_amount=tds_amount if tds_amount > 0 else None,
            confidence=invoice.confidence,
            status=status
        )

        logger.info(f"Created transaction: {transaction.vendor} -> {accounts['debit']} (₹{invoice.amount})")
        return transaction

    def _calculate_tds(self, amount: float, category: str) -> float:
        """
        Calculate TDS amount based on category.

        Args:
            amount: Invoice amount
            category: Expense category

        Returns:
            TDS amount to deduct
        """
        tds_rate = self.settings.tds_rates.get(category, 0.0)
        if tds_rate > 0:
            tds_amount = (amount * tds_rate) / 100
            logger.debug(f"TDS calculation: ₹{amount} * {tds_rate}% = ₹{tds_amount}")
            return tds_amount
        return 0.0

    def _learn_from_user_choice(self, invoice: InvoiceFields, category: str, existing_rules: list[Rule]):
        """
        Learn from user's classification choice.

        Args:
            invoice: Invoice that was classified
            category: User's chosen category
            existing_rules: Existing rules list
        """
        logger.info(f"Learning from user choice: {invoice.vendor} -> {category}")

        # Extract keywords from invoice text
        keywords = self._extract_keywords(invoice.raw_text, category)

        # Create new rule
        new_rule = Rule(
            vendor=invoice.vendor,
            keywords=keywords,
            debit_account=self._get_debit_account(category),
            credit_account=f"{invoice.vendor} (Payable)",
            tds_applicable=category in self.settings.tds_applicable_categories,
            learned_at=datetime.now(),
            applied_count=1
        )

        # Save to rules manager
        self.rules_manager.save_rule(new_rule)

        # Add to vector store
        self.vector_store.add_pattern(
            vendor=invoice.vendor,
            keywords=keywords,
            category=category,
            amount=invoice.amount
        )

        logger.info(f"Learned new rule for vendor '{invoice.vendor}' in category '{category}'")

    def _extract_keywords(self, text: str, category: str) -> list[str]:
        """
        Extract relevant keywords from invoice text.

        Args:
            text: Raw invoice text
            category: Classified category

        Returns:
            List of keywords
        """
        # Get category-specific keywords
        category_keywords = self.confidence_scorer.CATEGORY_KEYWORDS.get(category, [])

        # Extract additional keywords from text (vendor names, etc.)
        # Simple keyword extraction - split text and filter meaningful words
        words = text.lower().split()
        vendor_words = [word for word in words if len(word) > 2 and word.isalpha()]

        # Combine and deduplicate
        all_keywords = list(set(category_keywords + vendor_words))

        # Limit to top 5 most relevant
        return all_keywords[:5]

    def _get_debit_account(self, category: str) -> str:
        """
        Get debit account name for category.

        Args:
            category: Expense category

        Returns:
            Account name
        """
        account_map = {
            "rent": "Rent Expense",
            "consultancy": "Professional Fees",
            "salary": "Salary Expense",
            "contract": "Contract Expense",
            "other": "Miscellaneous Expense"
        }
        return account_map.get(category, "Miscellaneous Expense")