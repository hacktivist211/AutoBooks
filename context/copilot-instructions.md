# AutoBooks AI Coding Guidelines

## Architecture Overview
AutoBooks implements a SELF-RAG pipeline for intelligent accounting document processing:
- **Inbox Monitor** → **Document Decoder** → **Text Chunker** → **Embedding Manager** → **SELF-RAG Agent** → **Excel Ledger**
- Uses ChromaDB for vector storage, Ollama for LLM reasoning, regex-based field extraction with confidence scoring

## Key Patterns & Conventions

### Data Models
Use Pydantic `BaseModel` for all structured data:
```python
class TransactionEntry(BaseModel):
    transaction_id: str
    debit_account: str  # Always use account names, not codes
    debit_amount: float
    # ... other fields
```

New models added:
- `InvoiceFields`: Core extracted invoice data with validation
- `Transaction`: Accounting transaction records
- `Rule`: Learned classification rules for vendors

### OCR Engine
- Use `ocr_engine.extract_text_from_pdf(filepath)` for PDF text extraction
- Converts PDF to images (DPI=150) using pdf2image, then OCR with pytesseract
- Returns dict with success status, extracted text, page count, and error details
- Handles corrupted PDFs and missing files gracefully

### Invoice Extraction
- Use `InvoiceExtractor.extract(text)` to get structured `InvoiceFields` from raw OCR text
- Extracts 5 key fields using multiple regex patterns per field
- Parses amounts to float, dates to YYYY-MM-DD format
- Confidence score based on successful field extractions (0-1)

### Confidence Scoring
- Use `ConfidenceScorer.calculate(invoice, rules)` for rule-based confidence scoring
- Scores based on: vendor in learned rules (+0.35), keywords match (+0.30), amount range (+0.20), TDS correctness (+0.15)
- Use `ConfidenceScorer.guess_category(text)` for initial category guessing from keywords
- Returns confidence score 0.0-1.0

### Vector Store
- Use `VectorStore` class for ChromaDB operations with sentence-transformers
- `add_pattern(vendor, keywords, category, amount)` to store learned rules
- `query_similar(vendor, text, n_results)` to find similar patterns with similarity scores
- Stores embeddings of vendor + keywords, retrieves with cosine similarity

### Rules Manager
- Use `RulesManager` for persistent rule storage in JSON
- `load_rules()` loads from config/rules.json
- `save_rule(rule)` appends new rules atomically
- `find_matching(vendor, keywords)` finds existing rules
- Thread-safe operations with temp file writes

### Self-RAG Agent
- Use `SelfRAGAgent.process_invoice(filepath)` as the main entry point
- Implements the complete decision tree: OCR → Extract → Score → Decide → Learn
- Auto-posts high confidence (>75%), queries vector store for medium confidence, asks user for low confidence
- Learns from user corrections and updates both rules.json and ChromaDB
- Returns `Transaction` objects with full accounting details

### Excel Writer
- Use `ExcelLedger` class for Tally-compatible Excel output
- `append_transaction(txn)` adds formatted rows with color coding
- Auto-posts (green), user-confirmed (yellow), pattern-matched (blue)
- `get_summary()` provides totals and statistics
- Currency formatting and column auto-sizing

### Main Orchestrator
- Run `python main.py` to start the continuous file watcher
- Monitors `inbox/` folder for new PDFs using polling
- SHA256 deduplication prevents reprocessing
- Processes files through SelfRAGAgent → ExcelLedger pipeline
- Moves processed files to `archive/` folder
- Real-time statistics and graceful Ctrl+C shutdown

### Field Extraction
Implement regex patterns in `FieldExtractor.PATTERNS` with confidence scores:
```python
PATTERNS = {
    "invoice_id": [r"(?:Invoice|Inv)\s*(?:No|#|ID)\s*[:=]?\s*([A-Z0-9\-/]+)", ...],
    # Confidence: 0.95 for invoice_id, 0.85 for vendor_name
}
```

### Classification Logic
- Check `learned_rules.json` first for vendor-specific overrides (confidence 0.99)
- Fall back to keyword matching in `LedgerClassifier.CATEGORY_KEYWORDS`
- Use TDS category when available for expense classification

### SELF-RAG Flow
When confidence < threshold (default 0.70):
1. Query ChromaDB for similar document chunks
2. Use LLM to reason with retrieved context
3. Apply learned rules from user corrections

### Configuration
- Load from `.env` with `python-dotenv`
- Paths auto-create directories via `Path.mkdir(parents=True, exist_ok=True)`
- Use absolute paths for file operations

### Logging
- Import `get_logger(__name__)` from `logger.py`
- Use appropriate levels: `info` for pipeline steps, `debug` for details, `warning` for low confidence

### Testing
- Run `python test_core_logic.py` for quick validation without heavy models
- Test components independently: extraction → classification → chunking

### Dependencies
- Core: `chromadb`, `sentence-transformers`, `ollama`, `pydantic`
- OCR: `pytesseract`, `pdf2image` (requires system Tesseract)
- Output: `openpyxl`, `pandas`

## Common Workflows
- **Add new field**: Update `ExtractedFields` model, add regex in `FieldExtractor`, handle in `SelfRAGAgent`
- **New expense category**: Add to `LedgerClassifier.EXPENSE_ACCOUNTS` and `CATEGORY_KEYWORDS`
- **Debug low confidence**: Check ChromaDB queries, review learned rules, adjust threshold in config
- **User corrections**: Call `orchestrator.handle_user_correction()` to learn vendor rules