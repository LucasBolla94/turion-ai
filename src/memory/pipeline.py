from __future__ import annotations

from dataclasses import dataclass

from memory.retriever import Retriever
from memory.store import MemoryService
from memory.summarizer import LocalSummarizer
from memory.types import MemoryItem


@dataclass
class MemoryPipeline:
    memory: MemoryService
    retriever: Retriever
    summarizer: LocalSummarizer
    max_context_items: int = 12

    def build_context(self, user_id: str, query: str) -> tuple[list[MemoryItem], list[MemoryItem], str]:
        recent = self.memory.get_recent(user_id, limit=80)
        relevant = self.retriever.top(query, recent, limit=self.max_context_items)
        summary = self.summarizer.summarize([item.text for item in relevant]).text
        return recent, relevant, summary
