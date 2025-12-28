from typing import List, Dict, Optional
from models import ChunkMetadata
from logger import get_logger

logger = get_logger(__name__)

class TextChunker:
    """Splits documents into semantic chunks with overlap."""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
    
    def chunk_text(
        self,
        text: str,
        document_id: str,
        source_path: str,
        metadata: Optional[Dict] = None
    ) -> List[ChunkMetadata]:
        """Split text into chunks with overlap."""
        
        # Clean text
        text = text.strip()
        if not text:
            logger.warning(f"Empty text for document {document_id}")
            return []
        
        chunks_metadata = []
        chunk_index = 0
        position = 0
        
        while position < len(text):
            # Calculate chunk end position
            chunk_end = min(position + self.chunk_size, len(text))
            
            # Try to break at word boundary if not at end
            if chunk_end < len(text):
                # Look back for a space or newline
                last_space = text.rfind(' ', position, chunk_end)
                last_newline = text.rfind('\n', position, chunk_end)
                last_break = max(last_space, last_newline)
                
                if last_break > position:
                    chunk_end = last_break + 1
            
            chunk_text = text[position:chunk_end].strip()
            
            if chunk_text:  # Only add non-empty chunks
                chunk_meta = ChunkMetadata(
                    document_id=document_id,
                    chunk_index=chunk_index,
                    source_path=source_path,
                    chunk_text=chunk_text,
                    metadata=metadata or {}
                )
                chunks_metadata.append(chunk_meta)
                chunk_index += 1
            
            # Move position with overlap
            position = chunk_end - self.chunk_overlap
        
        logger.info(f"Split document {document_id} into {len(chunks_metadata)} chunks")
        return chunks_metadata
