"""
retrieval.py – Semantic retrieval helper.

Wraps EmbeddingProvider into a clean search API:
    retriever = SemanticRetriever(provider)
    retriever.index(texts)
    results = retriever.search("climate protest", top_k=20)
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .embeddings import EmbeddingProvider, get_provider

logger = logging.getLogger("echomatrix.retrieval")
TOKEN_RE = re.compile(r"\w+", re.UNICODE)


@dataclass
class SearchResult:
    """A single search hit with index and similarity score."""
    index: int
    score: float


class SemanticRetriever:
    """Thin wrapper that indexes a corpus and runs cosine-similarity search."""

    def __init__(self, provider: Optional[EmbeddingProvider] = None):
        self.provider = provider or get_provider()
        self._corpus_emb: Optional[np.ndarray] = None
        self._indexed_count: int = 0
        self._corpus_signature: tuple[str, ...] = ()
        self._retrieval_method: str = "uninitialized"

    def index(self, texts: list[str]) -> None:
        """Embed and store the corpus. Uses the provider's caching layer."""
        if not texts:
            self._corpus_emb = None
            self._indexed_count = 0
            self._corpus_signature = ()
            self._retrieval_method = "empty-corpus"
            return
        signature = tuple(texts)
        if self._corpus_emb is not None and self._corpus_signature == signature:
            logger.info("Skipping re-index; corpus unchanged (%d texts)", len(texts))
            return
        self._corpus_emb = self.provider.embed_corpus(texts)
        self._indexed_count = len(texts)
        self._corpus_signature = signature
        self._retrieval_method = "embedding-cosine"
        logger.info(
            "Indexed %d texts → (%d, %d) matrix",
            len(texts),
            *self._corpus_emb.shape,
        )

    def search(
        self,
        query: str,
        top_k: int = 20,
        threshold: float = 0.05,
    ) -> list[SearchResult]:
        """Rank corpus by cosine similarity to query.

        Args:
            query: natural-language search query
            top_k: max results to return
            threshold: minimum score to include (filters noise)

        Returns:
            Sorted list of SearchResult(index, score), highest first.
        """
        if self._corpus_emb is None or self._indexed_count == 0:
            return []

        if self._should_use_sparse_fallback(query):
            self._retrieval_method = "token-overlap-fallback"
            return self._lexical_fallback(query, top_k=top_k)

        query_emb = self.provider.embed_query(query)
        scores = self._corpus_emb @ query_emb          # dot product = cosine (normalized)

        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            s = float(scores[idx])
            if s < threshold:
                break                                    # sorted, so all remaining are lower
            results.append(SearchResult(index=int(idx), score=round(s, 4)))

        self._retrieval_method = "embedding-cosine"
        if not results:
            fallback = self._lexical_fallback(query, top_k=top_k)
            if fallback:
                self._retrieval_method = "embedding-cosine+token-overlap-fallback"
                return fallback
        return results

    @property
    def is_indexed(self) -> bool:
        return self._corpus_emb is not None and self._indexed_count > 0

    @property
    def retrieval_method(self) -> str:
        return self._retrieval_method

    def _should_use_sparse_fallback(self, query: str) -> bool:
        if self._corpus_emb is None:
            return True
        if self._indexed_count < 3:
            return True
        if self._corpus_emb.shape[1] <= 1:
            return True
        query_tokens = self._tokenize(query)
        if len(query_tokens) <= 1 and self._indexed_count < 10:
            return True
        return False

    def _lexical_fallback(self, query: str, top_k: int) -> list[SearchResult]:
        query_tokens = self._tokenize(query)
        if not query_tokens or not self._corpus_signature:
            return []

        scored: list[SearchResult] = []
        for idx, text in enumerate(self._corpus_signature):
            doc_tokens = self._tokenize(text)
            if not doc_tokens:
                continue
            overlap = len(query_tokens & doc_tokens)
            if overlap == 0:
                continue
            union = max(len(query_tokens | doc_tokens), 1)
            score = overlap / union
            scored.append(SearchResult(index=idx, score=round(float(score), 4)))

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def _tokenize(self, text: str) -> set[str]:
        return {
            token.lower()
            for token in TOKEN_RE.findall(text or "")
            if len(token.strip()) >= 2
        }
