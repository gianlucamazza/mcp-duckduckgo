"""Tests for the semantic cache implementation."""

from __future__ import annotations

from unittest.mock import patch

from mcp_duckduckgo.semantic_cache import SemanticCache


def test_make_key_and_embed_are_deterministic():
    sig = SemanticCache.embed_query("Test Query")
    key = SemanticCache.make_key(
        intent="general",
        embedding_signature=sig,
        count=5,
        offset=0,
        page=1,
        site=None,
        time_period=None,
        related=False,
        related_count=None,
    )

    assert sig == SemanticCache.embed_query("test query")
    assert key == f"general|{sig}|5|0|1|*|*|plain|0"


def test_cache_get_fresh_and_stale_behavior():
    cache = SemanticCache()
    key = "k"
    payload = {"results": []}

    with patch("mcp_duckduckgo.semantic_cache.time.time", return_value=1000):
        cache.set(key, intent="news", embedding_signature="sig", payload=payload)

    with patch("mcp_duckduckgo.semantic_cache.time.time", return_value=1000):
        lookup = cache.get(key, intent="news")
    assert lookup and lookup.fresh

    with patch(
        "mcp_duckduckgo.semantic_cache.time.time",
        return_value=1000 + 20 * 60,
    ):
        stale_lookup = cache.get(key, intent="news")
    assert stale_lookup and not stale_lookup.fresh


def test_mark_domain_stale_removes_entries():
    cache = SemanticCache()
    key = "k"
    cache.set(
        key,
        intent="general",
        embedding_signature="sig",
        payload={"results": [{"domain": "example.com"}]},
    )

    cache.mark_domain_stale("example.com")
    assert cache.get(key, intent="general") is None


def test_eviction_enforces_capacity():
    cache = SemanticCache(max_entries=2)
    for i in range(3):
        cache.set(
            f"key-{i}",
            intent="general",
            embedding_signature=f"sig-{i}",
            payload={"results": []},
        )

    assert cache.get("key-0", intent="general") is None
    assert cache.get("key-2", intent="general") is not None
