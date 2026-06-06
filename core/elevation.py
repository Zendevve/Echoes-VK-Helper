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


def _validate_resume_path(state_path: Path) -> None:
    """Ensure the resume state path is safe to embed in a command line.

    The path must resolve under the system TEMP directory and contain no
    characters that would break lpParameters parsing (quotes, newlines,
    tabs). Without these checks a malformed temp_state_path() (or an
    attacker who can write to %TEMP%) could inject extra arguments into
    the elevated process's command line.
    """
    state_str = str(state_path)
    if len(state_str) > 1024:
        raise ValueError(f"Resume state path too long: {len(state_str)} bytes")
    for bad in ('"', "'", "\r", "\n", "\t", "\0"):
        if bad in state_str:
            raise ValueError(
                f"Resume state path contains unsafe character {bad!r}: {state_str!r}"
            )
    temp_root = (
        Path(os.environ.get("TEMP"))
        or Path(os.environ.get("TMP"))
        or Path.home()
    )
    try:
        state_path.resolve().relative_to(temp_root.resolve())
    except (ValueError, OSError) as exc:
        raise ValueError(
            f"Resume state path {state_path} is not under TEMP ({temp_root}): {exc}"
        ) from exc


def _build_resume_params(state_path: Path, script: Path | None) -> str:
    """Build the lpParameters string for ShellExecuteW.

    Wraps the path in double quotes so paths with spaces survive. The
    caller must have validated both `state_path` and `script` via
    _validate_resume_path; this helper trusts that the inputs contain
    no embedded quotes.
    """
    resume_arg = f'--resume="{state_path}"'
    if script is None:
        return resume_arg
    return f'"{script}" {resume_arg}'


def relaunch_as_admin(state: Any) -> None:
    """Persist state, ask UAC to relaunch us elevated, then exit this process.

    Mutates `state` to mark the elevation attempt so the spawned process does
    not loop. Unlinks the temp state file if the UAC prompt was cancelled.
    """
    from core.paths import temp_state_path

    state_path = temp_state_path()
    _validate_resume_path(state_path)

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

    exe = sys.executable
    if getattr(sys, "frozen", False):
        params = _build_resume_params(state_path, None)
    else:
        script = Path(__file__).resolve().parent.parent / "app.py"
        _validate_resume_path(script)
        params = _build_resume_params(state_path, script)

    logger.info("Requesting UAC elevation: %s %s", exe, params)

    sw_shownormal = 1
    rc = int(
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            exe,
            params,
            None,
            sw_shownormal,
        )
    )
    # Per MSDN: ShellExecuteW returns > 32 on success. 1223 means the user
    # dismissed the UAC dialog (not an error, but nothing was launched).
    # 0..32 are real errors. Treat 1223 as a distinct outcome so the caller
    # can show a different message.
    if rc == 1223:
        logger.info("UAC elevation cancelled by user (rc=1223)")
        with contextlib.suppress(OSError):
            state_path.unlink(missing_ok=True)
        raise OSError("UAC elevation was cancelled by the user.")
    if rc <= 32:
        logger.error("ShellExecuteW failed with code %s", rc)
        with contextlib.suppress(OSError):
            state_path.unlink(missing_ok=True)
        raise OSError(f"Could not relaunch elevated (ShellExecuteW returned {rc}).")

    os._exit(0)


def consume_resume_argv() -> Path | None:
    """Inspect sys.argv for --resume=... and return the state path if present.

    The Windows CRT strips the outer quotes we added in _build_resume_params
    when constructing argv, so the value is already de-quoted. We do not
    recursively strip quotes because _validate_resume_path rejects paths
    with embedded quote characters, so a single layer is the correct max.
    """
    for arg in sys.argv[1:]:
        if arg.startswith("--resume="):
            return Path(arg.split("=", 1)[1])
    return None
