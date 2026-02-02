from __future__ import annotations

from dataclasses import dataclass

from adapters.grok import GrokClient, LLMRequest
from config.settings import Settings
from memory.pipeline import MemoryPipeline
from memory.retriever import Retriever
from memory.store import MemoryConfig, MemoryService
from memory.summarizer import LocalSummarizer
from memory.types import MemoryItem, UserProfile

try:
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover - optional
    fuzz = None


@dataclass
class Brain:
    settings: Settings
    memory: MemoryService
    pipeline: MemoryPipeline
    grok: GrokClient | None = None

    @classmethod
    def build(cls, settings: Settings) -> "Brain":
        memory = MemoryService(
            MemoryConfig(
                host=settings.db_host,
                port=settings.db_port,
                dbname=settings.db_name,
                user=settings.db_user,
                password=settings.db_password,
                cache_ttl_sec=settings.memory_cache_ttl_sec,
            )
        )
        pipeline = MemoryPipeline(
            memory=memory,
            retriever=Retriever(min_score=settings.memory_min_relevance),
            summarizer=LocalSummarizer(),
            max_context_items=settings.memory_max_context_items,
        )
        grok = None
        if settings.llm_provider and settings.llm_provider.lower() == "grok":
            if settings.llm_api_base and settings.llm_api_key:
                grok = GrokClient(settings.llm_api_base, settings.llm_api_key)
        return cls(settings=settings, memory=memory, pipeline=pipeline, grok=grok)

    def handle(self, user_id: str, message: str) -> str:
        self.memory.add_message(user_id, "user", message)

        recent, relevant, summary = self.pipeline.build_context(user_id, message)
        profile = self.memory.get_profile(user_id)

        shortcut = self._shortcut_reply(message, recent)
        if shortcut:
            self.memory.add_message(user_id, "assistant", shortcut)
            return shortcut

        if not self.grok:
            reply = self._fallback_reply(summary)
            self.memory.add_message(user_id, "assistant", reply)
            return reply

        prompt = self._build_prompt(message, summary, profile, relevant)
        response = self.grok.generate(prompt)

        reply = response.text.strip() or "Ok."
        self.memory.add_message(user_id, "assistant", reply)

        self._maybe_maintenance(user_id, recent)
        return reply

    def _maybe_maintenance(self, user_id: str, recent: list[MemoryItem]) -> None:
        if not self.grok:
            return
        count = self.memory.count_messages(user_id)
        if count < self.settings.grok_warmup_messages:
            self._update_profile(user_id, recent)
            return
        if count % self.settings.grok_maintenance_every == 0:
            self._update_profile(user_id, recent)

    def _update_profile(self, user_id: str, recent: list[MemoryItem]) -> None:
        if not self.grok:
            return
        snippet = "\n".join([f"{i.role}: {i.text}" for i in recent[:20]])
        req = LLMRequest(
            system=(
                "Extraia estilo, preferências e persona do usuário. "
                "Responda em texto curto com três linhas: persona=..., style=..., preferences=..."
            ),
            user="Atualize o perfil do usuário.",
            context=snippet,
            max_tokens=300,
        )
        resp = self.grok.generate(req).text
        profile = self._parse_profile(user_id, resp)
        if profile:
            self.memory.upsert_profile(profile)

    def _parse_profile(self, user_id: str, text: str) -> UserProfile | None:
        persona = None
        style = None
        preferences = None
        for line in text.splitlines():
            if "persona=" in line:
                persona = line.split("persona=", 1)[1].strip()
            if "style=" in line:
                style = line.split("style=", 1)[1].strip()
            if "preferences=" in line:
                preferences = line.split("preferences=", 1)[1].strip()
        if not any([persona, style, preferences]):
            return None
        return UserProfile(user_id=user_id, persona=persona, style=style, preferences=preferences)

    def _shortcut_reply(self, message: str, recent: list[MemoryItem]) -> str | None:
        if fuzz is None:
            return None
        best_score = 0.0
        best_reply: str | None = None

        for i in range(len(recent) - 1):
            if recent[i].role != "user":
                continue
            if recent[i + 1].role != "assistant":
                continue
            score = fuzz.ratio(message, recent[i].text) / 100.0
            if score > best_score:
                best_score = score
                best_reply = recent[i + 1].text

        if best_score >= self.settings.routing_shortcut_similarity:
            return best_reply
        return None

    def _build_prompt(
        self,
        message: str,
        summary: str,
        profile: UserProfile | None,
        relevant: list[MemoryItem],
    ) -> LLMRequest:
        persona = (
            "Você é um assistente útil e humano, adaptando-se ao usuário."
            if not profile or not profile.persona
            else profile.persona
        )
        style = profile.style if profile and profile.style else "Responda de forma clara e objetiva."

        context_lines = []
        if summary:
            context_lines.append("Resumo relevante: " + summary)
        for item in relevant:
            context_lines.append(f"{item.role}: {item.text}")

        context = "\n".join(context_lines)

        return LLMRequest(
            system=f"{persona}\n{style}",
            user=message,
            context=context,
            max_tokens=self.settings.llm_max_tokens,
        )

    def _fallback_reply(self, summary: str) -> str:
        if summary:
            return f"Entendi. Resumo do contexto: {summary}"
        return "Entendi."
