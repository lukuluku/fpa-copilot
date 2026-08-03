"""
FAISS-based retrieval: build index, search, and return top-k chunks with scores.
"""

import faiss
import numpy as np
from dataclasses import dataclass

from src.data_loader import Chunk
from src.embedding_service import EmbeddingService


@dataclass
class RetrievalResult:
    """A single retrieved chunk with its similarity score."""
    chunk: Chunk
    score: float  # Normalized similarity (0.0 to 1.0, higher is better)


class FAISSRetrieval:
    """Build and query a FAISS index over embedded chunks."""

    def __init__(self, chunks: list[Chunk], embedding_service: EmbeddingService):
        self.chunks = chunks
        self.embedding_service = embedding_service
        self.index = None
        self._build_index()

    def _build_index(self):
        """Embed all chunks and build a FAISS index."""
        print(f"Embedding {len(self.chunks)} chunks...")
        texts = [chunk.text for chunk in self.chunks]
        vectors = self.embedding_service.embed_batch(texts)

        # Convert to numpy array (FAISS expects float32)
        vectors_array = np.array(vectors, dtype=np.float32)

        # Create FAISS index (L2 distance — Euclidean)
        dimension = vectors_array.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(vectors_array)

        print(f"Built FAISS index: {self.index.ntotal} vectors, dimension {dimension}")

    def search(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """
        Search for chunks similar to query.
        Returns top_k results with similarity scores.
        """
        # Embed the query
        query_vector = self.embedding_service.embed_text(query)
        query_array = np.array([query_vector], dtype=np.float32)

        # Search FAISS index (returns distances and indices)
        distances, indices = self.index.search(query_array, top_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            # FAISS returns L2 distance; convert to similarity score (0-1)
            # Lower L2 distance = higher similarity
            # Normalize: similarity = 1 / (1 + distance)
            similarity = 1.0 / (1.0 + float(dist))

            result = RetrievalResult(
                chunk=self.chunks[idx],
                score=similarity,
            )
            results.append(result)

        return results


if __name__ == "__main__":
    from src.data_loader import load_csv, create_chunks

    rows = load_csv("data/sample_budget_data.csv")
    chunks = create_chunks(rows)

    embedding_service = EmbeddingService()
    retrieval = FAISSRetrieval(chunks, embedding_service)

    # Test query
    query = "Which cost centers had the largest budget overruns?"
    print(f"\nQuery: {query}")
    results = retrieval.search(query, top_k=3)

    print("\nTop results:")
    for i, result in enumerate(results, 1):
        print(f"{i}. (score: {result.score:.3f}) {result.chunk.text}")
