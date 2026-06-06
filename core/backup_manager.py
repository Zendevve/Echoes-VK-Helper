"""Rotating backup manager for both config (.bak chain) and DLLs (.backup chain)."""

from __future__ import annotations

import contextlib
import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CAP = 5


def _chain_slot(path: Path, suffix: str, slot: int) -> Path:
    if slot == 0:
        return path.with_name(path.name + suffix)
    return path.with_name(path.name + f"{suffix}.{slot}")


def create_backup(path: Path, suffix: str = ".bak", cap: int = DEFAULT_CAP) -> Path:
    """Rotate the backup chain and copy `path` into slot 0.

    Chain: <name><suffix>.N-1 -> <name><suffix>.N, ..., <name><suffix> -> <name><suffix>.1
    Newest backup lives at <name><suffix> (slot 0).
    The oldest slot is dropped when the chain exceeds `cap`.

    Crash safety: the source is first copied to a unique temp file in
    the same directory (so the eventual `os.replace` is atomic on
    Windows / POSIX). Only after the copy succeeds is the chain
    rotated and the temp atomically renamed into slot 0. A crash
    during the copy leaves the existing chain untouched. A crash
    during rotation leaves the temp file behind (recoverable) but
    does not destroy the new content.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Cannot back up non-existent file: {path}")

    new_backup = _chain_slot(path, suffix, 0)

    # Pick a unique temp name: same dir (so os.replace is atomic),
    # distinct from any existing chain slot. PID + monotonic counter
    # prevents collisions when create_backup is called twice in quick
    # succession on the same source.
    counter = 0
    while True:
        tmp = new_backup.with_name(f"{new_backup.name}.tmp.{os.getpid()}.{counter}")
        if not tmp.exists():
            break
        counter += 1
        if counter > 1000:
            raise OSError(f"Could not find a unique temp name near {new_backup}")

    try:
        shutil.copy2(path, tmp)
    except OSError:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise

    # Rotate: drop oldest, shift each slot up by one. Each os.replace
    # is atomic. The temp file is not promoted to slot 0 until every
    # shift has succeeded, so a mid-rotation crash leaves slot 0
    # holding the previous-good content.
    oldest = _chain_slot(path, suffix, cap)
    with contextlib.suppress(FileNotFoundError):
        oldest.unlink()

    for slot in range(cap - 1, 0, -1):
        src = _chain_slot(path, suffix, slot - 1)
        dst = _chain_slot(path, suffix, slot)
        if src.exists():
            os.replace(src, dst)

    try:
        os.replace(tmp, new_backup)
    except OSError:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise

    logger.info("Created backup: %s", new_backup)
    return new_backup


def restore_backup(path: Path, suffix: str = ".bak", cap: int = DEFAULT_CAP) -> bool:
    """Restore from the newest available backup. Returns True if restored."""
    for slot in range(0, cap + 1):
        candidate = _chain_slot(path, suffix, slot)
        if candidate.is_file():
            tmp = path.with_suffix(path.suffix + ".restore.tmp")
            shutil.copy2(candidate, tmp)
            os.replace(tmp, path)
            logger.info("Restored %s from %s", path, candidate)
            return True
    logger.warning("No backup found for %s", path)
    return False


def list_backups(path: Path, suffix: str = ".bak", cap: int = DEFAULT_CAP) -> list[Path]:
    return [
        _chain_slot(path, suffix, slot)
        for slot in range(0, cap + 1)
        if _chain_slot(path, suffix, slot).is_file()
    ]
