from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class Summary:
    text: str


class LocalSummarizer:
    def summarize(self, items: Iterable[str], max_sentences: int = 4) -> Summary:
        # Simple extractive summarizer: pick the most information-dense sentences.
        text = " ".join(items).strip()
        if not text:
            return Summary(text="")
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        return Summary(text=". ".join(sentences[:max_sentences]) + ("." if sentences else ""))
