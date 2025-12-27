"""
faiss_manager.py

FAISS index management for fast similarity search
"""

import logging
import os
from typing import List, Tuple

import faiss
import numpy as np

import config

logger = logging.getLogger(__name__)


class FAISSManager:
    """Manages FAISS index for face embedding similarity search"""
    
    def __init__(self, index_path: str = None):
        """
        Initialize FAISS manager
        
        Args:
            index_path: Path to save/load index (defaults to config)
        """
        self.index_path = index_path or config.FAISS_INDEX_PATH
        self.index = None
        self.dimension = config.EMBEDDING_DIMENSIONS
        
        # Try to load existing index
        if os.path.exists(self.index_path):
            self.load_index()
        else:
            self.create_index()
    
    def create_index(self, index_type: str = None):
        """
        Create new FAISS index
        
        Args:
            index_type: 'flat' or 'ivf' (defaults to config)
        """
        index_type = index_type or config.FAISS_INDEX_TYPE
        
        logger.info(f"Creating {index_type.upper()} index (dimension={self.dimension})...")
        
        if index_type == 'flat':
            # Exact search - slower but 100% accurate
            if config.FAISS_METRIC == 'L2':
                base_index = faiss.IndexFlatL2(self.dimension)
            else:  # IP (cosine similarity)
                base_index = faiss.IndexFlatIP(self.dimension)
        
        elif index_type == 'ivf':
            # Approximate search - faster but ~95-99% accurate
            n_lists = config.FAISS_IVF_CLUSTERS
            quantizer = faiss.IndexFlatL2(self.dimension)
            base_index = faiss.IndexIVFFlat(quantizer, self.dimension, n_lists)
        
        else:
            raise ValueError(f"Unknown index type: {index_type}")
        
        # Wrap in IndexIDMap to store face_ids
        self.index = faiss.IndexIDMap(base_index)
        logger.info(f"FAISS index created ({index_type.upper()} with {config.FAISS_METRIC} metric)")
    
    def add_embedding(self, face_id: int, embedding: np.ndarray):
        """
        Add single embedding to index
        
        Args:
            face_id: Face ID from database
            embedding: 128-dim numpy array
        """
        if self.index is None:
            self.create_index()
        
        # Ensure correct shape and type
        embedding = embedding.astype(np.float32).reshape(1, -1)
        face_id_array = np.array([face_id], dtype=np.int64)
        
        self.index.add_with_ids(embedding, face_id_array)
        logger.debug(f"Added face_id {face_id} to FAISS index")
    
    def add_embeddings_batch(self, face_ids: List[int], embeddings: np.ndarray):
        """
        Add multiple embeddings to index (more efficient)
        
        Args:
            face_ids: List of face IDs from database
            embeddings: (N, 128) numpy array
        """
        if self.index is None:
            self.create_index()
        
        # Ensure correct shape and type
        embeddings = embeddings.astype(np.float32)
        if len(embeddings.shape) == 1:
            embeddings = embeddings.reshape(1, -1)
        
        face_id_array = np.array(face_ids, dtype=np.int64)
        
        self.index.add_with_ids(embeddings, face_id_array)
        logger.info(f"Added {len(face_ids)} embeddings to FAISS index")
    
    def search(
        self,
        query_embedding: np.ndarray,
        k: int = None,
        threshold: float = None
    ) -> Tuple[List[float], List[int]]:
        """
        Search for similar faces
        
        Args:
            query_embedding: 128-dim numpy array
            k: Number of results to return (defaults to config)
            threshold: Minimum similarity threshold (defaults to config)
        
        Returns:
            (distances, face_ids) - distances are L2 or IP scores
        """
        if self.index is None or self.index.ntotal == 0:
            logger.warning("FAISS index is empty")
            return [], []
        
        k = k or config.DEFAULT_SEARCH_RESULTS
        threshold = threshold or config.MIN_SIMILARITY_THRESHOLD
        
        # Ensure correct shape and type
        query_embedding = query_embedding.astype(np.float32).reshape(1, -1)
        
        # Search
        distances, indices = self.index.search(query_embedding, k)
        
        # Filter results
        distances = distances[0]
        indices = indices[0]
        
        # Convert distances to similarity scores
        if config.FAISS_METRIC == 'L2':
            # L2 distance: smaller = more similar
            # Convert to similarity: 0 = identical, 1 = very different
            similarities = distances / (1 + distances)  # Normalize
            similarities = 1 - similarities  # Invert so higher = more similar
        else:  # IP (cosine similarity)
            # IP: higher = more similar (already in [0, 1] range if normalized)
            similarities = distances
        
        # Filter by threshold
        valid_mask = similarities >= threshold
        filtered_similarities = similarities[valid_mask].tolist()
        filtered_face_ids = indices[valid_mask].tolist()
        
        logger.info(f"Found {len(filtered_face_ids)} matches above {threshold:.0%} similarity")
        
        return filtered_similarities, filtered_face_ids
    
    def save_index(self, path: str = None):
        """Save index to disk"""
        path = path or self.index_path
        
        if self.index is None:
            logger.warning("No index to save")
            return
        
        faiss.write_index(self.index, path)
        logger.info(f"Saved FAISS index to {path} ({self.index.ntotal} vectors)")
    
    def load_index(self, path: str = None):
        """Load index from disk"""
        path = path or self.index_path
        
        if not os.path.exists(path):
            logger.warning(f"Index file not found: {path}")
            return
        
        self.index = faiss.read_index(path)
        logger.info(f"Loaded FAISS index from {path} ({self.index.ntotal} vectors)")
    
    def get_total_vectors(self) -> int:
        """Get number of vectors in index"""
        if self.index is None:
            return 0
        return self.index.ntotal
    
    def clear_index(self):
        """Clear all vectors from index"""
        self.create_index()
        logger.info("FAISS index cleared")


if __name__ == '__main__':
    # Test FAISS manager
    logging.basicConfig(level=logging.INFO)
    
    manager = FAISSManager()
    
    # Add some test vectors
    print("\n=== Adding Test Vectors ===")
    for i in range(10):
        embedding = np.random.rand(128).astype(np.float32)
        manager.add_embedding(face_id=i+1, embedding=embedding)
    
    print(f"\nTotal vectors: {manager.get_total_vectors()}")
    
    # Search
    print("\n=== Searching ===")
    query = np.random.rand(128).astype(np.float32)
    similarities, face_ids = manager.search(query, k=5)
    
    print(f"Top 5 matches:")
    for sim, fid in zip(similarities, face_ids):
        print(f"  Face #{fid}: {sim:.1%} similar")
    
    # Save
    print("\n=== Saving ===")
    manager.save_index("test_index.bin")
