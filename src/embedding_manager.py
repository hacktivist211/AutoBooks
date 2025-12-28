from pathlib import Path
from typing import List, Optional, Dict, Any
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from models import ChunkMetadata
from logger import get_logger

logger = get_logger(__name__)

class EmbeddingManager:
    """Manages embeddings and ChromaDB operations."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", db_path: Path = None):
        """Initialize embedding model and ChromaDB."""
        self.model_name = model_name
        self.db_path = db_path or Path("./chroma_db")
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="accounting_documents",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("ChromaDB collection initialized")
    
    def embed_chunks(self, chunks: List[ChunkMetadata]) -> List[List[float]]:
        """Generate embeddings for chunks."""
        if not chunks:
            return []
        
        texts = [chunk.chunk_text for chunk in chunks]
        logger.info(f"Embedding {len(texts)} chunks")
        embeddings = self.model.encode(texts)
        return embeddings.tolist()
    
    def upsert_chunks(self, chunks: List[ChunkMetadata]) -> bool:
        """Add or update chunks in ChromaDB."""
        try:
            if not chunks:
                logger.warning("No chunks to upsert")
                return False
            
            embeddings = self.embed_chunks(chunks)
            
            # Prepare data for ChromaDB
            ids = [f"{chunk.document_id}_chunk_{chunk.chunk_index}" for chunk in chunks]
            metadatas = [
                {
                    "document_id": chunk.document_id,
                    "chunk_index": str(chunk.chunk_index),
                    "source_path": chunk.source_path,
                    **chunk.metadata
                }
                for chunk in chunks
            ]
            documents = [chunk.chunk_text for chunk in chunks]
            
            # Upsert to collection
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
            
            logger.info(f"Successfully upserted {len(chunks)} chunks")
            return True
        except Exception as e:
            logger.error(f"Error upserting chunks: {str(e)}")
            raise
    
    def query_similar_chunks(
        self,
        query_text: str,
        n_results: int = 5,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query ChromaDB for similar chunks."""
        try:
            logger.debug(f"Querying similar chunks for: {query_text[:100]}...")
            
            # Generate embedding for query
            query_embedding = self.model.encode([query_text])[0].tolist()
            
            # Query collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter
            )
            
            # Format results
            formatted_results = {
                "ids": results["ids"][0] if results["ids"] else [],
                "distances": results["distances"][0] if results["distances"] else [],
                "documents": results["documents"][0] if results["documents"] else [],
                "metadatas": results["metadatas"][0] if results["metadatas"] else []
            }
            
            logger.debug(f"Found {len(formatted_results['ids'])} similar chunks")
            return formatted_results
        except Exception as e:
            logger.error(f"Error querying chunks: {str(e)}")
            raise
    
    def delete_chunks_by_document(self, document_id: str) -> bool:
        """Remove all chunks for a document."""
        try:
            results = self.collection.get(
                where={"document_id": {"$eq": document_id}}
            )
            
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
            
            return True
        except Exception as e:
            logger.error(f"Error deleting chunks: {str(e)}")
            raise
