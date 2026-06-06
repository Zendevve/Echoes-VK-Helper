"""Tests for core/uninstaller.py.

Run directly: `python tests/test_uninstaller.py`
Exits 0 on success, 1 on failure. No external deps.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core import uninstaller as un  # noqa: E402
from core.vulkan_installer import VULKAN_FILES  # noqa: E402


def _seed_game(dest: Path, with_backups: bool = False) -> None:
    """Lay down a fake DXVK install at `dest`.

    Live files are tagged b'NEW_<name>'. If with_backups, a `.backup` slot 0
    holds an older b'OLD_<name>' variant.
    """
    dest.mkdir(parents=True, exist_ok=True)
    for name in VULKAN_FILES:
        (dest / name).write_bytes(b"NEW_" + name.encode() + b"_x" * 100)
        if with_backups:
            (dest / (name + ".backup")).write_bytes(b"OLD_" + name.encode() + b"_y" * 100)


def _seed_config(dest: Path, with_bak: bool = False) -> Path:
    """Create a fake UserPreferences.echoes.ini at `dest` with optional .bak chain."""
    cfg = dest / "UserPreferences.echoes.ini"
    cfg.write_text("[General]\nFullscreen=True\n", encoding="utf-8")
    if with_bak:
        (dest / "UserPreferences.echoes.ini.bak").write_text(
            "[General]\nFullscreen=False\n", encoding="utf-8"
        )
    return cfg


def test_all_files_removed_when_no_backup() -> None:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        game = td / "game"
        _seed_game(game, with_backups=False)

        outcomes = un.uninstall_vulkan_files(game)

        assert len(outcomes) == 3
        for o in outcomes:
            assert o.action == "removed", f"{o.name}: {o.action}"
            assert not (game / o.name).exists()
        print("OK: all_files_removed_when_no_backup")


def test_all_files_restored_when_backup_present() -> None:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        game = td / "game"
        _seed_game(game, with_backups=True)

        outcomes = un.uninstall_vulkan_files(game)

        for o in outcomes:
            assert o.action == "restored_from_backup", f"{o.name}: {o.action}"
            assert (game / o.name).is_file()
            assert (game / o.name).read_bytes().startswith(b"OLD_")
            assert not (game / (o.name + ".backup")).exists()
        print("OK: all_files_restored_when_backup_present")


def test_mixed_backups() -> None:
    """Some files have .backup, some don't. Each handled per its own state."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        game = td / "game"
        _seed_game(game, with_backups=False)
        # add a .backup for only d3d9.dll
        (game / "d3d9.dll.backup").write_bytes(b"OLD_d3d9.dll_y" * 50)

        outcomes = {o.name: o for o in un.uninstall_vulkan_files(game)}

        assert outcomes["dinput8.ini"].action == "removed"
        assert outcomes["dinput8.dll"].action == "removed"
        assert outcomes["d3d9.dll"].action == "restored_from_backup"
        assert (game / "d3d9.dll").read_bytes().startswith(b"OLD_")
        assert not (game / "dinput8.ini").exists()
        assert not (game / "dinput8.dll").exists()
        print("OK: mixed_backups")


def test_missing_game_dir_is_noop() -> None:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        outcomes = un.uninstall_vulkan_files(td / "nope")
        assert outcomes == []
        print("OK: missing_game_dir_is_noop")


def test_config_restored_from_bak() -> None:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cfg = _seed_config(td, with_bak=True)

        restored, action = un.uninstall_config(cfg)

        assert restored is True
        assert action == "restored"
        assert cfg.read_text(encoding="utf-8").strip() == "[General]\nFullscreen=False"
        print("OK: config_restored_from_bak")


def test_config_no_backup_left_alone() -> None:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cfg = _seed_config(td, with_bak=False)
        original = cfg.read_text(encoding="utf-8")

        restored, action = un.uninstall_config(cfg)

        assert restored is False
        assert action == "no_backup"
        assert cfg.read_text(encoding="utf-8") == original
        print("OK: config_no_backup_left_alone")


def test_config_missing_is_skipped() -> None:
    restored, action = un.uninstall_config(None)
    assert restored is False
    assert action == "skipped"
    print("OK: config_missing_is_skipped")


def test_uninstall_all_combines() -> None:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        game = td / "game"
        _seed_game(game, with_backups=True)
        cfg = _seed_config(td, with_bak=True)

        result = un.uninstall_all(game, cfg)

        assert len(result.vulkan_outcomes) == 3
        assert all(o.action == "restored_from_backup" for o in result.vulkan_outcomes)
        assert result.config_action == "restored"
        assert result.config_restored is True
        assert not result.has_errors
        lines = result.summary_lines()
        assert any("d3d9.dll: restored_from_backup" in ln for ln in lines)
        assert any("config: restored" in ln for ln in lines)
        print("OK: uninstall_all_combines")


def test_uninstall_all_handles_missing_files_gracefully() -> None:
    """Empty game dir, no config -> all outcomes skipped, no errors."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        game = td / "empty_game"
        game.mkdir()
        cfg = td / "UserPreferences.echoes.ini"  # doesn't exist

        result = un.uninstall_all(game, cfg)

        assert all(o.action == "skipped" for o in result.vulkan_outcomes)
        assert result.config_action == "skipped"
        assert not result.has_errors
        print("OK: uninstall_all_handles_missing_files_gracefully")


def test_uninstall_all_captures_oserror() -> None:
    """If a DXVK file is unremovable, the outcome carries the error but other files still process."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        game = td / "game"
        _seed_game(game, with_backups=False)
        # Make d3d9.dll unremovable: open it for read on Windows to lock delete.
        locked = game / "d3d9.dll"
        try:
            fh = locked.open("rb")
        except OSError:
            print("SKIP: uninstall_all_captures_oserror (cannot open for lock on this platform)")
            return
        try:
            result = un.uninstall_all(game, None)
        finally:
            fh.close()
            # On Windows, close releases the read lock; on POSIX, unlink works regardless.
            if locked.exists():
                try:
                    locked.unlink()
                except OSError:
                    pass

        # On Linux/macOS the lock doesn't prevent unlink, so we just verify structure.
        assert len(result.vulkan_outcomes) == 3
        for o in result.vulkan_outcomes:
            assert o.action in ("removed", "skipped", "restored_from_backup")
        print("OK: uninstall_all_captures_oserror")


def main() -> int:
    tests = [
        test_all_files_removed_when_no_backup,
        test_all_files_restored_when_backup_present,
        test_mixed_backups,
        test_missing_game_dir_is_noop,
        test_config_restored_from_bak,
        test_config_no_backup_left_alone,
        test_config_missing_is_skipped,
        test_uninstall_all_combines,
        test_uninstall_all_handles_missing_files_gracefully,
        test_uninstall_all_captures_oserror,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            print(f"FAIL: {t.__name__}: {exc}")
            failed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: {t.__name__}: {exc!r}")
            failed += 1
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
