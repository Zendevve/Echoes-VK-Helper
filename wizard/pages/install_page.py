"""Step 4 - Install progress page.

The install runs in a background thread and pushes events onto a queue. The UI
polls the queue via `after()` and updates widgets only on the main thread.
"""
from __future__ import annotations

import logging
import queue
import threading
import traceback
from typing import TYPE_CHECKING

import customtkinter as ctk

from core.logger import attach_ui_queue, detach_ui_queue
from wizard.controller import (
    ACCENT,
    BG_DARK,
    DANGER,
    SUCCESS,
    SURFACE_HOVER,
    TEXT,
    TEXT_MUTED,
    WizardState,
)
from wizard.pages._common import make_card, make_subtitle, make_title

if TYPE_CHECKING:
    from wizard.controller import WizardController

logger = logging.getLogger(__name__)


class InstallPage(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, controller: "WizardController") -> None:
        super().__init__(parent, fg_color=BG_DARK, corner_radius=0)
        self.controller = controller
        self._q: queue.Queue = queue.Queue()
        self._worker: threading.Thread | None = None
        self._built = False
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.grid_columnconfigure(0, weight=1)

        make_title(header, "Installing").grid(row=0, column=0, sticky="ew", padx=8)
        make_subtitle(
            header,
            "Please wait while the helper applies the changes. This usually takes a few seconds.",
        ).grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 0))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=0)
        body.grid_rowconfigure(1, weight=1)

        progress_card = make_card(body)
        progress_card.grid(row=0, column=0, sticky="ew", padx=8, pady=(0, 8))
        progress_card.grid_columnconfigure(0, weight=1)

        self.step_label = ctk.CTkLabel(
            progress_card,
            text="Preparing...",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=TEXT,
            anchor="w",
        )
        self.step_label.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))

        self.progress = ctk.CTkProgressBar(
            progress_card,
            height=10,
            progress_color=ACCENT,
            fg_color=SURFACE_HOVER,
        )
        self.progress.set(0.0)
        self.progress.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))

        log_card = make_card(body)
        log_card.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(1, weight=1)

        log_title = ctk.CTkLabel(
            log_card,
            text="Live log",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        log_title.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))

        self.log_box = ctk.CTkTextbox(
            log_card,
            fg_color="#101010",
            text_color="#d0d0d0",
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
        )
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))
        self.log_box.configure(state="disabled")

        self._built = True

    def on_enter(self, state: WizardState) -> None:
        if not self._built:
            return
        self.progress.set(0.0)
        self.step_label.configure(text="Preparing...")
        self._clear_log()
        self._start_install()

    def on_exit(self) -> None:
        return None

    def can_advance(self) -> bool:
        return False

    def _clear_log(self) -> None:
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _append_log(self, line: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _start_install(self) -> None:
        attach_ui_queue(self._q)
        self._worker = threading.Thread(target=self._run_install, name="install", daemon=True)
        self._worker.start()
        self.after(120, self._drain)

    def _run_install(self) -> None:
        state = self.controller.context
        state.install_succeeded = False
        try:
            if state.needs_elevation and state.game_path:
                from core.elevation import relaunch_as_admin

                self._q.put(("log", "Game folder is read-only. Requesting elevation..."))
                relaunch_as_admin(state)
                return

            self._run_step_backup(state)
            self._run_step_resolution(state)
            self._run_step_config(state)
            self._run_step_vulkan(state)
            self._run_step_validation(state)
            self._step("Done.", 100)
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc()
            self._q.put(("log", f"ERROR: {exc}"))
            self._q.put(("log", tb))
            self._q.put(("error", exc))

    def _run_step_backup(self, state: WizardState) -> None:
        self._step("Creating backup...", 5)
        if not state.config_path:
            return
        from core.backup_manager import create_backup

        backup = create_backup(state.config_path)
        self._q.put(("log", f"Backup created: {backup}"))
        state.backup_paths.append(str(backup))

    def _run_step_resolution(self, state: WizardState) -> None:
        self._step("Detecting resolution...", 25)
        if state.resolution is not None:
            return
        from core.resolution import get_native_resolution

        state.resolution = get_native_resolution()
        self._q.put(("log", f"Resolution: {state.resolution[0]}x{state.resolution[1]}"))

    def _run_step_config(self, state: WizardState) -> None:
        self._step("Updating configuration...", 40)
        if not state.config_path:
            return
        from core.config_manager import apply_recommended_settings

        apply_recommended_settings(state.config_path, state.resolution)
        self._q.put(("log", "Configuration updated."))

    def _run_step_vulkan(self, state: WizardState) -> None:
        self._step("Installing Vulkan files...", 60)
        if not state.game_path:
            return
        from core.vulkan_installer import (
            VulkanInstallError,
            install_vulkan,
            rollback as vulkan_rollback,
        )

        try:
            result = install_vulkan(state.game_path)
        except VulkanInstallError as exc:
            self._q.put(("log", f"Vulkan install failed: {exc}; rolling back..."))
            vulkan_rollback(exc.result)
            raise
        except Exception as exc:
            self._q.put(("log", f"Vulkan install failed: {exc}"))
            raise

        state.vulkan_install_result = result.__dict__
        self._q.put(("log", "Vulkan files installed."))

    def _run_step_validation(self, state: WizardState) -> None:
        self._step("Running validation...", 90)
        from core.validator import run_validation

        backup_path = None
        if state.config_path:
            from core.backup_manager import list_backups

            backups = list_backups(state.config_path)
            if backups:
                backup_path = backups[0]
        result = run_validation(state.config_path, backup_path, state.game_path)
        state.validation = result.__dict__
        state.install_succeeded = result.all_passed

        for msg in result.failed():
            self._q.put(("log", f"FAILED: {msg}"))

        if not result.all_passed:
            self._q.put(("log", "Validation reported failures. Marking install as failed."))

    def _step(self, label: str, pct: float) -> None:
        self._q.put(("step", label, pct))

    def _drain(self) -> None:
        try:
            while True:
                evt = self._q.get_nowait()
                kind = evt[0]
                if kind == "log":
                    self._append_log(evt[1])
                elif kind == "step":
                    _, label, pct = evt
                    self.step_label.configure(text=label)
                    self.progress.set(pct / 100.0)
                elif kind == "done":
                    self._finish(success=True)
                    return
                elif kind == "error":
                    self._finish(success=False)
                    return
        except queue.Empty:
            pass

        if self._worker and self._worker.is_alive():
            self.after(120, self._drain)
        else:
            self._finish(success=self.controller.context.install_succeeded)

    def _finish(self, success: bool) -> None:
        detach_ui_queue()
        self.controller.context.install_succeeded = bool(success)
        self.step_label.configure(
            text="Complete" if success else "Completed with errors",
            text_color=SUCCESS if success else DANGER,
        )
        self.progress.set(1.0)
        self.controller.after(600, lambda: self.controller.go_to("completion"))
