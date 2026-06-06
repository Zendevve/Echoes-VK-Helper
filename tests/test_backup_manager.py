"""Tests for core/backup_manager.py.

Run directly: `python tests/test_backup_manager.py`
Exits 0 on success, 1 on failure. No external deps.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.backup_manager import (  # noqa: E402
    DEFAULT_CAP,
    _chain_slot,
    create_backup,
    list_backups,
    restore_backup,
)


def _setup(tmp: Path) -> Path:
    src = tmp / "config.ini"
    src.write_text("v0", encoding="utf-8")
    return src


def test_six_iteration_chain() -> None:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        src = _setup(tmp)
        cap = DEFAULT_CAP

        for i in range(1, cap + 2):
            src.write_text(f"v{i}", encoding="utf-8")
            create_backup(src)

        backups = list_backups(src)
        assert len(backups) == cap, (
            f"expected {cap} backups, got {len(backups)}: {backups}"
        )

        slot0 = _chain_slot(src, ".bak", 0)
        assert slot0.read_text(encoding="utf-8") == f"v{cap + 1}"

        slot_cap_minus_1 = _chain_slot(src, ".bak", cap - 1)
        assert slot_cap_minus_1.read_text(encoding="utf-8") == "v2"

        slot_cap = _chain_slot(src, ".bak", cap)
        assert not slot_cap.exists()

        leftovers = list(tmp.glob("config.ini.bak.tmp.*"))
        assert not leftovers, f"temp files leaked: {leftovers}"
        print("test_six_iteration_chain: PASS")


def test_concurrent_unique_temp_names() -> None:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        src = tmp / "config.ini"
        src.write_text("v0", encoding="utf-8")

        src.write_text("v1", encoding="utf-8")
        create_backup(src)
        src.write_text("v2", encoding="utf-8")
        create_backup(src)

        slot0 = _chain_slot(src, ".bak", 0)
        slot1 = _chain_slot(src, ".bak", 1)
        assert slot0.read_text(encoding="utf-8") == "v2"
        assert slot1.read_text(encoding="utf-8") == "v1"

        leftovers = list(tmp.glob("config.ini.bak.tmp.*"))
        assert not leftovers, f"temp files leaked: {leftovers}"
        print("test_concurrent_unique_temp_names: PASS")


def test_restore_after_rotation() -> None:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        src = _setup(tmp)
        src.write_text("v1", encoding="utf-8")
        create_backup(src)
        src.write_text("v2", encoding="utf-8")
        create_backup(src)

        src.write_text("CORRUPTED", encoding="utf-8")
        assert restore_backup(src)
        assert src.read_text(encoding="utf-8") == "v2"
        print("test_restore_after_rotation: PASS")


def test_missing_source_raises() -> None:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        missing = tmp / "nope.ini"
        try:
            create_backup(missing)
        except FileNotFoundError:
            print("test_missing_source_raises: PASS")
            return
        raise AssertionError("expected FileNotFoundError")


if __name__ == "__main__":
    test_six_iteration_chain()
    test_concurrent_unique_temp_names()
    test_restore_after_rotation()
    test_missing_source_raises()
    print("ALL BACKUP MANAGER TESTS PASS")
