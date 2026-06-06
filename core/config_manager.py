"""Detect, read, and modify the Echoes UserPreferences.echoes.ini file."""
from __future__ import annotations

import configparser
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_RELATIVE = Path("Lord of the Rings Online") / "UserPreferences.echoes.ini"

REQUIRED_KEYS = {
    "Fullscreen": "True",
    "ConfineFullScreenMouseCursor": "False",
}


def find_config() -> Path | None:
    """Return the path to UserPreferences.echoes.ini, or None if not found."""
    candidate = Path.home() / "Documents" / CONFIG_RELATIVE
    if candidate.is_file():
        return candidate
    return None


def _make_parser() -> configparser.ConfigParser:
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    parser.optionxform = str
    return parser


def _read_with_fallback(path: Path) -> configparser.ConfigParser:
    encodings = ("utf-8", "utf-8-sig", "cp1252")
    last_exc: Exception | None = None
    for enc in encodings:
        try:
            parser = _make_parser()
            with path.open("r", encoding=enc) as fh:
                parser.read_file(fh)
            return parser
        except (UnicodeDecodeError, configparser.Error, OSError) as exc:
            last_exc = exc
            continue
    raise OSError(f"Could not read config with any supported encoding: {last_exc}")


def read_settings(path: Path) -> configparser.ConfigParser:
    """Read the config file using a tolerant encoding chain."""
    return _read_with_fallback(path)


def read_setting(path: Path, key: str) -> str | None:
    """Return the value for `key` from the first section that has it, else None."""
    try:
        parser = read_settings(path)
    except OSError as exc:
        logger.warning("read_setting failed for %s: %s", path, exc)
        return None
    for section in parser.sections():
        if parser.has_option(section, key):
            return parser.get(section, key, fallback=None)
    return None


def apply_recommended_settings(
    path: Path, resolution: tuple[int, int]
) -> tuple[str, list[str]]:
    """Ensure Fullscreen=True, ConfineFullScreenMouseCursor=False, Resolution=WxH.

    Preserves all other settings. Writes atomically via a temp file. Returns
    the section name and the list of keys written, for callers that want to
    report what changed.
    """
    width, height = resolution
    desired = dict(REQUIRED_KEYS)
    desired["Resolution"] = f"{width}x{height}"

    parser = _read_with_fallback(path)

    target_section = "General"
    if target_section not in parser.sections():
        parser.add_section(target_section)

    for key, value in desired.items():
        parser.set(target_section, key, value)

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as fh:
        parser.write(fh)
    os.replace(tmp_path, path)
    keys = list(desired.keys())
    logger.info(
        "Config updated at %s (section=%s, keys=%s)",
        path,
        target_section,
        keys,
    )
    return target_section, keys
