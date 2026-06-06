"""Tests for tools/update_vulkan.py.

Run directly: `python tests/test_update_vulkan.py`
Exits 0 on success, 1 on failure. No external deps.
"""
from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools import update_vulkan as uv  # noqa: E402


def _make_zip(path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)


def _seed_dest(dest: Path) -> None:
    """Create a complete initial asset set at dest."""
    dest.mkdir(parents=True, exist_ok=True)
    for name in uv.REQUIRED_FILES:
        (dest / name).write_bytes(b"OLD_" + name.encode() + b"_x" * 100)


def test_install_happy_path() -> None:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        dest = td / "vulkan"
        _seed_dest(dest)

        new_files = {n: b"NEW_" + n.encode() + b"_y" * 200 for n in uv.REQUIRED_FILES}
        zip_path = td / "provider.zip"
        _make_zip(zip_path, new_files)

        report = uv._atomic_replace(zip_path, dest)

        assert len(report) == 3
        for name, old_size, new_size, old_hash, new_hash in report:
            assert old_size > 0
            assert new_size > 0
            assert new_size != old_size
            assert new_hash != old_hash
            assert (dest / name).read_bytes() == new_files[name]

        assert not (dest / uv.PREVIOUS_DIRNAME).exists(), "no snapshot in this test"
        print("OK: install_happy_path")


def test_install_rejects_extras() -> None:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        dest = td / "vulkan"
        _seed_dest(dest)
        zip_path = td / "provider.zip"
        _make_zip(
            zip_path,
            {n: b"x" * 200 for n in uv.REQUIRED_FILES} | {"readme.txt": b"hi"},
        )
        try:
            uv.verify_zip(zip_path)
        except uv.UpdateError as exc:
            assert "unexpected files" in str(exc).lower() or "extras" in str(exc).lower() or "readme.txt" in str(exc)
            print("OK: install_rejects_extras")
            return
        raise AssertionError("verify_zip accepted archive with extras")


def test_install_rejects_missing() -> None:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        dest = td / "vulkan"
        _seed_dest(dest)
        zip_path = td / "provider.zip"
        # Drop d3d9.dll
        partial = {n: b"x" * 200 for n in uv.REQUIRED_FILES if n != "d3d9.dll"}
        _make_zip(zip_path, partial)
        try:
            uv.verify_zip(zip_path)
        except uv.UpdateError as exc:
            assert "d3d9.dll" in str(exc)
            print("OK: install_rejects_missing")
            return
        raise AssertionError("verify_zip accepted archive missing d3d9.dll")


def test_install_rejects_subdir() -> None:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        zip_path = td / "provider.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("x64/dinput8.dll", b"x" * 100)
        try:
            uv.verify_zip(zip_path)
        except uv.UpdateError as exc:
            assert "subdirectories" in str(exc).lower() or "x64" in str(exc)
            print("OK: install_rejects_subdir")
            return
        raise AssertionError("verify_zip accepted archive with nested dirs")


def test_size_guard_truncation() -> None:
    """New file < 50% of old must be refused (truncated download guard)."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        dest = td / "vulkan"
        _seed_dest(dest)
        zip_path = td / "provider.zip"
        # Same files, but make new dinput8.dll tiny (1% of old)
        tiny = {n: b"N" * 200 for n in uv.REQUIRED_FILES}
        # Make sure it's under 50% of old
        old_size = (dest / "dinput8.dll").stat().st_size
        tiny["dinput8.dll"] = b"T" * max(1, old_size // 100)
        _make_zip(zip_path, tiny)

        # verify_zip should pass; _atomic_replace should raise
        uv.verify_zip(zip_path)
        try:
            uv._atomic_replace(zip_path, dest)
        except uv.UpdateError as exc:
            assert "truncated" in str(exc).lower() or "guard" in str(exc).lower()
            print("OK: size_guard_truncation")
            return
        raise AssertionError("size guard did not trip on truncated file")


def test_full_install_then_rollback() -> None:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        dest = td / "vulkan"
        _seed_dest(dest)
        old_bytes = {n: (dest / n).read_bytes() for n in uv.REQUIRED_FILES}

        zip_path = td / "provider.zip"
        new_bytes = {n: b"FRESH_" + n.encode() + b"_z" * 300 for n in uv.REQUIRED_FILES}
        _make_zip(zip_path, new_bytes)

        # snapshot + install
        snap = uv._snapshot_current(dest)
        uv._atomic_replace(zip_path, dest)
        for n in uv.REQUIRED_FILES:
            assert (dest / n).read_bytes() == new_bytes[n]

        # rollback using manifest
        manifest_path = snap / uv.MANIFEST_NAME
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for name in manifest:
            src = snap / name
            target = dest / name
            target.write_bytes(src.read_bytes())

        for n in uv.REQUIRED_FILES:
            assert (dest / n).read_bytes() == old_bytes[n]
        print("OK: full_install_then_rollback")


def test_snapshot_rotates_previous() -> None:
    """A prior .previous/ must rotate to .previous.1/ on next snapshot."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        dest = td / "vulkan"
        _seed_dest(dest)
        first = uv._snapshot_current(dest)
        second = uv._snapshot_current(dest)
        assert (dest / uv.PREVIOUS_DIRNAME).is_dir()
        assert (dest / f"{uv.PREVIOUS_DIRNAME}.1").is_dir()
        assert first.exists()
        assert second.exists()
        print("OK: snapshot_rotates_previous")


def main() -> int:
    tests = [
        test_install_happy_path,
        test_install_rejects_extras,
        test_install_rejects_missing,
        test_install_rejects_subdir,
        test_size_guard_truncation,
        test_full_install_then_rollback,
        test_snapshot_rotates_previous,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            print(f"FAIL: {t.__name__}: {exc}")
            failed += 1
        except Exception as exc:
            print(f"ERROR: {t.__name__}: {exc!r}")
            failed += 1
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
