from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


def _env_get(env: dict[str, str | None], key: str, default: str | None = None) -> str | None:
    value = env.get(key)
    if value is None:
        return default
    return value


def _env_bool(env: dict[str, str | None], key: str, default: bool = False) -> bool:
    raw = env.get(key)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    mode: str = "dev"
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_api_base: str | None = None
    llm_max_tokens: int = 20000

    whatsapp_gateway_url: str | None = None
    whatsapp_api_key: str | None = None

    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = "turion"
    db_user: str = "turion"
    db_password: str | None = None

    memory_user_id: str = "default"
    memory_use_embeddings: bool = False
    memory_cache_ttl_sec: int = 3600
    memory_max_context_items: int = 12
    memory_min_relevance: float = 0.25

    routing_confidence_threshold: float = 0.78
    routing_shortcut_similarity: float = 0.90

    grok_warmup_messages: int = 50
    grok_maintenance_every: int = 20

    @classmethod
    def load(cls) -> "Settings":
        root = Path(__file__).resolve().parents[2]
        env = dotenv_values(root / ".env")
        return cls(
            mode=_env_get(env, "MODE", "dev") or "dev",
            llm_provider=_env_get(env, "LLM_PROVIDER"),
            llm_api_key=_env_get(env, "LLM_API_KEY"),
            llm_api_base=_env_get(env, "LLM_API_BASE"),
            llm_max_tokens=int(_env_get(env, "LLM_MAX_TOKENS", "20000") or "20000"),
            whatsapp_gateway_url=_env_get(env, "WHATSAPP_GATEWAY_URL"),
            whatsapp_api_key=_env_get(env, "WHATSAPP_API_KEY"),
            db_host=_env_get(env, "DB_HOST", "127.0.0.1") or "127.0.0.1",
            db_port=int(_env_get(env, "DB_PORT", "5432") or "5432"),
            db_name=_env_get(env, "DB_NAME", "turion") or "turion",
            db_user=_env_get(env, "DB_USER", "turion") or "turion",
            db_password=_env_get(env, "DB_PASSWORD"),
            memory_user_id=_env_get(env, "MEMORY_USER_ID", "default") or "default",
            memory_use_embeddings=_env_bool(env, "MEMORY_USE_EMBEDDINGS", False),
            memory_cache_ttl_sec=int(_env_get(env, "MEMORY_CACHE_TTL_SEC", "3600") or "3600"),
            memory_max_context_items=int(_env_get(env, "MEMORY_MAX_CONTEXT_ITEMS", "12") or "12"),
            memory_min_relevance=float(_env_get(env, "MEMORY_MIN_RELEVANCE", "0.25") or "0.25"),
            routing_confidence_threshold=float(_env_get(env, "ROUTING_CONF_THRESHOLD", "0.78") or "0.78"),
            routing_shortcut_similarity=float(_env_get(env, "ROUTING_SHORTCUT_SIM", "0.90") or "0.90"),
            grok_warmup_messages=int(_env_get(env, "GROK_WARMUP_MESSAGES", "50") or "50"),
            grok_maintenance_every=int(_env_get(env, "GROK_MAINTENANCE_EVERY", "20") or "20"),
        )
