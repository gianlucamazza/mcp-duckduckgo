"""Tests for sandbox snapshot storage."""

import pytest

from mcp_duckduckgo.sandbox.snapshots import SnapshotStore, snapshot_store


def test_snapshot_store_record_and_list():
    store = SnapshotStore(max_entries=10)
    snapshot = store.record(
        url="https://example.com", content="Example content", metadata={"a": 1}
    )
    all_snapshots = store.list_snapshots()
    assert snapshot in all_snapshots
    assert snapshot.metadata["a"] == 1


def test_snapshot_store_diff():
    store = SnapshotStore(max_entries=10)
    first = store.record(url="https://example.com", content="line1", metadata={})
    second = store.record(
        url="https://example.com", content="line1\nline2", metadata={}
    )
    diff = store.diff(first.id, second.id, loader=lambda snap: snap.preview)
    assert first.id in diff.diff
    assert second.id in diff.diff


def test_global_snapshot_store_prunes():
    snapshot_store.clear()
    for i in range(205):
        snapshot_store.record(
            url=f"https://example.com/{i}", content=f"content {i}", metadata={}
        )
    assert len(snapshot_store.list_snapshots()) <= 200
