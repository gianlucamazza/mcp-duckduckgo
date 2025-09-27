"""Snapshot storage for sandboxed browsing sessions."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from difflib import unified_diff
from typing import Any, Callable


@dataclass
class Snapshot:
    """Persisted record of fetched content."""

    id: str
    url: str
    created_at: float
    content_hash: str
    preview: str
    metadata: dict[str, Any]


@dataclass
class SnapshotDiff:
    """Unified diff between two snapshots."""

    left_id: str
    right_id: str
    diff: str


class SnapshotStore:
    """In-memory snapshot ledger suitable for local sandboxing."""

    def __init__(self, max_entries: int = 200) -> None:
        self._entries: list[Snapshot] = []
        self._max_entries = max_entries

    @staticmethod
    def _hash_content(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _preview(content: str, limit: int = 240) -> str:
        stripped = " ".join(content.split())
        if len(stripped) <= limit:
            return stripped
        return f"{stripped[: limit - 1]}…"

    def record(
        self,
        *,
        url: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Snapshot:
        created_at = time.time()
        content_hash = self._hash_content(content)
        identifier = f"snap-{int(created_at * 1000)}-{content_hash[:8]}"
        snapshot = Snapshot(
            id=identifier,
            url=url,
            created_at=created_at,
            content_hash=content_hash,
            preview=self._preview(content),
            metadata=metadata or {},
        )

        self._entries.append(snapshot)
        self._prune_if_needed()
        return snapshot

    def list_snapshots(self) -> list[Snapshot]:
        return list(self._entries)

    def get_snapshot(self, snapshot_id: str) -> Snapshot | None:
        for entry in reversed(self._entries):
            if entry.id == snapshot_id:
                return entry
        return None

    def diff(
        self,
        left_id: str,
        right_id: str,
        *,
        loader: Callable[[Snapshot], str] | None = None,
    ) -> SnapshotDiff:
        left = self.get_snapshot(left_id)
        right = self.get_snapshot(right_id)

        if left is None or right is None:
            raise ValueError("Both snapshot IDs must exist for diff computation")

        loader = loader or (lambda snapshot: snapshot.preview)
        left_content = loader(left).splitlines(keepends=True)
        right_content = loader(right).splitlines(keepends=True)

        diff_lines = list(
            unified_diff(
                left_content,
                right_content,
                fromfile=left.id,
                tofile=right.id,
                n=3,
            )
        )
        diff_text = "".join(diff_lines)
        return SnapshotDiff(left_id=left_id, right_id=right_id, diff=diff_text)

    def clear(self) -> None:
        self._entries.clear()

    def _prune_if_needed(self) -> None:
        overflow = len(self._entries) - self._max_entries
        if overflow <= 0:
            return
        del self._entries[:overflow]


snapshot_store = SnapshotStore()


__all__ = ["Snapshot", "SnapshotDiff", "SnapshotStore", "snapshot_store"]
