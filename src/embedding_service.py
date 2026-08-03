"""
Generate embeddings using sentence-transformers (all-MiniLM-L6-v2).
Phase 1 uses local embeddings for quick iteration; Phase 2+ can swap to API-based.
"""

from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Generates embeddings using a local sentence-transformer model."""

    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string into a vector."""
        embedding = self.model.encode(text, convert_to_numpy=False)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts efficiently."""
        embeddings = self.model.encode(texts, convert_to_numpy=False)
        return [e.tolist() for e in embeddings]


if __name__ == "__main__":
    service = EmbeddingService()
    test_texts = [
        "Engineering payroll was $475,000 in Q3, 5.6% over budget.",
        "Sales and marketing campaign spend was significantly over budget.",
    ]
    vectors = service.embed_batch(test_texts)
    print(f"Generated {len(vectors)} embeddings")
    print(f"Embedding dimension: {len(vectors[0])}")
