"""Semantic cache with freshness heuristics tailored to search intent."""

from __future__ import annotations

import copy
import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from .models import SearchIntent

INTENT_TTL_SECONDS: dict[SearchIntent, int] = {
    "news": 15 * 60,
    "technical": 24 * 60 * 60,
    "shopping": 6 * 60 * 60,
    "academic": 36 * 60 * 60,
    "finance": 3 * 60 * 60,
    "local": 2 * 60 * 60,
    "general": 6 * 60 * 60,
}


@dataclass
class CacheEntry:
    key: str
    intent: SearchIntent
    embedding_signature: str
    payload: dict[str, Any]
    created_at: float

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at


@dataclass
class CacheLookup:
    payload: dict[str, Any]
    age_seconds: float
    fresh: bool


class SemanticCache:
    """A bounded LRU cache keyed by semantic query fingerprints."""

    def __init__(self, max_entries: int = 256) -> None:
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_entries = max_entries

    @staticmethod
    def embed_query(query: str) -> str:
        digest = hashlib.sha256(query.lower().encode("utf-8")).hexdigest()
        return digest[:24]

    @staticmethod
    def _intent_ttl(intent: SearchIntent) -> int:
        return INTENT_TTL_SECONDS.get(intent, INTENT_TTL_SECONDS["general"])

    @staticmethod
    def make_key(
        *,
        intent: SearchIntent,
        embedding_signature: str,
        count: int,
        offset: int,
        page: int,
        site: str | None,
        time_period: str | None,
        related: bool,
        related_count: int | None,
    ) -> str:
        parts = [
            intent,
            embedding_signature,
            str(count),
            str(offset),
            str(page),
            site or "*",
            time_period or "*",
            "related" if related else "plain",
            str(related_count or 0),
        ]
        return "|".join(parts)

    def get(self, key: str, intent: SearchIntent) -> CacheLookup | None:
        entry = self._store.get(key)
        if entry is None:
            return None

        ttl = self._intent_ttl(intent)
        fresh = entry.age_seconds <= ttl

        if fresh:
            self._store.move_to_end(key)

        return CacheLookup(
            payload=copy.deepcopy(entry.payload),
            age_seconds=entry.age_seconds,
            fresh=fresh,
        )

    def set(
        self,
        key: str,
        *,
        intent: SearchIntent,
        embedding_signature: str,
        payload: dict[str, Any],
    ) -> None:
        if key in self._store:
            self._store.move_to_end(key)

        entry = CacheEntry(
            key=key,
            intent=intent,
            embedding_signature=embedding_signature,
            payload=copy.deepcopy(payload),
            created_at=time.time(),
        )

        self._store[key] = entry
        self._evict_if_needed()

    def mark_domain_stale(self, domain: str) -> None:
        lowered = domain.lower()
        keys_to_remove = []
        for key, entry in self._store.items():
            results = entry.payload.get("results", [])
            for result in results:
                candidate = (result.get("domain") or "").lower()
                if lowered in candidate:
                    keys_to_remove.append(key)
                    break

        for key in keys_to_remove:
            self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def _evict_if_needed(self) -> None:
        while len(self._store) > self._max_entries:
            self._store.popitem(last=False)


semantic_cache = SemanticCache()


__all__ = [
    "CacheEntry",
    "CacheLookup",
    "SemanticCache",
    "semantic_cache",
]
