"""Resource path resolution for dev runs and PyInstaller --onefile builds."""
from __future__ import annotations

import logging
import os
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

APP_NAME = "EchoesVulkanHelper"

ASSET_VULKAN_FILES = ("dinput8.ini", "dinput8.dll", "d3d9.dll")


def is_frozen() -> bool:
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def project_root() -> Path:
    """Root of the source tree (used in dev runs)."""
    return Path(__file__).resolve().parent.parent


def bundle_root() -> Path:
    """Root inside a PyInstaller bundle."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))
    return project_root()


def resource_path(relative: str) -> Path:
    """Resolve a bundled asset to an absolute path.

    Works in both dev (`python app.py`) and frozen (`EchoesVulkanHelper.exe`).
    """
    return bundle_root() / relative


def _safe_mkdir(path: Path) -> Path | None:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError as exc:
        logger.warning("Could not create %s: %s", path, exc)
        return None


def user_data_dir() -> Path:
    """Per-user data directory for logs/state.

    Falls back to %TEMP%/APP_NAME then EXE directory if all of %APPDATA% are
    unavailable. Failures on expected, handled candidates (e.g. non-writable
    EXE-dir) are logged at DEBUG to avoid polluting the user log on every
    startup.
    """
    if is_frozen():
        candidates = [
            Path.home() / "AppData" / "Local" / APP_NAME,
            Path(tempfile.gettempdir()) / APP_NAME,
        ]
        try:
            # EXE-dir is demoted to last: on a non-writable install (e.g. under
            # Program Files) it always fails, so it's an expected, handled path.
            exe_dir = Path(sys.executable).resolve().parent
            candidates.append(exe_dir / APP_NAME)
        except OSError:
            pass
    else:
        candidates = [project_root()]

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError as exc:
            logger.debug("Skipping data dir candidate %s: %s", candidate, exc)

    fallback = Path(tempfile.gettempdir()) / APP_NAME
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _safe_mkdir(path: Path) -> Path | None:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError as exc:
        logger.warning("Could not create %s: %s", path, exc)
        return None


def logs_dir() -> Path:
    d = user_data_dir() / "logs"
    _safe_mkdir(d)
    return d


def temp_state_path() -> Path:
    return Path(tempfile.gettempdir()) / f"{APP_NAME}_state.json"


def assert_vulkan_assets_present() -> list[str]:
    """Return the list of missing Vulkan asset filenames. Empty = all present."""
    vulkan_dir = resource_path("assets" + os.sep + "vulkan")
    missing: list[str] = []
    if not vulkan_dir.exists():
        return list(ASSET_VULKAN_FILES)
    for name in ASSET_VULKAN_FILES:
        if not (vulkan_dir / name).exists():
            missing.append(name)
    return missing
