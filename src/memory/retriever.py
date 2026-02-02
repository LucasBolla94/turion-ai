from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

try:
    from rank_bm25 import BM25Okapi
except Exception:  # pragma: no cover - optional
    BM25Okapi = None

from memory.types import MemoryItem


def _tokenize(text: str) -> list[str]:
    return [t for t in text.lower().split() if t]


@dataclass
class Retriever:
    min_score: float = 0.25

    def score(self, query: str, items: Iterable[MemoryItem]) -> list[tuple[MemoryItem, float]]:
        if BM25Okapi is None:
            return [(item, 0.0) for item in items]

        docs = [item.text for item in items]
        tokenized = [_tokenize(d) for d in docs]
        bm25 = BM25Okapi(tokenized)
        scores = bm25.get_scores(_tokenize(query))
        results: list[tuple[MemoryItem, float]] = []
        for item, score in zip(items, scores, strict=False):
            results.append((item, float(score)))

        max_score = max(scores) if len(scores) > 0 else 0.0
        normalized: list[tuple[MemoryItem, float]] = []
        for item, score in results:
            norm = score / max_score if max_score > 0 else 0.0
            normalized.append((item, norm))

        return normalized

    def top(self, query: str, items: list[MemoryItem], limit: int) -> list[MemoryItem]:
        scored = self.score(query, items)
        scored.sort(key=lambda x: x[1], reverse=True)
        return [item for item, score in scored if score >= self.min_score][:limit]
