from __future__ import annotations

import hashlib
import importlib.util
import logging
import os
from typing import Optional

import numpy as np

logger = logging.getLogger("echomatrix.embeddings")

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", ".cache")
DEFAULT_MODEL = "all-MiniLM-L6-v2"


class EmbeddingProvider:
    def __init__(
        self,
        model_name: Optional[str] = None,
        cache_dir: Optional[str] = None,
        batch_size: int = 256,
    ):
        self.model_name = model_name or os.environ.get(
            "ECHOMATRIX_EMBED_MODEL", DEFAULT_MODEL
        )
        self.cache_dir = os.path.abspath(cache_dir or CACHE_DIR)
        self.batch_size = batch_size

        self._model = None
        self._using_fallback = False
        self._tfidf_vectorizer = None
        self._svd = None
        self._cache_backend = self._detect_cache_backend()
        self._mem_cache: dict[str, np.ndarray] = {}

    def embed_corpus(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=np.float32)

        cache_key = self._hash_texts(texts)

        if cache_key in self._mem_cache:
            logger.info("Embeddings hit memory cache (%s)", cache_key[:8])
            return self._mem_cache[cache_key]

        cache_path = self._cache_path(cache_key)
        if self._can_use_disk_cache() and os.path.exists(cache_path):
            logger.info("Embeddings hit disk cache (%s)", cache_key[:8])
            emb = np.load(cache_path)
            if not self._is_cache_compatible(emb):
                logger.warning("Ignoring incompatible cached embeddings at %s", cache_path)
            else:
                self._mem_cache[cache_key] = emb
                return emb

        logger.info(
            "Computing embeddings for %d texts with model=%s",
            len(texts),
            self.model_name,
        )
        emb = self._encode(texts)
        self._save_cache(cache_key, emb)
        return emb

    def embed_query(self, query: str) -> np.ndarray:
        result = self._encode([query])
        return result[0]

    def warm_cache(self, texts: list[str]) -> None:
        if not texts:
            return
        self.embed_corpus(texts)
        logger.info("Embedding cache warmed for %d texts", len(texts))

    @property
    def dimension(self) -> int:
        probe = self._encode(["probe"])
        return probe.shape[1]

    def _encode(self, texts: list[str]) -> np.ndarray:
        if not self._using_fallback:
            try:
                return self._encode_st(texts)
            except Exception as e:
                logger.warning(
                    "sentence-transformers failed (%s), falling back to TF-IDF", e
                )
                self._using_fallback = True

        return self._encode_tfidf(texts)

    def _encode_st(self, texts: list[str]) -> np.ndarray:
        model = self._get_model()
        emb = model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=len(texts) > 500,
            normalize_embeddings=True,
        )
        return np.asarray(emb, dtype=np.float32)

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading model: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def _encode_tfidf(self, texts: list[str]) -> np.ndarray:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD
        from sklearn.preprocessing import normalize

        if self._tfidf_vectorizer is None:
            logger.info("Building TF-IDF fallback model")
            self._tfidf_vectorizer = TfidfVectorizer(
                max_features=10_000,
                sublinear_tf=True,
                strip_accents="unicode",
            )
            tfidf_matrix = self._tfidf_vectorizer.fit_transform(texts)

            max_components = min(384, tfidf_matrix.shape[1] - 1, len(texts) - 1)
            if max_components >= 2:
                self._svd = TruncatedSVD(n_components=max_components, random_state=42)
                self._svd.fit(tfidf_matrix)
                dense = self._svd.transform(tfidf_matrix)
            else:
                self._svd = None
                dense = tfidf_matrix.toarray()

            if dense.shape[1] == 0:
                dense = np.ones((len(texts), 1), dtype=np.float32)

            dense = normalize(dense, norm="l2").astype(np.float32)
            return dense

        tfidf_matrix = self._tfidf_vectorizer.transform(texts)
        if self._svd is None:
            dense = tfidf_matrix.toarray()
        else:
            dense = self._svd.transform(tfidf_matrix)

        if dense.shape[1] == 0:
            dense = np.ones((len(texts), 1), dtype=np.float32)

        dense = normalize(dense, norm="l2").astype(np.float32)
        return dense

    def _hash_texts(self, texts: list[str]) -> str:
        h = hashlib.sha256()
        h.update(
            f"model={self.model_name}|backend={self._cache_backend}|n={len(texts)}|".encode()
        )
        for t in texts:
            h.update(t.encode("utf-8", errors="replace"))
            h.update(b"\x00")  # separator
        return h.hexdigest()

    def _detect_cache_backend(self) -> str:
        if self._using_fallback:
            return "tfidf"
        if importlib.util.find_spec("sentence_transformers") is not None:
            return f"sentence-transformers:{self.model_name}"
        return "tfidf"

    def _is_cache_compatible(self, emb: np.ndarray) -> bool:
        if emb.ndim != 2:
            return False
        if self._cache_backend == "tfidf":
            return True
        return emb.shape[1] > 1

    def _can_use_disk_cache(self) -> bool:
        return self._cache_backend != "tfidf"

    def _cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"emb_{key[:24]}.npy")

    def _save_cache(self, key: str, emb: np.ndarray) -> None:
        self._mem_cache[key] = emb
        if not self._can_use_disk_cache():
            return
        os.makedirs(self.cache_dir, exist_ok=True)
        path = self._cache_path(key)
        np.save(path, emb)
        logger.info("Cached embeddings to %s", path)

_provider: Optional[EmbeddingProvider] = None


def get_provider() -> EmbeddingProvider:
    global _provider
    if _provider is None:
        _provider = EmbeddingProvider()
    return _provider

def embed_texts(texts: list[str]) -> np.ndarray:
    return get_provider().embed_corpus(texts)


def embed_query(query: str) -> np.ndarray:
    return get_provider().embed_query(query)


def cosine_search(
    query_emb: np.ndarray,
    corpus_emb: np.ndarray,
    top_k: int = 20,
) -> list[tuple[int, float]]:
    scores = corpus_emb @ query_emb
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [(int(i), float(scores[i])) for i in top_indices]
