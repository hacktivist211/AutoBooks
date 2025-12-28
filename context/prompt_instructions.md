# AUTOBOOKS - MASTER CONTEXT FOR AI CODING ASSISTANT

## PROJECT OVERVIEW
AutoBooks is an intelligent accounting document processing system that automates invoice/voucher entry into Tally ERP. It uses Self-RAG (Self-Reflective Retrieval-Augmented Generation) to learn from user corrections and improve classification accuracy over time.

## CORE PROBLEM
Accounting teams manually enter transaction data from scanned invoices into Tally daily. This is tedious, error-prone, and repetitive. AutoBooks watches an inbox folder, extracts invoice details, classifies them to the correct ledger accounts, and generates Tally-compatible Excel output.

## KEY INNOVATION: SELF-RAG
Traditional RAG just retrieves and answers. Our Self-RAG:
1. **Attempts classification** using regex + context
2. **Judges its own confidence** (0.0 to 1.0 score)
3. **If confident (≥0.75)**: Auto-posts the transaction
4. **If uncertain (0.5-0.75)**: Retrieves similar patterns from ChromaDB
5. **If still uncertain (<0.5)**: Asks user ONCE via CLI
6. **Learns forever**: Saves user correction as a rule, never asks again

## TECHNICAL ARCHITECTURE

```
INPUT: ./data/inbox (PDFs dropped here)
         ↓
[Document Monitor] → Detects new files (Pathway or simple polling)
         ↓
[OCR Engine] → Tesseract extracts text from PDF
         ↓
[Field Extractor] → Regex extracts: vendor, amount, date, TDS%
         ↓
[Confidence Scorer] → Rule-based scoring (0.0-1.0)
         ↓
[Decision Tree]
  ├─ ≥0.75? → AUTO-POST (create entry)
  ├─ ≥0.50? → Query ChromaDB for similar invoices
  │           → Still unsure? Ask user
  └─ <0.50? → Ask user directly
         ↓
[Rule Learning] → Save correction to rules.json + ChromaDB
         ↓
[Excel Writer] → Append row to ledger.xlsx (Tally-compatible)
         ↓
OUTPUT: Structured Excel file ready for Tally import
```

## TECH STACK
- **Streaming**: Pathway (preferred) or watchdog (fallback)
- **OCR**: Tesseract via pdf2image + pytesseract
- **Extraction**: Regex (deterministic, fast, no LLM needed)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Vector Store**: ChromaDB (persistent, local, no API)
- **Rules**: JSON file (version-controlled, human-readable)
- **Output**: openpyxl (Excel generation)
- **Config**: pydantic + python-dotenv

## FILE STRUCTURE
```
AutoBooks/
├── src/
│   ├── config.py           # Pydantic settings + TDS rates
│   ├── models.py           # Data models (Invoice, Transaction, etc.)
│   ├── ocr.py              # PDF → Text extraction
│   ├── extractor.py        # Text → Fields (regex-based)
│   ├── confidence.py       # Confidence scoring logic
│   ├── vector_store.py     # ChromaDB wrapper
│   ├── rules.py            # Rule learning + matching
│   ├── agent.py            # Self-RAG orchestrator
│   └── excel_writer.py     # Excel output generation
├── data/
│   ├── inbox/              # Drop PDFs here
│   ├── archive/            # Processed files
│   ├── chroma_db/          # Vector store
│   └── ledger.xlsx         # Output
├── config/
│   └── rules.json          # Learned rules
├── main.py                 # Entry point
└── requirements.txt
```

## KEY DATA MODELS

### Invoice (Extracted Fields)
```python
{
    "vendor": str,           # "ABC Consultancy"
    "amount": float,         # 50000.0
    "date": str,            # "2024-12-28"
    "tds_percentage": float, # 10.0
    "raw_text": str,        # Full OCR output
    "confidence": float     # 0.0-1.0
}
```

### Transaction (Ledger Entry)
```python
{
    "date": str,
    "vendor": str,
    "debit_account": str,    # "Consultancy Charges"
    "debit_amount": float,   # 50000.0
    "credit_account": str,   # "ABC Consultancy (Payable)"
    "credit_amount": float,  # 45000.0 (after TDS)
    "tds_account": str,      # "TDS Payable"
    "tds_amount": float,     # 5000.0
    "confidence": float,
    "status": str           # "AUTO_POSTED" | "USER_CONFIRMED"
}
```

### Rule (Learned Pattern)
```python
{
    "vendor": str,
    "keywords": list[str],   # ["rent", "lease"]
    "debit_account": str,
    "credit_account": str,
    "tds_applicable": bool,
    "learned_at": str,
    "applied_count": int
}
```

## CONFIDENCE SCORING RULES
```python
base_score = 0.0

# Check vendor in learned rules
if vendor in rules:
    base_score += 0.35
    
# Check keywords match
if rule_keywords in invoice_text:
    base_score += 0.30
    
# Check amount in expected range
if amount_reasonable:
    base_score += 0.20
    
# Check TDS applicability
if tds_detected:
    base_score += 0.15

return min(base_score, 1.0)
```

## TDS RULES (Hardcoded)
```python
TDS_RATES = {
    "rent": 10.0,           # 10% TDS on rent
    "salary": 5.0,          # 5% TDS on salary
    "consultancy": 10.0,    # 10% TDS on professional fees
    "contract": 5.0         # 5% TDS on contracts
}
```

## REGEX PATTERNS (Examples)
```python
PATTERNS = {
    "vendor": r"(?:Bill to|From|Vendor)[:\s]+([A-Za-z\s\.]+)",
    "amount": r"(?:Total|Grand Total)[:\s]+₹?\s*([\d,]+\.?\d*)",
    "date": r"(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
    "tds": r"TDS[:\s]+(\d+)%"
}
```

## CODING GUIDELINES FOR COPILOT

### 1. Always Use Type Hints
```python
def extract_amount(text: str) -> float | None:
    """Extract total amount from invoice text."""
    # Copilot will autocomplete better
```

### 2. Document All Functions
```python
"""
Extract vendor name from OCR text using regex patterns.

Args:
    text: Raw OCR output from invoice
    
Returns:
    Vendor name string or "UNKNOWN" if not found
    
Example:
    >>> extract_vendor("Bill to: ABC Corp")
    'ABC Corp'
"""
```

### 3. Use Pydantic for Validation
```python
from pydantic import BaseModel, Field

class InvoiceData(BaseModel):
    vendor: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    date: str
```

### 4. Handle Errors Gracefully
```python
try:
    amount = float(amount_str.replace(",", ""))
except (ValueError, AttributeError):
    logger.warning(f"Failed to parse amount: {amount_str}")
    return None
```

### 5. Keep Functions Single-Purpose
```python
# GOOD: One clear job
def calculate_tds(amount: float, category: str) -> float:
    """Calculate TDS deduction for given category."""
    return amount * (TDS_RATES.get(category, 0) / 100)

# BAD: Too many responsibilities
def process_everything(filepath):
    # OCR, extract, classify, write...
```

## SELF-RAG FLOW (PSEUDOCODE)
```python
def process_invoice(filepath: str) -> Transaction:
    # 1. EXTRACT
    text = ocr_engine.extract_text(filepath)
    fields = extractor.extract_fields(text)
    
    # 2. SCORE CONFIDENCE
    confidence = scorer.calculate_confidence(fields)
    
    # 3. DECISION TREE
    if confidence >= 0.75:
        # HIGH CONFIDENCE: Auto-post
        return create_transaction(fields, status="AUTO_POSTED")
        
    elif confidence >= 0.50:
        # MEDIUM: Try ChromaDB retrieval
        similar = vector_store.query_similar(fields.vendor, text)
        
        if similar and similar[0].distance < 0.3:
            # Found close match, use that
            return create_transaction_from_rule(similar[0])
        else:
            # Still unsure, ask user
            return ask_user_and_learn(fields)
            
    else:
        # LOW CONFIDENCE: Ask user immediately
        return ask_user_and_learn(fields)
```

## CHROMADB USAGE
```python
# Initialize (once)
client = chromadb.PersistentClient(path="./data/chroma_db")
collection = client.get_or_create_collection("vendor_patterns")

# Add pattern (when user corrects)
embedding = model.encode(f"{vendor} {keywords}")
collection.add(
    ids=[f"rule_{timestamp}"],
    embeddings=[embedding],
    metadatas=[{
        "vendor": vendor,
        "category": category,
        "amount_range": f"{amount * 0.8}-{amount * 1.2}"
    }]
)

# Query (during classification)
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=3,
    where={"vendor": vendor}  # Optional filter
)
```

## EXCEL OUTPUT FORMAT (Tally-Compatible)
```
Date       | Vendor      | Debit Account        | Debit Amt | Credit Account    | Credit Amt | TDS Account | TDS Amt | Status
-----------|-------------|----------------------|-----------|-------------------|------------|-------------|---------|-------------
2024-12-28 | ABC Corp    | Consultancy Charges  | 50000.00  | ABC Corp (Pay)    | 45000.00   | TDS Payable | 5000.00 | AUTO_POSTED
```

## CRITICAL RULES
1. **No External APIs**: Everything runs offline (embeddings are local)
2. **Regex First**: Don't overthink extraction, regex is fast and deterministic
3. **Simple Confidence**: Rule-based scoring, no ML training needed
4. **Learn Once**: User corrections are saved forever, never re-ask
5. **Incremental Processing**: Each file is independent, no batch reprocessing
6. **Error Handling**: Every function should handle None/empty gracefully
7. **Logging**: Use Python logging, not print statements
8. **Testing**: Each module should be testable independently

## DEMO SCRIPT (5 minutes)
1. **Start system**: `python main.py`
2. **Drop Invoice 1**: New vendor (Dhruv Consultancy, ₹10,000)
   - System asks: "Is this Rent or Consultancy?"
   - User types: "Consultancy"
   - Rule saved
3. **Drop Invoice 2**: Same vendor (Dhruv, ₹8,000)
   - System auto-classifies as Consultancy
   - Shows learning in action
4. **Drop Invoice 3**: Different vendor (XYZ Corp, ₹25,000)
   - ChromaDB finds similar "consultancy" pattern
   - Auto-posts
5. **Show Excel**: Open ledger.xlsx, see 3 rows
6. **Show Rules**: Open config/rules.json, see learned patterns

## SUCCESS CRITERIA
- ✅ 5 invoices processed in < 2 minutes
- ✅ At least 1 rule learned from user feedback
- ✅ Excel file generated with proper columns
- ✅ ChromaDB contains embeddings
- ✅ Code is clean, documented, and tested
- ✅ Demo runs smoothly without crashes

---

**Use this context when prompting GitHub Copilot for ANY file in the project.**