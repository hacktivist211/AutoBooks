# AutoBooks - Intelligent Accounting Document Processing System

##  Overview

AutoBooks is an intelligent, agentic accounting system that automates the extraction and classification of financial documents (invoices, vouchers, bills) into appropriate ledger accounts. It demonstrates **Self-RAG (Self-Reflective Retrieval-Augmented Generation)** in production, combining OCR, NLP, vector embeddings, and LLM reasoning to process accounting documents with high confidence while learning from user feedback.

### Problem Statement

Accounting teams manually:
- Extract data from scanned invoices/vouchers
- Classify transactions to correct ledger accounts
- Handle Tax Deduction at Source (TDS) calculations
- Update accounting ledgers in Tally ERP

###  Key Features

| Feature | Description |
|---------|-------------|
| **Real-time Monitoring** | Watches inbox folder for new/modified PDF, Excel, and text files |
| **Intelligent Text Extraction** | OCR via Tesseract for PDFs; structured parsing for Excel |
| **Smart Field Extraction** | Regex-based extraction of vendor name, amount, date, GST, TDS |
| **Confidence Scoring** | Rule-based scoring (0.0-1.0) based on field extraction success |
| **SELF-RAG Decision Engine** | Confidence thresholds trigger different actions: auto-post, retrieve context, or ask user |
| **Vector Search** | Sentence Transformers + ChromaDB for semantic similarity matching |
| **TDS Handling** | Automatic TDS deduction (rent: 10%, salary: 5%, professional: 10%, contract: 5%) |
| **Rule Learning** | Learn from user corrections; apply rules persistently to future documents |
| **Excel Output** | Tally-compatible ledger in XLSX format with formatting and validation |
| **Audit Trail** | File archiving, transaction logging, and status tracking |

---

## Architecture

```
INPUT STREAM
     │
     ▼
┌─────────────────────────────────────────────────┐
│     Document Monitor (Polling)                  │
│  Watches: ./inbox/*.{pdf,xlsx,txt}              │
│  Detects: added, modified, deleted files        │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│     OCR Engine (Tesseract)                      │
│  PDFs → Images → Text via pytesseract           │
│  Excel → Cell extraction                        │
│  TXT → Direct read                              │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│     Field Extractor (Regex)                     │
│  Extracts: vendor, amount, date, gst, tds       │
│  Validates: types, ranges, formats              │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│     Confidence Scorer (Rule-based)              │
│  Scores extraction quality (0.0-1.0)            │
│  Per-field confidence breakdown                 │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│     SELF-RAG Decision Engine                    │
│                                                 │
│  ≥ 0.75? ──► AUTO-POST (create transaction)     │
│                                                 │
│  0.50-0.75? ──► Query ChromaDB for similar      │
│                 patterns → match? → post        │
│                 no match? → ask user            │
│                                                 │
│  < 0.50? ──► Ask user directly                  │
│                                                 │
│  User feedback? ──► Learn rule + store          │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│     Text Chunker (Semantic)                     │
│  Chunks: 500 chars with 50-char overlap         │
│  Purpose: Preserve context for embeddings       │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│     Embedding Manager (Sentence Transformers)   │ 
│  Model: BAAI/bge-m3 or all-MiniLM-L6-v2         |
│  Storage: ChromaDB (persistent)                 │
│  Use: Semantic similarity search                │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│     Rules Manager + Vector Store                │
│  Persists: rules.json (learned patterns)        │
│  Persists: chroma.sqlite3 (embeddings)          │
│  Applies: Rules to future documents             │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│     Excel Ledger Writer                         │
│  Output: autobooks_ledger.xlsx                  │
│  Columns: Date, Vendor, Debit Acct, Debit Amt,  │
│           Credit Acct, Credit Amt, TDS Acct,    │
│           TDS Amt, Confidence, Status           │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│     Output                                      │
│  Tally-ready Excel ledger + archive folder      │
│  (for downstream ERP integration)               │
└─────────────────────────────────────────────────┘
```

---

##  Project Structure

```
AutoBooks/
├── main.py                          # Entry point - runs the orchestrator
├── requirements.txt                 # Python dependencies
├── .env                            # Configuration (paths, models, thresholds)
├── setup_autobooks.bat             # Windows setup script
│
├── src/
│   ├── __init__.py
│   ├── agent.py                    # SelfRAGAgent - main processing orchestrator
│   ├── self_rag_agent.py           # Alternative SELF-RAG implementation
│   ├── models.py                   # Pydantic models (InvoiceFields, Transaction, Rule, etc.)
│   ├── config.py                   # Settings management (Pydantic BaseSettings)
│   ├── logger.py                   # Logging configuration
│   │
│   ├── document_monitor.py         # Monitors inbox for file changes
│   ├── ocr_engine.py               # Tesseract OCR for PDF extraction
│   ├── document_decoder.py         # Multi-format document parsing
│   │
│   ├── field_extractor.py          # Regex-based field extraction
│   ├── invoice_extractor.py        # Invoice-specific extraction
│   ├── confidence_scorer.py        # Confidence calculation logic
│   │
│   ├── text_chunker.py             # Semantic text chunking
│   ├── embedding_manager.py        # ChromaDB + Sentence Transformers
│   ├── vector_store.py             # Vector store wrapper for patterns
│   │
│   ├── ledger_classifier.py        # Classify transactions to ledger accounts
│   ├── rules.py                    # Rule learning and persistence
│   ├── llm_manager.py              # LLM interaction (Ollama)
│   │
│   ├── excel_ledger.py             # Excel writing (legacy)
│   ├── excel_writer.py             # Excel output generation (Openpyxl)
│   └── orchestrator.py             # Pipeline orchestration
│
├── config/
│   └── rules.json                  # Learned rules (persisted)
│
├── chroma_db/
│   └── chroma.sqlite3              # Vector embeddings database
│
├── inbox/
│   ├── sample_invoice_001.txt      # Example invoice files
│   ├── sample_invoice_002.txt
│   └── sample_invoice_003.txt
│
├── output/
│   └── autobooks_ledger.xlsx       # Generated ledger (created on first run)
│
├── archive/
│   └── *_processed.*               # Processed files moved here
│
├── context/
│   ├── prompt_instructions.md      # AI assistant instructions
│   └── copilot-instructions.md     # GitHub Copilot context
│
├── test_core_logic.py              # Unit tests for field extraction
├── test_rules.py                   # Unit tests for rule learning
│
├── LICENSE
└── README.md
```

---

##  Quick Start

### Prerequisites
- Python 3.9+
- Tesseract OCR (`apt-get install tesseract-ocr` on Linux, `brew install tesseract` on Mac)
- Ollama (optional, for local LLM; or use API-based alternatives)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd AutoBooks
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment** (update `.env` as needed)
   ```bash
   cp .env.example .env  # If provided
   # Edit .env with your paths and settings
   ```

5. **Run the system**
   ```bash
   python main.py
   ```

The system will:
- Monitor `./inbox` folder
- Process new/modified documents
- Generate `./output/autobooks_ledger.xlsx`
- Archive processed files to `./archive`

---

##  Configuration

### Key Settings (`.env` or `config.py`)

```env
# Paths
INBOX_PATH=./inbox                          # Input documents folder
ARCHIVE_PATH=./archive                      # Processed files backup
OUTPUT_PATH=./output                        # Output ledger location
CHROMA_DB_PATH=./chroma_db                  # Vector store location
CONFIG_PATH=./config                        # Rules configuration

# Models
EMBEDDING_MODEL=BAAI/bge-m3                 # Embedding model
LLM_MODEL=gemma3:4b                         # Local LLM (via Ollama)

# Confidence Thresholds
CONFIDENCE_THRESHOLD=0.70                   # Overall threshold
CONFIDENCE_HIGH=0.75                        # Auto-post if ≥ 0.75
CONFIDENCE_MEDIUM=0.50                      # Query ChromaDB if 0.50-0.75

# Text Processing
CHUNK_SIZE=500                              # Characters per chunk
CHUNK_OVERLAP=50                            # Overlap between chunks

# TDS Configuration
TDS_RATES={"rent": 10, "salary": 5, "professional": 10, "contract": 5}
TDS_APPLICABLE_CATEGORIES=["rent", "salary", "professional", "contract"]

# Logging
LOG_LEVEL=DEBUG                             # DEBUG, INFO, WARNING, ERROR

# File Formats
SUPPORTED_FORMATS=[".pdf", ".xlsx", ".txt"] # Supported input formats
```

---

## 🔄 Processing Pipeline

### Step-by-Step Flow

1. **Document Monitor** scans inbox every 2 seconds
   - Detects new/modified files using hash-based deduplication
   - Filters by supported formats (.pdf, .xlsx, .txt)

2. **OCR/Text Extraction**
   - PDFs: Convert to images → Tesseract OCR
   - Excel: Direct cell reading
   - Text: Read as-is

3. **Field Extraction**
   - Regex patterns extract: vendor, amount, date, GST, TDS
   - Returns per-field confidence scores

4. **Confidence Scoring**
   - Rule-based calculation (0.0 to 1.0)
   - Considers: extraction success, field validation, pattern matching

5. **SELF-RAG Decision**
   ```
   If confidence ≥ 0.75 → AUTO-POST
     Create transaction, write to Excel, archive file
   
   Else if 0.50 ≤ confidence < 0.75 → QUERY VECTOR STORE
     Retrieve similar vendor patterns from ChromaDB
     If match found (similarity > 0.8) → POST
     Else → ASK USER
   
   Else if confidence < 0.50 → ASK USER DIRECTLY
   
   If user provides correction → LEARN RULE
     Save to rules.json + update ChromaDB
     Apply rule to future documents
   ```

6. **Excel Output**
   - Append transaction row to `autobooks_ledger.xlsx`
   - Apply formatting, validations, hyperlinks
   - Tally-compatible format

7. **Archiving**
   - Move processed file to `./archive` with timestamp
   - Prevent re-processing

---

## 📊 SELF-RAG Implementation Details

### What is SELF-RAG?

**Self-Reflective Retrieval-Augmented Generation** = The system reflects on its own confidence and takes different actions:

- **No external feedback needed**: The system learns from user corrections
- **Context-aware**: Uses embeddings to find similar past decisions
- **Adaptive**: Rules persist and improve over time

### Confidence Scoring Logic

```python
# Field extraction confidence
- Invoice ID found? +0.15
- Vendor name extracted? +0.20
- Amount extracted? +0.25
- Date parsed? +0.15
- TDS category identified? +0.10
- Field validations passed? +0.15

Total: Max 1.0
```

### Rule Matching

When confidence is medium (0.50-0.75):
1. Generate embedding of current vendor + keywords
2. Query ChromaDB for nearest neighbors
3. If similarity score > 0.8 → Use learned category
4. Else → Ask user for clarification

### Learning Mechanism

User provides correction → System saves:
```json
{
  "vendor": "M/s ABC Consulting",
  "keywords": ["consulting", "professional", "services"],
  "debit_account": "Professional Services",
  "credit_account": "M/s ABC Consulting (Payable)",
  "tds_applicable": true,
  "learned_at": "2024-12-20T10:30:00",
  "applied_count": 0
}
```

This rule is applied to all future similar invoices.

---

##  Testing

### Run Unit Tests

```bash
# Test field extraction and regex patterns
python test_core_logic.py

# Test rule learning and persistence
python test_rules.py
```

### Sample Input

Three sample invoices are provided in `./inbox`:
- `sample_invoice_001.txt` - Office furniture (GST 18%)
- `sample_invoice_002.txt` - Professional services
- `sample_invoice_003.txt` - Rent payment with TDS

Run main.py to process these samples.

---

##  Dependencies

| Package | Purpose |
|---------|---------|
| **pathway** | Real-time data streaming (alternative to polling) |
| **chromadb** | Vector database for embeddings |
| **sentence-transformers** | Generate embeddings |
| **pandas** | Data manipulation |
| **openpyxl** | Excel file writing |
| **pydantic** | Data validation (models) |
| **python-dotenv** | Environment configuration |
| **pillow** | Image processing |
| **pytesseract** | OCR (requires Tesseract binary) |
| **pdf2image** | PDF to image conversion |
| **langchain** | LLM orchestration |
| **ollama** | Local LLM inference |

---

## 🔍 Output Format

### Excel Ledger (autobooks_ledger.xlsx)

| Column | Description | Example |
|--------|-------------|---------|
| Date | Transaction date | 2024-12-20 |
| Vendor | Vendor/supplier name | M/s Premium Office Furnishings |
| Debit Account | Expense ledger account | Office Furniture |
| Debit Amount | Expense amount (₹) | 47200.00 |
| Credit Account | Payable account | M/s Premium Office Furnishings (Payable) |
| Credit Amount | Same as debit | 47200.00 |
| TDS Account | TDS receivable (if applicable) | TDS Receivable - Professional |
| TDS Amount | TDS deducted (₹) | 4720.00 |
| Confidence | Confidence score (%) | 85% |
| Status | Processing result | AUTO_POSTED / USER_CONFIRMED |

---

##  Troubleshooting

### OCR Issues
```
Error: pytesseract.TesseractNotFoundError
Fix: Install Tesseract binary
  Linux: apt-get install tesseract-ocr
  Mac: brew install tesseract
  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
```

### ChromaDB Errors
```
Error: PersistentClient not found
Fix: pip install --upgrade chromadb
```

### LLM Connection
```
Error: Connection refused at localhost:11434
Fix: Start Ollama service (ollama serve) or use API-based LLM
```

### Memory Issues
```
Fix: Reduce CHUNK_SIZE in .env (e.g., 250 instead of 500)
Fix: Use smaller embedding model (all-MiniLM-L6-v2 instead of BAAI/bge-m3)
```

---

##  Contributing

1. Create a feature branch (`git checkout -b feature/your-feature`)
2. Commit changes (`git commit -am 'Add feature'`)
3. Push to branch (`git push origin feature/your-feature`)
4. Create Pull Request

---

##  License

See [LICENSE](LICENSE) file for details.

---

##  Future Enhancements

- [ ] Multi-currency support
- [ ] GST reconciliation and reporting
- [ ] Integration with Tally API
- [ ] Web UI for rule management
- [ ] Mobile app for document capture
- [ ] Real-time analytics dashboard
- [ ] Batch processing mode
- [ ] Document signature verification

---
