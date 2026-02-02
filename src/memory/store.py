from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import RealDictCursor

from memory.types import MemoryItem, UserProfile


@dataclass
class MemoryConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str | None
    cache_ttl_sec: int = 3600


@dataclass
class MemoryService:
    config: MemoryConfig
    _conn: psycopg2.extensions.connection | None = field(default=None, init=False)
    _cache: dict[str, tuple[float, list[MemoryItem]]] = field(default_factory=dict, init=False)

    def _conn_or_none(self) -> psycopg2.extensions.connection | None:
        if self._conn:
            return self._conn
        if not self.config.password:
            return None
        self._conn = psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            dbname=self.config.dbname,
            user=self.config.user,
            password=self.config.password,
        )
        self._conn.autocommit = True
        return self._conn

    def add_message(self, user_id: str, role: str, text: str, tags: list[str] | None = None) -> MemoryItem:
        item = MemoryItem(
            id=str(uuid.uuid4()),
            user_id=user_id,
            role=role,
            text=text,
            created_at=datetime.now(timezone.utc),
            tags=tags or [],
        )
        conn = self._conn_or_none()
        if conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into memory_items (id, user_id, role, text, tags, created_at)
                    values (%s, %s, %s, %s, %s, %s)
                    """,
                    (item.id, item.user_id, item.role, item.text, item.tags, item.created_at),
                )
        self._cache.pop(user_id, None)
        return item

    def get_recent(self, user_id: str, limit: int = 50) -> list[MemoryItem]:
        now = time.time()
        cached = self._cache.get(user_id)
        if cached and now - cached[0] <= self.config.cache_ttl_sec:
            return cached[1]

        conn = self._conn_or_none()
        if not conn:
            return []
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                select id, user_id, role, text, tags, created_at
                from memory_items
                where user_id = %s
                order by created_at desc
                limit %s
                """,
                (user_id, limit),
            )
            rows = cur.fetchall()
        items = []
        for row in rows:
            items.append(
                MemoryItem(
                    id=row["id"],
                    user_id=row["user_id"],
                    role=row["role"],
                    text=row["text"],
                    created_at=row["created_at"],
                    tags=row.get("tags") or [],
                )
            )
        self._cache[user_id] = (now, items)
        return items

    def count_messages(self, user_id: str) -> int:
        conn = self._conn_or_none()
        if not conn:
            return 0
        with conn.cursor() as cur:
            cur.execute(
                """
                select count(*) from memory_items where user_id = %s
                """,
                (user_id,),
            )
            return int(cur.fetchone()[0])

    def get_profile(self, user_id: str) -> UserProfile | None:
        conn = self._conn_or_none()
        if not conn:
            return None
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                select user_id, persona, preferences, style, language, updated_at
                from user_profiles
                where user_id = %s
                limit 1
                """,
                (user_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return UserProfile(
            user_id=row["user_id"],
            persona=row.get("persona"),
            preferences=row.get("preferences"),
            style=row.get("style"),
            language=row.get("language"),
            updated_at=row.get("updated_at"),
        )

    def upsert_profile(self, profile: UserProfile) -> None:
        conn = self._conn_or_none()
        if not conn:
            return
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into user_profiles (user_id, persona, preferences, style, language, updated_at)
                values (%s, %s, %s, %s, %s, %s)
                on conflict (user_id)
                do update set
                    persona = excluded.persona,
                    preferences = excluded.preferences,
                    style = excluded.style,
                    language = excluded.language,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.user_id,
                    profile.persona,
                    profile.preferences,
                    profile.style,
                    profile.language,
                    datetime.now(timezone.utc),
                ),
            )


@dataclass
class MemorySnapshot:
    user_id: str
    recent: list[MemoryItem]
    profile: UserProfile | None
