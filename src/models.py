from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class DocumentMetadata(BaseModel):
    """Metadata for tracked documents."""
    document_id: str
    source_path: str
    document_type: str  # "pdf" or "excel"
    created_at: datetime
    modified_at: datetime
    hash_value: Optional[str] = None  # For deduplication

class ExtractedFields(BaseModel):
    """Extracted fields from accounting documents."""
    invoice_id: Optional[str] = None
    invoice_date: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_id: Optional[str] = None
    amount: Optional[float] = None
    gst_percent: Optional[float] = None
    gst_amount: Optional[float] = None
    tds_category: Optional[str] = None  # rent, salary, professional, contract
    tds_percent: Optional[float] = None
    tds_amount: Optional[float] = None
    net_amount: Optional[float] = None  # amount - tds
    account_code: Optional[str] = None
    description: Optional[str] = None
    raw_text: Optional[str] = None

class ExtractionResult(BaseModel):
    """Result of field extraction with confidence."""
    fields: ExtractedFields
    confidence_score: float  # 0-1
    confidence_breakdown: Dict[str, float] = Field(default_factory=dict)  # per-field confidence
    is_validated: bool = False
    validation_errors: List[str] = Field(default_factory=list)

class TransactionEntry(BaseModel):
    """Structured accounting transaction."""
    transaction_id: str
    document_id: str
    date: str
    debit_account: str  # Expense account
    debit_amount: float
    credit_account: str  # Party/Vendor account
    credit_amount: float
    tds_account: Optional[str] = None
    tds_amount: Optional[float] = None
    description: str
    gst_amount: Optional[float] = None
    confidence_score: float
    rule_applied: Optional[str] = None  # Which learned rule was applied
    user_correction: Optional[str] = None
    status: str = "pending"  # pending, approved, flagged

class ChunkMetadata(BaseModel):
    """Metadata for text chunks in ChromaDB."""
    document_id: str
    chunk_index: int
    source_path: str
    chunk_text: str
    metadata: Dict = Field(default_factory=dict)
