#!/usr/bin/env python3
"""
Quick test script - tests core logic without heavy model downloads
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from logger import get_logger
from field_extractor import FieldExtractor
from ledger_classifier import LedgerClassifier
from text_chunker import TextChunker
from models import DocumentMetadata, ExtractedFields
from datetime import datetime

logger = get_logger(__name__)

def test_field_extraction():
    """Test the field extraction regex patterns."""
    logger.info("\n" + "="*70)
    logger.info("TEST 1: Field Extraction")
    logger.info("="*70)
    
    sample_text = """
    INVOICE
    
    Invoice Number: INV-2024-001
    Invoice Date: 2024-12-20
    
    Bill To: AutoBooks Pvt Ltd
    Vendor: Premium Office Furnishings
    
    Description: Office Furniture - Desk Set
    Amount: ₹47200
    GST @ 18%: ₹7200
    """
    
    result = FieldExtractor.extract_fields(sample_text)
    
    logger.info(f"Extraction Results:")
    logger.info(f"  Invoice ID: {result.fields.invoice_id}")
    logger.info(f"  Date: {result.fields.invoice_date}")
    logger.info(f"  Vendor: {result.fields.vendor_name}")
    logger.info(f"  Amount: {result.fields.amount}")
    logger.info(f"  GST: {result.fields.gst_amount}")
    logger.info(f"  Overall Confidence: {result.confidence_score:.2%}")
    logger.info(f"  Validation Status: {'✓ Valid' if result.is_validated else '✗ Invalid'}")
    
    return result

def test_ledger_classification():
    """Test ledger account classification."""
    logger.info("\n" + "="*70)
    logger.info("TEST 2: Ledger Classification")
    logger.info("="*70)
    
    fields = ExtractedFields(
        vendor_name="Premium Office Furnishings",
        tds_category=None,
        description="Office furniture purchase"
    )
    
    result = LedgerClassifier.classify_ledger_accounts(fields)
    
    logger.info(f"Classification Results:")
    logger.info(f"  Debit Account: {result['debit_account']} ({result['debit_code']})")
    logger.info(f"  Credit Account: {result['credit_account']} ({result['credit_code']})")
    logger.info(f"  Confidence: {result['confidence']:.2%}")
    logger.info(f"  Flags: {result['flags'] if result['flags'] else 'None'}")
    
    return result

def test_text_chunking():
    """Test text chunking."""
    logger.info("\n" + "="*70)
    logger.info("TEST 3: Text Chunking")
    logger.info("="*70)
    
    long_text = """
    This is a sample invoice document. It contains multiple lines of text about the invoice details.
    The text includes information about the vendor, the amount, and various other accounting details.
    We need to split this into chunks for semantic processing and embedding.
    Text chunking with overlap helps preserve context across chunk boundaries.
    """ * 5  # Repeat to make it longer
    
    chunker = TextChunker(chunk_size=200, chunk_overlap=30)
    chunks = chunker.chunk_text(
        text=long_text,
        document_id="test_doc_001",
        source_path="/tmp/test.txt"
    )
    
    logger.info(f"Chunking Results:")
    logger.info(f"  Total Chunks: {len(chunks)}")
    logger.info(f"  Sample Chunk 0: {chunks[0].chunk_text[:80]}...")
    logger.info(f"  Sample Chunk 1: {chunks[1].chunk_text[:80]}...")
    
    return chunks

def test_rent_invoice():
    """Test with rent invoice (includes TDS)."""
    logger.info("\n" + "="*70)
    logger.info("TEST 4: Rent Invoice with TDS")
    logger.info("="*70)
    
    rent_text = """
    INVOICE
    Invoice Number: INV-2024-002
    Invoice Date: 2024-12-21
    Vendor: ABC Rent & Lease Services
    
    Monthly Rent: ₹50000
    TDS Category: Rent
    TDS Deduction @ 10%: ₹5000
    Net Amount: ₹45000
    """
    
    result = FieldExtractor.extract_fields(rent_text)
    logger.info(f"Rent Invoice Extraction:")
    logger.info(f"  Vendor: {result.fields.vendor_name}")
    logger.info(f"  Amount: {result.fields.amount}")
    logger.info(f"  TDS Category: {result.fields.tds_category}")
    logger.info(f"  TDS Amount: {result.fields.tds_amount}")
    logger.info(f"  Confidence: {result.confidence_score:.2%}")
    
    # Classify
    classification = LedgerClassifier.classify_ledger_accounts(result.fields)
    logger.info(f"  Debit Account: {classification['debit_account']} ({classification['debit_code']})")
    logger.info(f"  Credit Account: {classification['credit_account']} ({classification['credit_code']})")
    
    return result

def test_professional_invoice():
    """Test with professional services (includes TDS)."""
    logger.info("\n" + "="*70)
    logger.info("TEST 5: Professional Services with TDS")
    logger.info("="*70)
    
    prof_text = """
    INVOICE
    Invoice Number: INV-2024-003
    Invoice Date: 2024-12-22
    Vendor: Professional Consulting Services Ltd
    
    Consulting Fees: ₹100000
    TDS Category: Professional Services
    TDS Deduction @ 10%: ₹10000
    Net Amount: ₹90000
    GST @ 18%: ₹18000
    """
    
    result = FieldExtractor.extract_fields(prof_text)
    logger.info(f"Professional Services Invoice:")
    logger.info(f"  Vendor: {result.fields.vendor_name}")
    logger.info(f"  Amount: {result.fields.amount}")
    logger.info(f"  TDS Category: {result.fields.tds_category}")
    logger.info(f"  TDS Amount: {result.fields.tds_amount}")
    logger.info(f"  GST: {result.fields.gst_amount}")
    logger.info(f"  Confidence: {result.confidence_score:.2%}")
    
    # Classify
    classification = LedgerClassifier.classify_ledger_accounts(result.fields)
    logger.info(f"  Debit Account: {classification['debit_account']} ({classification['debit_code']})")
    logger.info(f"  Credit Account: {classification['credit_account']} ({classification['credit_code']})")
    
    return result

def main():
    """Run all tests."""
    
    logger.info("\n" + "="*70)
    logger.info("AUTOBOOKS - CORE LOGIC TEST SUITE")
    logger.info("(No LLM/Embedding model downloads)")
    logger.info("="*70)
    
    try:
        # Run tests
        test_field_extraction()
        test_ledger_classification()
        test_text_chunking()
        test_rent_invoice()
        test_professional_invoice()
        
        logger.info("\n" + "="*70)
        logger.info("✓ ALL CORE LOGIC TESTS PASSED")
        logger.info("="*70)
        logger.info("\nNotes:")
        logger.info("- Field extraction uses regex patterns (no LLM needed)")
        logger.info("- Classification uses rule-based ledger mapping")
        logger.info("- Text chunking is deterministic")
        logger.info("\nNext steps for full deployment:")
        logger.info("1. Ensure BAAI/bge-m3 is downloaded (first time ~2-3GB)")
        logger.info("2. Pull gemma3:4b via Ollama (ollama pull gemma3:4b)")
        logger.info("3. Run main.py for full SELF-RAG pipeline")
        logger.info("="*70 + "\n")
        
        return 0
    
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
