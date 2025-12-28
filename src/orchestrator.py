from pathlib import Path
from typing import Dict, Optional, List
import json
from datetime import datetime

from config import *
from logger import get_logger
from document_monitor import DocumentMonitor
from document_decoder import DocumentDecoder
from text_chunker import TextChunker
from embedding_manager import EmbeddingManager
from llm_manager import LLMManager
from field_extractor import FieldExtractor
from ledger_classifier import LedgerClassifier
from self_rag_agent import SelfRAGAgent
from excel_ledger import ExcelLedger
from models import TransactionEntry

logger = get_logger(__name__)

class AutoBooksOrchestrator:
    """Main orchestrator for the AutoBooks processing pipeline."""
    
    def __init__(self):
        """Initialize all components."""
        logger.info("Initializing AutoBooks Orchestrator...")
        
        # Initialize components
        self.monitor = DocumentMonitor(INBOX_PATH, poll_interval=2)
        self.text_chunker = TextChunker(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        self.embedding_manager = EmbeddingManager(model_name=EMBEDDING_MODEL, db_path=CHROMA_DB_PATH)
        self.llm_manager = LLMManager(model_name=LLM_MODEL)
        self.self_rag_agent = SelfRAGAgent(
            rules_path=RULES_PATH,
            embedding_manager=self.embedding_manager,
            llm_manager=self.llm_manager,
            confidence_threshold=CONFIDENCE_THRESHOLD
        )
        self.excel_ledger = ExcelLedger(EXCEL_OUTPUT_PATH)
        
        # Track processed documents
        self.processed_documents: Dict[str, str] = self._load_processed_cache()
        
        logger.info("AutoBooks Orchestrator initialized successfully")
    
    def _load_processed_cache(self) -> Dict[str, str]:
        """Load cache of processed documents."""
        cache_file = CONFIG_PATH / "processed_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load cache: {str(e)}")
        return {}
    
    def _save_processed_cache(self):
        """Persist processed documents cache."""
        try:
            cache_file = CONFIG_PATH / "processed_cache.json"
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump(self.processed_documents, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save cache: {str(e)}")
    
    def process_document(self, file_path: Path) -> Optional[Dict]:
        """Process a single document through the full pipeline."""
        
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing: {file_path.name}")
            logger.info(f"{'='*60}")
            
            # Step 1: Decode document
            logger.info("Step 1: Decoding document...")
            text, doc_metadata = DocumentDecoder.decode_document(file_path)
            document_id = doc_metadata.document_id
            
            # Check if already processed (deduplication)
            file_hash = DocumentDecoder.get_file_hash(file_path)
            if document_id in self.processed_documents:
                if self.processed_documents[document_id] == file_hash:
                    logger.info(f"Document already processed (hash match): {document_id}")
                    return None
                else:
                    logger.info(f"Document modified: {document_id} - reprocessing")
                    # Delete old chunks from ChromaDB
                    self.embedding_manager.delete_chunks_by_document(document_id)
            
            # Step 2: Chunk text
            logger.info("Step 2: Chunking text...")
            chunks = self.text_chunker.chunk_text(
                text=text,
                document_id=document_id,
                source_path=str(file_path),
                metadata={"document_type": doc_metadata.document_type}
            )
            
            # Step 3: Embed and upsert to ChromaDB
            logger.info("Step 3: Embedding and upserting to ChromaDB...")
            self.embedding_manager.upsert_chunks(chunks)
            
            # Step 4: SELF-RAG agent processing
            logger.info("Step 4: Running SELF-RAG agent...")
            agent_result = self.self_rag_agent.process_document(
                text=text,
                document_id=document_id,
                metadata={"document_type": doc_metadata.document_type}
            )
            
            # Step 5: Write to Excel
            logger.info("Step 5: Writing to Excel ledger...")
            extraction = agent_result["extraction"]
            transaction = agent_result["transaction"]
            
            self.excel_ledger.append_transaction(
                transaction=transaction,
                extraction_data={
                    "invoice_id": extraction.fields.invoice_id,
                    "vendor_name": extraction.fields.vendor_name,
                }
            )
            
            # Mark as processed
            self.processed_documents[document_id] = file_hash
            self._save_processed_cache()
            
            # Log results
            logger.info(f"\n✓ Document processed successfully")
            logger.info(f"  Transaction ID: {transaction.transaction_id}")
            logger.info(f"  Invoice ID: {extraction.fields.invoice_id}")
            logger.info(f"  Vendor: {extraction.fields.vendor_name}")
            logger.info(f"  Amount: {extraction.fields.amount}")
            logger.info(f"  Confidence: {transaction.confidence_score:.2%}")
            logger.info(f"  Status: {transaction.status}")
            
            if agent_result["status"] == "needs_review":
                logger.warning(f"  ⚠ Flagged for review - awaiting user correction")
            
            return agent_result
        
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}", exc_info=True)
            return None
    
    def process_inbox(self) -> List[Dict]:
        """Process all new/modified files in inbox."""
        
        logger.info(f"\nScanning inbox: {INBOX_PATH}")
        changes = self.monitor.scan_inbox()
        
        results = []
        
        # Process added and modified files
        files_to_process = changes["added"] + changes["modified"]
        
        if not files_to_process:
            logger.info("No new or modified files found")
            return results
        
        for filename in files_to_process:
            file_path = INBOX_PATH / filename
            result = self.process_document(file_path)
            if result:
                results.append(result)
        
        return results
    
    def handle_user_correction(self, document_id: str, correction: Dict):
        """Handle user correction and learn from it."""
        
        logger.info(f"Processing user correction for: {document_id}")
        
        vendor_name = correction.get("vendor_name")
        if vendor_name:
            self.self_rag_agent.learn_from_correction(vendor_name, correction)
            logger.info(f"Learned rule from user for vendor: {vendor_name}")
        
        # Update Excel with correction
        transaction_id = correction.get("transaction_id")
        if transaction_id:
            self.excel_ledger.update_transaction(
                transaction_id,
                {
                    "status": "approved",
                    "rule_applied": f"user_correction_{vendor_name}",
                    "confidence": correction.get("confidence", 0.99)
                }
            )
    
    def get_ledger_summary(self) -> Dict:
        """Get summary of the ledger."""
        return self.excel_ledger.get_summary()
    
    def run_demo(self):
        """Run a demo processing the current inbox contents."""
        logger.info("\n" + "="*70)
        logger.info("AUTOBOOKS - Intelligent Accounting Document Processing")
        logger.info("="*70)
        
        # Process inbox
        results = self.process_inbox()
        
        logger.info(f"\n{'='*70}")
        logger.info(f"Processing Complete!")
        logger.info(f"Total documents processed: {len(results)}")
        
        # Show summary
        summary = self.get_ledger_summary()
        if summary:
            logger.info(f"\nLedger Summary:")
            logger.info(f"  Total Transactions: {summary.get('total_transactions', 0)}")
            logger.info(f"  Total Debit: ₹{summary.get('total_debit', 0):,.2f}")
            logger.info(f"  Total Credit: ₹{summary.get('total_credit', 0):,.2f}")
            logger.info(f"  Total TDS: ₹{summary.get('total_tds', 0):,.2f}")
            logger.info(f"  Average Confidence: {summary.get('avg_confidence', 0):.2%}")
            if summary.get('status_breakdown'):
                logger.info(f"  Status Breakdown: {summary['status_breakdown']}")
        
        logger.info(f"\nOutput files:")
        logger.info(f"  Excel Ledger: {EXCEL_OUTPUT_PATH}")
        logger.info(f"  Learned Rules: {RULES_PATH}")
        logger.info(f"{'='*70}\n")
        
        return results
