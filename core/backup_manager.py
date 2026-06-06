"""Rotating backup manager for both config (.bak chain) and DLLs (.backup chain)."""
from __future__ import annotations

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
    """
    if not path.is_file():
        raise FileNotFoundError(f"Cannot back up non-existent file: {path}")

    oldest = _chain_slot(path, suffix, cap)
    if oldest.exists():
        oldest.unlink()

    for slot in range(cap - 1, 0, -1):
        src = _chain_slot(path, suffix, slot - 1)
        dst = _chain_slot(path, suffix, slot)
        if src.exists():
            os.replace(src, dst)

    new_backup = _chain_slot(path, suffix, 0)
    shutil.copy2(path, new_backup)
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
