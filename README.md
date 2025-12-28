# AutoBooks - Intelligent Accounting Document Processing System

## Overview

AutoBooks is a live, agentic accounting system designed to demonstrate how SELF-RAG can be applied to real-world financial workflows. It continuously monitors an inbox folder for incoming or updated accounting documents, incrementally processes them using a streaming data pipeline, and extracts key accounting information such as parties, amounts, and descriptions. The system classifies transactions into appropriate ledger accounts with confidence-aware reasoning and, when ambiguity arises, incorporates one-time user feedback as persistent knowledge. This learned context is applied immediately to future documents, allowing AutoBooks to adapt in real time while producing continuously updated, Excel-ready accounting outputs suitable for downstream financial workflows.

### Key Features

 **Real-time Document Monitoring** - Watches inbox for new/modified PDF and Excel files

 **Intelligent Text Extraction** - OCR for PDFs, parsing for structured data

 **Smart Chunking** - Semantic text chunking with overlap for context preservation

 **Vector Embeddings** - Sentence Transformers + ChromaDB for semantic search

 **SELF-RAG Agent** - Confidence-aware classification with context retrieval

 **TDS Handling** - Automatic TDS deduction for rent, salary, professional services, contracts

 **Rule Learning** - Learns from user corrections and applies rules to future documents

 **Live Excel Output** - Continuously updated ledger with transaction details

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        INBOX MONITOR                        │
│         (Real-time document stream detection)               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    DOCUMENT DECODER                         │
│         (OCR, parsing, text extraction)                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    TEXT CHUNKER                             │
│       (Semantic chunking with overlap for context)          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 EMBEDDING MANAGER                           │
│    (Sentence Transformers → ChromaDB vector store)          │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         │
┌──────────────────┐              │
│ SELF-RAG AGENT   │              │
│ ┌──────────────┐ │              │
│ │ Extraction   │ │              │
│ │ Validation   │ │              │
│ │ Confidence   │ │──────────────┤
│ │ Assessment   │ │    Query     │
│ │              │ │    ChromaDB  │
│ │ Low Conf? ───┼──────────────► │
│ │ Retrieve     │ │              │
│ │ Context      │ │              │
│ │ Reason       │ │              │
│ │ Learn Rules  │ │              │
│ └──────────────┘ │              │
└────────────────┬─┘              │
                 │                │
        ┌────────┴────────┐       │
        │                 │       │
        ▼                 ▼       │
┌──────────────────┐              │
│ LEDGER           │              │
│ CLASSIFIER       │◄─────────────┘
└────────────────┬─┘
                 │
                 ▼
┌──────────────────────────────────────┐
│  TRANSACTION GENERATOR               │
│  (Journal entries, TDS calculations) │
└────────────────┬─────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────┐
│  EXCEL LEDGER OUTPUT                 │
│  (Live, continuously updated)        │
└──────────────────────────────────────┘
```

## System Components

### 1. **document_monitor.py** - Real-time Inbox Monitoring
- Simulates Pathway filesystem connector
- Detects file additions, modifications, deletions
- Maintains file state via hashing
- Polls inbox at configurable interval

### 2. **document_decoder.py** - Multi-Format Document Extraction
- **PDF OCR**: Uses Tesseract via pdf2image
- **Excel Parsing**: Reads structured data from sheets
- **Metadata Extraction**: Document IDs, timestamps, hash for deduplication

### 3. **text_chunker.py** - Intelligent Text Segmentation
- Configurable chunk size and overlap
- Respects word/line boundaries for semantic integrity
- Preserves document context across chunks

### 4. **embedding_manager.py** - Vector Store Integration
- SentenceTransformers for embeddings (all-MiniLM-L6-v2)
- ChromaDB for persistent vector storage
- Supports semantic similarity search
- Incremental chunk updates

### 5. **field_extractor.py** - Deterministic Field Extraction
Regex-based extraction with confidence scoring:
- **Invoice ID** (95% confidence)
- **Date** (90%)
- **Vendor Name** (85%)
- **Amount** (92%)
- **GST %/Amount** (90%/88%)
- **TDS Amount** (85%)
- **TDS Category** (88%)

### 6. **ledger_classifier.py** - Intelligent Account Classification
- Multi-class expense category classification
- Vendor → Party account mapping
- Confidence-based decision making
- Handles multiple TDS categories

### 7. **self_rag_agent.py** - The Core Intelligence 

**SELF-RAG Flow:**
```
1. EXTRACTION
   └─ Extract fields with confidence scores

2. VALIDATION  
   └─ Check field completeness and formats

3. CLASSIFICATION
   └─ Map to ledger accounts
   └─ Calculate confidence

4. CONFIDENCE CHECK
   └─ If confidence >= threshold → Approve ✓
   └─ If confidence < threshold → Retrieve Context

5. CONTEXT RETRIEVAL
   └─ Query ChromaDB for similar invoices
   └─ Extract patterns from similar documents

6. REASONING
   └─ Analyze similar documents' categorizations
   └─ Refine initial decision with evidence

7. DECISION
   └─ If confidence now OK → Approve ✓
   └─ If still uncertain → Flag for User Review

8. RULE LEARNING
   └─ Store user correction as vendor-specific rule
   └─ Apply rule to future documents from same vendor
```

### 8. **excel_ledger.py** - Live Output Management
- Formatted Excel with headers and styling
- Auto-append transaction rows
- Status color coding (green=approved, red=flagged)
- Summary statistics calculation
- Maintains running ledger

### 9. **orchestrator.py** - Master Pipeline Orchestrator
- Coordinates all components
- Manages document lifecycle
- Handles user corrections and rule learning
- Provides summary statistics

## Setup & Installation

### Prerequisites
- Python 3.10+
- Tesseract OCR (for PDF processing)
- System packages: `poppler-utils`

### Installation

```bash
# On Ubuntu/Debian
sudo apt-get install tesseract-ocr poppler-utils

# On macOS
brew install tesseract poppler

# Python packages
pip install -r requirements.txt
```

### Environment Configuration

Edit `.env`:
```
INBOX_PATH=./inbox
OUTPUT_PATH=./output
CHROMA_DB_PATH=./chroma_db
CONFIG_PATH=./config

EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CONFIDENCE_THRESHOLD=0.70
CHUNK_SIZE=500
CHUNK_OVERLAP=50

LOG_LEVEL=DEBUG
```

## Project Structure

```
AutoBooks/
├── src/
│   ├── __init__.py
│   ├── config.py                  # Configuration & paths
│   ├── logger.py                  # Logging setup
│   ├── models.py                  # Pydantic data models
│   ├── document_decoder.py        # PDF/Excel parsing
│   ├── document_monitor.py        # Real-time monitoring
│   ├── text_chunker.py            # Text segmentation
│   ├── embedding_manager.py       # ChromaDB integration
│   ├── field_extractor.py         # Regex extraction
│   ├── ledger_classifier.py       # Account classification
│   ├── self_rag_agent.py          # Core SELF-RAG logic
│   ├── excel_ledger.py            # Excel output
│   └── orchestrator.py            # Pipeline orchestrator
├── inbox/                         # Input document folder
├── output/                        # Output location
│   └── autobooks_ledger.xlsx      # Live Excel ledger
├── config/                        # Persistent storage
│   ├── learned_rules.json         # Vendor-specific rules
│   └── processed_cache.json       # Deduplication cache
├── chroma_db/                     # Vector store
├── main.py                        # Entry point
├── requirements.txt               # Dependencies
├── .env                           # Configuration
└── README.md                      # This file
```

## Usage

### Demo Mode

```bash
# Run the complete pipeline on current inbox contents
python main.py
```

**Output:**
```
======================================================================
AUTOBOOKS - Intelligent Accounting Document Processing
======================================================================

Scanning inbox: ./inbox
==============================================================
Processing: sample_invoice_001.txt
==============================================================
Step 1: Decoding document...
Step 2: Chunking text...
Step 3: Embedding and upserting to ChromaDB...
Step 4: Running SELF-RAG agent...
Step 5: Writing to Excel ledger...

✓ Document processed successfully
  Transaction ID: TXN_sample_invoice_001_1735...
  Invoice ID: INV-2024-001
  Vendor: Premium Office Furnishings
  Amount: 47200.0
  Confidence: 88.00%
  Status: approved

[Similar output for remaining documents...]

==============================================================
Processing Complete!
Total documents processed: 3

Ledger Summary:
  Total Transactions: 3
  Total Debit: ₹197,200.00
  Total Credit: ₹178,000.00
  Total TDS: ₹15,000.00
  Average Confidence: 86.67%
  Status Breakdown: {'approved': 3}

Output files:
  Excel Ledger: /path/to/output/autobooks_ledger.xlsx
  Learned Rules: /path/to/config/learned_rules.json
======================================================================
```

### Programmatic Usage

```python
from src.orchestrator import AutoBooksOrchestrator

# Initialize
orchestrator = AutoBooksOrchestrator()

# Process inbox
results = orchestrator.process_inbox()

# Handle user correction
orchestrator.handle_user_correction(
    document_id="sample_invoice_001_1735...",
    correction={
        "vendor_name": "Premium Office Furnishings",
        "debit_account": "office_supplies",
        "debit_code": "5003",
        "credit_account": "supplier",
        "credit_code": "4003",
        "confidence": 0.99,
        "reason": "user_feedback"
    }
)

# Get summary
summary = orchestrator.get_ledger_summary()
print(f"Total transactions: {summary['total_transactions']}")
```

## Ledger Accounts Reference

### Expense Accounts (Debit)
- **5001**: Rent
- **5002**: Utilities
- **5003**: Office Supplies
- **5004**: Professional Fees
- **5005**: Catering
- **5006**: Equipment
- **5007**: Travel
- **5008**: Maintenance
- **5009**: Advertising
- **5099**: Other Expenses

### Party Accounts (Credit)
- **4001**: Landlord
- **4002**: Utilities Vendor
- **4003**: Supplier
- **4004**: Professional
- **4005**: Contractor
- **4006**: Employee

## TDS (Tax Deducted at Source) Handling

TDS is automatically calculated for:
- **Rent**: 10%
- **Salary**: 5%
- **Professional/Consultancy**: 10%
- **Contracts**: 5%

When TDS is present:
```
Debit: Expense Account (Full Amount)
Credit: Party Account (Amount - TDS)
Credit: TDS Payable Account (TDS Amount)
```

## Confidence Scoring

The SELF-RAG agent scores each field:
- **High Confidence** (>85%): Automatically approved
- **Medium Confidence** (70-85%): Approved with context
- **Low Confidence** (<70%): Flagged for user review

Confidence factors:
- Field extraction accuracy
- Vendor recognition
- Category clarity
- Validation status

## Rule Learning Example

### Initial Processing (Low Confidence)
```
Vendor: "XYZ Consulting"
Extracted Category: Unknown (confidence 0.45)
Status: Flagged for review
```

### User Correction
```json
{
  "vendor_name": "XYZ Consulting",
  "debit_account": "professional_fees",
  "debit_code": "5004",
  "credit_account": "professional",
  "credit_code": "4004"
}
```

### Learned Rule Saved
```json
{
  "XYZ Consulting": {
    "debit_account": "professional_fees",
    "debit_code": "5004",
    "credit_account": "professional",
    "credit_code": "4004",
    "learned_at": "2024-12-28T10:30:00",
    "correction_reason": "user_feedback"
  }
}
```

### Future Processing
When "XYZ Consulting" appears again:
- ✓ Automatically classified to Professional Fees
- ✓ Confidence: 99%
- ✓ No user review needed

## Output Files

### 1. **autobooks_ledger.xlsx**
Live Excel file with columns:
- Date, Transaction ID, Invoice ID, Vendor
- Description, Debit Account, Debit Amount
- Credit Account, Credit Amount, TDS Account, TDS Amount
- GST Amount, Confidence, Rule Applied, Status

Color coding:
-  Green: Approved transactions
-  Red: Flagged for review

### 2. **learned_rules.json**
Vendor-specific classification rules:
```json
{
  "Premium Office Furnishings": {
    "debit_account": "office_supplies",
    "debit_code": "5003",
    "credit_account": "supplier",
    "credit_code": "4003",
    "learned_at": "2024-12-28T10:30:00",
    "correction_reason": "user_feedback"
  }
}
```

### 3. **processed_cache.json**
Deduplication cache to track processed files:
```json
{
  "sample_invoice_001_1735123456": "abc123def456..."
}
```

## Performance Characteristics

- **Document Processing**: ~2-5 seconds per invoice (depends on PDF size)
- **ChromaDB Query**: <500ms for similarity search
- **Embedding Generation**: ~100ms for typical invoice text
- **Excel Output**: <100ms append

## Future Enhancements

- Integration with actual Pathway framework for streaming
- Multi-model confidence (LLM-based fallback)
- Advanced TDS rule configuration
- Bank statement matching
- Tally XML export
- Real-time UI dashboard
- Batch processing optimization

## Limitations & Scope

**In Scope (Hackathon):**
- Single-file processing
- Text-based accounting documents
- Rule learning per vendor
- Excel output generation

**Out of Scope:**
- Direct Tally integration
- Multi-company support
- Advanced reconciliation
- Real-time streaming (uses polling instead)
- API endpoint deployment

## Testing

Sample invoices are provided in `inbox/`:
1. **sample_invoice_001.txt** - Office furniture purchase (GST only)
2. **sample_invoice_002.txt** - Rent payment (with TDS)
3. **sample_invoice_003.txt** - Professional consulting (with TDS)

Run demo:
```bash
python main.py
```

## Troubleshooting

### No Tesseract Found
```bash
# Install Tesseract
sudo apt-get install tesseract-ocr

# Or set path in config
export PATH=$PATH:/usr/bin/tesseract
```

### ChromaDB Issues
```bash
# Delete and reinitialize
rm -rf chroma_db/
python main.py
```

### Low Confidence on All Documents
- Check field extraction patterns in `field_extractor.py`
- Add more sample documents to train embeddings
- Lower `CONFIDENCE_THRESHOLD` if needed

## Contact & Support

Built for: IITM SYNAPTIX Hackathon
Demo Purpose: Intelligent Accounting Automation

---

**AutoBooks** - Making Accounting Smarter, One Invoice at a Time 
