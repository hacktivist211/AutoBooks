from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
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

# New Pydantic Models

class InvoiceFields(BaseModel):
    """Extracted fields from invoice documents with validation."""
    vendor: str = Field(..., description="Name of the vendor or supplier")
    amount: float = Field(..., gt=0, description="Total invoice amount")
    date: str = Field(..., description="Invoice date in YYYY-MM-DD format")
    tds_percentage: Optional[float] = Field(None, ge=0, le=100, description="TDS percentage if applicable")
    raw_text: str = Field(..., description="Raw extracted text from document")
    confidence: float = Field(..., ge=0, le=1, description="Extraction confidence score")

    @field_validator('date')
    @classmethod
    def validate_date_format(cls, v):
        """Validate date format."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')

class Transaction(BaseModel):
    """Accounting transaction record."""
    date: str = Field(..., description="Transaction date in YYYY-MM-DD format")
    vendor: str = Field(..., description="Vendor name")
    debit_account: str = Field(..., description="Debit account name")
    debit_amount: float = Field(..., gt=0, description="Amount debited")
    credit_account: str = Field(..., description="Credit account name")
    credit_amount: float = Field(..., gt=0, description="Amount credited")
    tds_account: Optional[str] = Field(None, description="TDS account if applicable")
    tds_amount: Optional[float] = Field(None, ge=0, description="TDS amount deducted")
    confidence: float = Field(..., ge=0, le=1, description="Classification confidence")
    status: str = Field("pending", description="Transaction status")

    @field_validator('date')
    @classmethod
    def validate_date_format(cls, v):
        """Validate date format."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate status values."""
        valid_statuses = ["pending", "approved", "flagged", "rejected", "AUTO_POSTED", "USER_CONFIRMED", "PATTERN_MATCHED"]
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of {valid_statuses}')
        return v

class Rule(BaseModel):
    """Learned classification rule for vendors."""
    vendor: str = Field(..., description="Vendor name this rule applies to")
    keywords: List[str] = Field(default_factory=list, description="Keywords associated with this vendor")
    debit_account: str = Field(..., description="Debit account for this vendor")
    credit_account: str = Field(..., description="Credit account for this vendor")
    tds_applicable: bool = Field(False, description="Whether TDS is applicable")
    learned_at: datetime = Field(default_factory=datetime.now, description="When this rule was learned")
    applied_count: int = Field(0, ge=0, description="Number of times this rule has been applied")

    @field_validator('keywords')
    @classmethod
    def validate_keywords(cls, v):
        """Ensure keywords are non-empty strings."""
        if not all(isinstance(k, str) and k.strip() for k in v):
            raise ValueError('All keywords must be non-empty strings')
        return v
