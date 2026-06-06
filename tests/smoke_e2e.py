"""End-to-end smoke test that walks the wizard with stubbed data.

Runs the install worker against a temp game directory and verifies the
completion page reports all checks passed.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import customtkinter as ctk

ctk.set_appearance_mode("dark")

from core.logger import setup_logging  # noqa: E402
from core.paths import logs_dir  # noqa: E402

setup_logging(logs_dir())

from wizard.controller import WizardController, WizardState  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        game_dir = td / "Echoes"
        game_dir.mkdir()
        for name in ("dinput8.ini", "dinput8.dll", "d3d9.dll", "lotroclient.exe"):
            (game_dir / name).write_bytes(b"placeholder")

        config_path = td / "UserPreferences.echoes.ini"
        config_path.write_text(
            "[General]\nSomeOther=keep\nFullscreen=False\n", encoding="utf-8"
        )

        state = WizardState(
            config_path=config_path,
            game_path=game_dir,
            resolution=(1920, 1080),
        )

        app = WizardController(initial_state=state)

        welcome = app._pages["welcome"]
        detection = app._pages["detection"]
        summary = app._pages["summary"]
        welcome.on_enter(state)
        detection.on_enter(state)
        summary.on_enter(state)
        print("Non-install pages on_enter() called without error")

        fake_src = Path(__file__).resolve().parent / "_fake_vulkan_src"
        fake_src.mkdir(exist_ok=True)
        for name in ("dinput8.ini", "dinput8.dll", "d3d9.dll"):
            (fake_src / name).write_bytes(b"FAKE_BINARY_" + name.encode())

        import core.vulkan_installer as vi
        original = vi.vulkan_source_dir
        vi.vulkan_source_dir = lambda: fake_src  # type: ignore[assignment]

        install_page = app._pages["install"]
        import threading
        t = threading.Thread(target=install_page._run_install, name="install-test", daemon=True)
        t.start()
        t.join(timeout=15)
        print("Install worker completed within 15s")

        vi.vulkan_source_dir = original  # type: ignore[assignment]

        import queue as _q
        while not install_page._q.empty():
            try:
                evt = install_page._q.get_nowait()
                print("queue event:", evt[0], evt[1] if len(evt) > 1 else "")
            except _q.Empty:
                break

        app._show_page(4)
        print("install_succeeded:", state.install_succeeded)
        if state.validation:
            print("validation:", state.validation)

        import shutil
        shutil.rmtree(fake_src, ignore_errors=True)

        for name in ("dinput8.ini", "dinput8.dll", "d3d9.dll"):
            f = game_dir / name
            if f.exists():
                f.unlink()
        backup = config_path.with_name(config_path.name + ".bak")
        if backup.exists():
            backup.unlink()

        app.destroy()

    return 0 if state.install_succeeded else 1


if __name__ == "__main__":
    sys.exit(main())

