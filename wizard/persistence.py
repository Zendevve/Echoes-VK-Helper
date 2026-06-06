"""Persistent wizard state across runs.

Stores the last-known good config and game paths in a JSON file under
``%LOCALAPPDATA%\\EchoesVKHelper\\state.json`` (falls back to ``%APPDATA%`` when
``LOCALAPPDATA`` is not set). The wizard reloads these on startup so the user
does not have to re-browse on every run.

The on-disk schema is intentionally minimal and versioned:

    {
        "version": 1,
        "config_path": "C:\\\\Users\\\\...\\\\UserPreferences.echoes.ini",
        "game_path":   "D:\\\\Games\\\\Echoes of Angmar"
    }

Failures (missing file, malformed JSON, permission errors) are non-fatal; the
wizard simply falls back to re-running auto-detection.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from wizard.controller import WizardState

logger = logging.getLogger(__name__)

APP_DIRNAME = "EchoesVKHelper"
STATE_FILENAME = "state.json"
STATE_VERSION = 1


def _state_path() -> Path:
    """Return the absolute path of the on-disk state file."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if not base:
        base = str(Path.home() / "AppData" / "Local")
    return Path(base) / APP_DIRNAME / STATE_FILENAME


def load_state() -> dict[str, Any]:
    """Return the persisted state as a dict, or ``{}`` on any failure."""
    path = _state_path()
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read state file %s: %s", path, exc)
        return {}
    if not isinstance(data, dict):
        logger.warning("State file %s has unexpected type %s", path, type(data).__name__)
        return {}
    return data


def save_state(context: WizardState) -> bool:
    """Persist the paths from ``context`` to disk. Returns True on success."""
    payload: dict[str, Any] = {
        "version": STATE_VERSION,
        "config_path": str(context.config_path) if context.config_path else None,
        "game_path": str(context.game_path) if context.game_path else None,
        "resolution": list(context.resolution) if context.resolution else None,
    }
    path = _state_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp, path)
    except OSError as exc:
        logger.warning("Could not write state file %s: %s", path, exc)
        return False
    return True


def apply_to_context(context: WizardState, data: dict[str, Any]) -> None:
    """Populate ``context`` with persisted paths if they still exist on disk.

    Paths that no longer exist are dropped silently so auto-detection runs as
    normal.
    """
    cfg_raw = data.get("config_path")
    game_raw = data.get("game_path")
    res_raw = data.get("resolution")

    if isinstance(cfg_raw, str) and cfg_raw:
        cfg = Path(cfg_raw)
        if cfg.is_file():
            context.config_path = cfg
            logger.info("Restored config_path: %s", cfg)
        else:
            logger.info("Persisted config_path no longer exists: %s", cfg)

    if isinstance(game_raw, str) and game_raw:
        game = Path(game_raw)
        if game.is_dir():
            context.game_path = game
            logger.info("Restored game_path: %s", game)
        else:
            logger.info("Persisted game_path no longer exists: %s", game)

    if (
        isinstance(res_raw, list)
        and len(res_raw) == 2
        and all(isinstance(x, int) and x > 0 for x in res_raw)
    ):
        context.resolution = (res_raw[0], res_raw[1])
        logger.info("Restored resolution: %s", context.resolution)
