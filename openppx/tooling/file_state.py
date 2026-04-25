"""Lightweight file read/write state tracking for core tools."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FileReadState:
    """Snapshot of a file window observed by ``read_file``."""

    mtime_ns: int
    size: int
    offset: int
    limit: int | None
    variant: str
    content_hash: str
    can_dedup: bool = True


_STATE: dict[str, FileReadState] = {}


def _key(path: Path) -> str:
    return str(path.resolve())


def _hash_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record_read(path: Path, *, offset: int = 1, limit: int | None = None, variant: str = "") -> None:
    """Record that a file window has just been read successfully."""

    stat = path.stat()
    _STATE[_key(path)] = FileReadState(
        mtime_ns=stat.st_mtime_ns,
        size=stat.st_size,
        offset=offset,
        limit=limit,
        variant=variant,
        content_hash=_hash_path(path),
        can_dedup=True,
    )


def record_write(path: Path) -> None:
    """Record a local tool write.

    The write snapshot is intentionally not deduplicable. A later read should
    still return content once, even if the file hash already matches.
    """

    stat = path.stat()
    _STATE[_key(path)] = FileReadState(
        mtime_ns=stat.st_mtime_ns,
        size=stat.st_size,
        offset=1,
        limit=None,
        variant="",
        content_hash=_hash_path(path),
        can_dedup=False,
    )


def check_read(path: Path) -> str | None:
    """Return a warning when a write is attempted without a fresh read."""

    state = _STATE.get(_key(path))
    if state is None:
        return "Warning: this file has not been read with read_file in this session."

    stat = path.stat()
    if stat.st_mtime_ns != state.mtime_ns or stat.st_size != state.size:
        return "Warning: this file changed since it was last read with read_file."
    return None


def is_unchanged(path: Path, *, offset: int = 1, limit: int | None = None, variant: str = "") -> bool:
    """Return whether the requested file window matches the last read state."""

    state = _STATE.get(_key(path))
    if state is None or not state.can_dedup:
        return False
    if state.offset != offset or state.limit != limit or state.variant != variant:
        return False

    stat = path.stat()
    if stat.st_mtime_ns != state.mtime_ns or stat.st_size != state.size:
        return False
    return _hash_path(path) == state.content_hash


def clear() -> None:
    """Clear all tracked file state."""

    _STATE.clear()
