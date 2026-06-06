"""Echoes Vulkan Helper - entry point."""

from __future__ import annotations

import contextlib
import logging
import sys
import traceback
from pathlib import Path

from core import __app_name__, __version__
from core.elevation import consume_resume_argv, load_resume_state
from core.logger import setup_logging
from core.paths import assert_vulkan_assets_present, logs_dir

logger = logging.getLogger(__name__)


def _hydrate_state_from_resume() -> dict | None:
    resume_path = consume_resume_argv()
    if not resume_path:
        return None
    data = load_resume_state(resume_path)
    if not data:
        return None
    with contextlib.suppress(OSError):
        resume_path.unlink()
    return data


def _show_fatal_dialog(message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Echoes Vulkan Helper", message)
        root.destroy()
    except Exception:
        print(message, file=sys.stderr)


def _check_assets_or_warn() -> bool:
    missing = assert_vulkan_assets_present()
    if not missing:
        return True
    msg = (
        "Vulkan binaries are missing from the installation.\n\n"
        "Expected files in assets/vulkan/:\n  - " + "\n  - ".join(missing) + "\n\n"
        "Please reinstall the helper or restore the missing files."
    )
    logger.error(msg)
    _show_fatal_dialog(msg)
    return False


def _safe_setup_logging() -> None:
    try:
        setup_logging(logs_dir())
    except Exception as exc:
        try:
            setup_logging(Path.cwd() / "logs")
        except Exception as exc2:
            print(f"Logging init failed: {exc} / {exc2}", file=sys.stderr)


def main() -> int:
    _safe_setup_logging()
    logger.info("=== %s v%s started ===", __app_name__, __version__)

    if not _check_assets_or_warn():
        return 2

    try:
        from wizard.controller import WizardController, WizardState

        state_kwargs = _hydrate_state_from_resume() or {}
        initial_state = WizardState(**state_kwargs)

        app = WizardController(initial_state=initial_state)
        app.mainloop()
        logger.info("=== %s v%s exited cleanly ===", __app_name__, __version__)
        return 0
    except Exception:
        tb = traceback.format_exc()
        logger.exception("Fatal error in main loop: %s", tb)
        _show_fatal_dialog(
            "An unexpected error occurred. The helper will now close.\n\n"
            "Logs are saved in:\n" + str(logs_dir())
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
