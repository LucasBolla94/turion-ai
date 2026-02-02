from __future__ import annotations

from dataclasses import dataclass

import requests


@dataclass
class LLMRequest:
    system: str
    user: str
    context: str
    max_tokens: int = 2000


@dataclass
class LLMResponse:
    text: str
    confidence: float = 0.5


@dataclass
class GrokClient:
    api_base: str
    api_key: str

    def generate(self, req: LLMRequest) -> LLMResponse:
        # Generic JSON API; update for your Grok endpoint when ready.
        payload = {
            "system": req.system,
            "user": req.user,
            "context": req.context,
            "max_tokens": req.max_tokens,
        }
        headers = {"authorization": f"Bearer {self.api_key}"}
        resp = requests.post(self.api_base, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return LLMResponse(text=data.get("text", ""), confidence=float(data.get("confidence", 0.5)))
