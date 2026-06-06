"""Locate the Echoes of Angmar install (lotroclient.exe) on the local filesystem."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

EXE_NAME = "lotroclient.exe"

_REGISTRY_HINTS: tuple[tuple[str, str], ...] = (
    (r"SOFTWARE\StandingStoneGames\LOTRO", "InstallLocation"),
    (r"SOFTWARE\WOW6432Node\StandingStoneGames\LOTRO", "InstallLocation"),
    (r"SOFTWARE\Valve\Steam", "SteamPath"),
)

_CUSTOM_PATHS: tuple[Path, ...] = (
    Path("D:/Games"),
    Path("C:/Games"),
    Path("E:/Games"),
    Path("C:/LOTRO"),
    Path("D:/LOTRO"),
)


def is_writable(path: Path) -> bool:
    """Return True if we can create+delete a tiny test file under `path`."""
    if not path.exists() or not path.is_dir():
        return False
    if not os.access(path, os.W_OK):
        return False
    probe = path / ".evh_write_test"
    try:
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def _read_registry_value(subkey: str, value_name: str) -> str | None:
    """Read a string value from HKLM. Returns None on any failure."""
    try:
        import winreg  # type: ignore[import-not-found]

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey) as hkey:
            value, _ = winreg.QueryValueEx(hkey, value_name)
            return str(value) if value else None
    except (OSError, ImportError):
        return None


def _registry_install_paths() -> list[Path]:
    paths: list[Path] = []
    for subkey, value_name in _REGISTRY_HINTS:
        v = _read_registry_value(subkey, value_name)
        if not v:
            continue
        p = Path(v)
        if p.is_dir():
            paths.append(p)
    return paths


def _walk_for_exe(root: Path, max_depth: int = 4) -> Path | None:
    """Depth-limited directory walk that returns the first folder containing the EXE."""
    if not root.is_dir():
        return None
    try:
        for current, dirs, files in os.walk(root):
            rel = Path(current).relative_to(root)
            depth = len(rel.parts)
            if depth > max_depth:
                dirs[:] = []
                continue
            if EXE_NAME in files:
                return Path(current)
    except OSError as exc:
        logger.debug("Walk failed for %s: %s", root, exc)
    return None


def search_steam_libraries() -> list[Path]:
    """Return Steam library root folders by parsing libraryfolders.vdf.

    Also looks in the well-known Steam install paths. Skips any that fail to parse.
    """
    candidates: list[Path] = []
    for subkey, value_name in _REGISTRY_HINTS:
        if "Steam" not in subkey:
            continue
        v = _read_registry_value(subkey, value_name)
        if v:
            candidates.append(Path(v) / "steamapps")

    candidates.extend(
        [
            Path(r"C:\Program Files (x86)\Steam\steamapps"),
            Path(r"D:\Steam\steamapps"),
            Path(r"C:\Steam\steamapps"),
        ]
    )

    library_roots: list[Path] = []
    for steamapps in candidates:
        if not steamapps.is_dir():
            continue
        library_roots.append(steamapps)
        vdf = steamapps / "libraryfolders.vdf"
        if vdf.is_file():
            try:
                content = vdf.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for match in re.finditer(r'"path"\s+"([^"]+)"', content):
                library_roots.append(Path(match.group(1)) / "steamapps")
    return library_roots


def _candidate_roots() -> list[Path]:
    roots: list[Path] = []
    roots.extend(_registry_install_paths())
    roots.extend(search_steam_libraries())

    for parent in (
        Path("C:/Program Files"),
        Path("C:/Program Files (x86)"),
        Path("D:/Program Files"),
        Path("D:/Program Files (x86)"),
    ):
        if parent.is_dir():
            for child in parent.iterdir():
                name = child.name.lower()
                if any(token in name for token in ("echoes", "lotro", "turbine", "standingstone")):
                    roots.append(child)

    for custom in _CUSTOM_PATHS:
        if custom.is_dir():
            for child in custom.iterdir():
                name = child.name.lower()
                if any(token in name for token in ("echoes", "lotro")):
                    roots.append(child)
            roots.append(custom)

    seen: set[Path] = set()
    unique: list[Path] = []
    for r in roots:
        try:
            key = r.resolve()
        except OSError:
            key = r
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    return unique


def find_game_installation() -> Path | None:
    """Return the folder containing lotroclient.exe, or None if not found."""
    for root in _candidate_roots():
        logger.debug("Searching for %s under %s", EXE_NAME, root)
        hit = _walk_for_exe(root)
        if hit:
            logger.info("Found game at %s", hit)
            return hit
    return None
