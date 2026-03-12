"""
Embedding Service
Handles text embedding using sentence-transformers (MiniLM-L6)
with FAISS indexing for fast similarity search - Natural Language Processing
"""

import os
import numpy as np
import faiss
from typing import List, Tuple, Optional
from sentence_transformers import SentenceTransformer

from config import Config


class EmbeddingService:
    """Service for generating and managing text embeddings"""
    
    _instance = None
    _model = None
    _index = None
    _id_map = []  # Maps FAISS index positions to document IDs
    
    def __new__(cls):
        """Singleton pattern to avoid loading model multiple times"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        print("Loading embedding model...")
        self._model = SentenceTransformer(Config.EMBEDDING_MODEL_NAME)
        self._embedding_dim = self._model.get_sentence_embedding_dimension()
        self._index = None
        self._id_map = []
        self._load_or_create_index()
        self._initialized = True
        print(f"✓ Embedding model loaded (dim={self._embedding_dim})")
    
    def _load_or_create_index(self):
        """Load existing FAISS index or create new one"""
        if os.path.exists(Config.FAISS_INDEX_PATH):
            try:
                self._index = faiss.read_index(Config.FAISS_INDEX_PATH)
                # Load ID map
                id_map_path = Config.FAISS_INDEX_PATH + '.ids.npy'
                if os.path.exists(id_map_path):
                    self._id_map = np.load(id_map_path).tolist()
                print(f"✓ Loaded FAISS index with {self._index.ntotal} vectors")
            except Exception as e:
                print(f"Error loading FAISS index: {e}")
                self._create_new_index()
        else:
            self._create_new_index()
    
    def _create_new_index(self):
        """Create a new FAISS index"""
        # Using IndexFlatIP for inner product (cosine similarity with normalized vectors)
        self._index = faiss.IndexFlatIP(self._embedding_dim)
        self._id_map = []
        print("✓ Created new FAISS index")
    
    def save_index(self):
        """Save FAISS index to disk"""
        os.makedirs(os.path.dirname(Config.FAISS_INDEX_PATH), exist_ok=True)
        faiss.write_index(self._index, Config.FAISS_INDEX_PATH)
        np.save(Config.FAISS_INDEX_PATH + '.ids.npy', np.array(self._id_map))
    
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.astype('float32')
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for multiple texts"""
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.astype('float32')
    
    def add_to_index(self, doc_id: str, embedding: np.ndarray):
        """Add a single embedding to the FAISS index"""
        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)
        self._index.add(embedding)
        self._id_map.append(doc_id)
    
    def add_batch_to_index(self, doc_ids: List[str], embeddings: np.ndarray):
        """Add multiple embeddings to the FAISS index"""
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        self._index.add(embeddings)
        self._id_map.extend(doc_ids)
    
    def search(self, query_embedding: np.ndarray, k: int = 10) -> List[Tuple[str, float]]:
        """
        Search for similar documents in the FAISS index
        Returns list of (doc_id, similarity_score) tuples
        """
        if self._index.ntotal == 0:
            return []
        
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Search
        k = min(k, self._index.ntotal)
        scores, indices = self._index.search(query_embedding, k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self._id_map):
                results.append((self._id_map[idx], float(score)))
        
        return results
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings"""
        # Embeddings are already normalized, so dot product = cosine similarity
        return float(np.dot(embedding1, embedding2))
    
    def compute_similarity_matrix(self, embeddings: np.ndarray) -> np.ndarray:
        """Compute pairwise similarity matrix for a set of embeddings"""
        # Normalize if not already
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / (norms + 1e-8)
        # Dot product of normalized vectors = cosine similarity
        return np.dot(normalized, normalized.T)
    
    def rank_by_similarity(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: np.ndarray,
        candidate_ids: List[str]
    ) -> List[Tuple[str, float]]:
        """
        Rank candidates by similarity to query
        Returns sorted list of (candidate_id, similarity_score) tuples
        """
        if len(candidate_embeddings) == 0:
            return []
        
        # Compute similarities
        similarities = np.dot(candidate_embeddings, query_embedding)
        
        # Create sorted results
        results = list(zip(candidate_ids, similarities.tolist()))
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def embedding_to_bytes(self, embedding: np.ndarray) -> bytes:
        """Convert embedding to bytes for database storage"""
        return embedding.tobytes()
    
    def bytes_to_embedding(self, data: bytes) -> np.ndarray:
        """Convert bytes back to embedding array"""
        return np.frombuffer(data, dtype='float32')
    
    def clear_index(self):
        """Clear the FAISS index"""
        self._create_new_index()
    
    @property
    def index_size(self) -> int:
        """Return number of vectors in the index"""
        return self._index.ntotal if self._index else 0
