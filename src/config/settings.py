from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class Settings:
    mode: str = "dev"
    llm_provider: str | None = None
    llm_api_key: str | None = None
    whatsapp_gateway_url: str | None = None
    whatsapp_api_key: str | None = None

    @classmethod
    def load(cls) -> "Settings":
        root = Path(__file__).resolve().parents[2]
        env = dotenv_values(root / ".env")
        return cls(
            mode=env.get("MODE", "dev"),
            llm_provider=env.get("LLM_PROVIDER"),
            llm_api_key=env.get("LLM_API_KEY"),
            whatsapp_gateway_url=env.get("WHATSAPP_GATEWAY_URL"),
            whatsapp_api_key=env.get("WHATSAPP_API_KEY"),
        )
