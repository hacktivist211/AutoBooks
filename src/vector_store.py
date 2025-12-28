from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from datetime import datetime
from src.logger import get_logger

logger = get_logger(__name__)

class VectorStore:
    """ChromaDB wrapper for storing and retrieving vendor patterns."""

    def __init__(self, persist_dir: str):
        """
        Initialize ChromaDB client and sentence transformer.

        Args:
            persist_dir: Directory to persist ChromaDB data
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initializing ChromaDB at {self.persist_dir}")

        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="vendor_patterns",
            metadata={"hnsw:space": "cosine"}
        )

        # Initialize sentence transformer
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("VectorStore initialized successfully")

    def add_pattern(self, vendor: str, keywords: List[str], category: str, amount: float):
        """
        Store a learned rule pattern in the vector store.

        Args:
            vendor: Vendor name
            keywords: List of keywords associated with this vendor
            category: Expense category
            amount: Typical amount for this vendor
        """
        # Create embedding text
        keywords_joined = " ".join(keywords)
        embedding_text = f"{vendor} {keywords_joined}"

        # Generate embedding
        embedding = self.model.encode([embedding_text])[0].tolist()

        # Create metadata
        amount_range = f"{amount * 0.8:.0f}-{amount * 1.2:.0f}"  # ±20% range
        learned_at = datetime.now().isoformat()

        # Create unique ID
        pattern_id = f"{vendor}_{category}_{int(datetime.now().timestamp())}"

        # Add to collection
        self.collection.add(
            ids=[pattern_id],
            embeddings=[embedding],
            metadatas=[{
                "vendor": vendor,
                "category": category,
                "amount_range": amount_range,
                "learned_at": learned_at,
                "keywords": ",".join(keywords)
            }],
            documents=[embedding_text]
        )

        logger.info(f"Added pattern for vendor '{vendor}' in category '{category}'")

    def query_similar(self, vendor: str, text: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Find similar vendor patterns.

        Args:
            vendor: Vendor name to search for
            text: Context text to embed and search
            n_results: Number of results to return

        Returns:
            List of dicts with vendor, category, similarity_score
        """
        # Create query embedding
        query_text = f"{vendor} {text}"
        query_embedding = self.model.encode([query_text])[0].tolist()

        # Query collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["metadatas", "distances"]
        )

        # Format results
        formatted_results = []
        if results["metadatas"] and results["distances"]:
            for metadata, distance in zip(results["metadatas"][0], results["distances"][0]):
                # Convert cosine distance to similarity score (higher is better)
                similarity_score = 1 - distance

                formatted_results.append({
                    "vendor": metadata.get("vendor", ""),
                    "category": metadata.get("category", ""),
                    "similarity_score": round(similarity_score, 3),
                    "amount_range": metadata.get("amount_range", ""),
                    "learned_at": metadata.get("learned_at", ""),
                    "keywords": metadata.get("keywords", "").split(",") if metadata.get("keywords") else []
                })

        logger.debug(f"Found {len(formatted_results)} similar patterns for vendor '{vendor}'")
        return formatted_results

    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the vector store collection."""
        count = self.collection.count()
        return {
            "total_patterns": count,
            "collection_name": self.collection.name
        }