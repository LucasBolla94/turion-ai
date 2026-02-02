from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MemoryItem:
    id: str
    user_id: str
    role: str
    text: str
    created_at: datetime
    tags: list[str] = field(default_factory=list)


@dataclass
class UserProfile:
    user_id: str
    persona: str | None = None
    preferences: str | None = None
    style: str | None = None
    updated_at: datetime | None = None
