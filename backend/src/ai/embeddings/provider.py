import os
import random
import hashlib
from abc import ABC, abstractmethod
from typing import List

try:
    from google import genai
except ImportError:
    genai = None


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings."""
        pass


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "models/text-embedding-004"):
        if genai is None:
            raise ImportError(
                "google-genai package is not installed. Please install it using 'pip install google-genai'."
            )
        api_key = os.getenv("GEMINI_API_KEY", "").strip("'\"")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not configured.")
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def embed_text(self, text: str) -> List[float]:
        if not text.strip():
            # Return zero vector for empty strings
            return [0.0] * 1536
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=text
        )
        if not response.embeddings:
            raise RuntimeError("Gemini embedding request returned no embeddings.")
        return response.embeddings[0].values

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        # Filter empty strings safely
        cleaned_texts = [t if t.strip() else " " for t in texts]
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=cleaned_texts
        )
        if not response.embeddings:
            raise RuntimeError("Gemini batch embedding request returned no embeddings.")
        return [e.values for e in response.embeddings]


class MockEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dimensions: int = 1536):
        self.dimensions = dimensions

    def embed_text(self, text: str) -> List[float]:
        if not text.strip():
            return [0.0] * self.dimensions
        # Generate deterministic seeded dimensions
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        vec = [rng.gauss(0, 1) for _ in range(self.dimensions)]
        norm = sum(x * x for x in vec) ** 0.5
        if norm == 0.0:
            return [0.0] * self.dimensions
        return [x / norm for x in vec]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


def get_embedding_provider(provider_name: str, model_name: str, dimensions: int = 1536) -> EmbeddingProvider:
    provider_name = provider_name.lower()
    if provider_name == "gemini":
        return GeminiEmbeddingProvider(model_name=model_name)
    elif provider_name == "mock":
        return MockEmbeddingProvider(dimensions=dimensions)
    else:
        raise ValueError(f"Unsupported embedding provider: {provider_name}")
