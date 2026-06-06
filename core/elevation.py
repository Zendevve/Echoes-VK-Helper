"""UAC elevation: relaunch the helper with admin rights while preserving state."""
from __future__ import annotations

import contextlib
import ctypes
import json
import logging
import os
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _state_to_dict(state: Any) -> dict[str, Any]:
    if is_dataclass(state):
        raw = asdict(state)
    elif hasattr(state, "__dict__"):
        raw = dict(state.__dict__)
    else:
        raw = dict(state)
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if isinstance(v, Path):
            out[k] = str(v)
        elif isinstance(v, tuple):
            out[k] = list(v)
        else:
            out[k] = v
    return out


def save_resume_state(state: Any, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _state_to_dict(state)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Saved resume state to %s", path)
    return path


def load_resume_state(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load resume state: %s", exc)
        return None


def relaunch_as_admin(state: Any) -> None:
    """Persist state, ask UAC to relaunch us elevated, then exit this process.

    Mutates `state` to mark the elevation attempt so the spawned process does
    not loop. Unlinks the temp state file if the UAC prompt was cancelled.
    """
    from core.paths import temp_state_path

    state_path = temp_state_path()

    if is_dataclass(state):
        state.needs_elevation = False
        state._elevated_attempted = True
    elif isinstance(state, dict):
        state["needs_elevation"] = False
        state["_elevated_attempted"] = True
    else:
        try:
            state.needs_elevation = False
            state._elevated_attempted = True
        except AttributeError:
            pass

    save_resume_state(state, state_path)

    if getattr(sys, "frozen", False):
        exe = sys.executable
        params = f'--resume="{state_path}"'
    else:
        exe = sys.executable
        script = str(Path(__file__).resolve().parent.parent / "app.py")
        params = f'"{script}" --resume="{state_path}"'

    logger.info("Requesting UAC elevation: %s %s", exe, params)

    sw_shownormal = 1
    rc = int(ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        exe,
        params,
        None,
        sw_shownormal,
    ))
    if rc <= 32 or rc == 1223:
        logger.error("ShellExecuteW failed or cancelled with code %s", rc)
        with contextlib.suppress(OSError):
            state_path.unlink(missing_ok=True)
        if rc == 1223:
            raise OSError("UAC elevation was cancelled by the user.")
        raise OSError(f"Could not relaunch elevated (ShellExecuteW returned {rc}).")

    os._exit(0)


def consume_resume_argv() -> Path | None:
    """Inspect sys.argv for --resume=... and return the state path if present."""
    for arg in sys.argv[1:]:
        if arg.startswith("--resume="):
            return Path(arg.split("=", 1)[1].strip('"'))
    return None
