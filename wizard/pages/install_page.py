"""Step 4 - Install progress page.

The install runs in a background thread and pushes events onto a queue. The UI
polls the queue via `after()` and updates widgets only on the main thread.

The progress + live log render inside the system's single dark surface to echo
the hero TUI mockup from the welcome page. The dark surface is reserved for
these two moments only.
"""
from __future__ import annotations

import logging
import queue
import threading
import time
import traceback
from typing import TYPE_CHECKING

import customtkinter as ctk

from core.logger import attach_ui_queue, detach_ui_queue
from wizard.controller import (
    BUTTON_MD,
    CANVAS,
    DANGER,
    HAIRLINE,
    INK,
    INK_DEEP,
    MUTE,
    ON_DARK,
    ON_PRIMARY,
    SUCCESS,
    SURFACE_DARK,
    SURFACE_DARK_ELEVATED,
    SURFACE_SOFT,
    WizardState,
    font,
    heading_font,
)
from wizard.pages._common import (
    MARK_FAIL,
    MARK_OK,
    MARK_PENDING,
    make_dark_card,
    make_hairline,
    make_primary_button,
    make_section_label,
    make_subtitle,
)

if TYPE_CHECKING:
    from wizard.controller import WizardController

logger = logging.getLogger(__name__)

WATCHDOG_SECONDS = 60.0
POLL_INTERVAL_MS = 120


class InstallAborted(Exception):
    """Raised by install steps when the user requests an abort."""


class InstallPage(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, controller: "WizardController") -> None:
        super().__init__(parent, fg_color=CANVAS, corner_radius=0)
        self.controller = controller
        self._q: queue.Queue = queue.Queue()
        self._worker: threading.Thread | None = None
        self._built = False
        self._abort_event = threading.Event()
        self._watchdog_after: str | None = None
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        self._build_header(self)
        self._build_body(self)

        self._built = True

    def _build_header(self, parent: ctk.CTkFrame) -> None:
        header = ctk.CTkFrame(parent, fg_color=CANVAS, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 8))
        header.grid_columnconfigure(0, weight=1)

        self._section_lbl = make_section_label(header, "[?]  Installing")
        self._section_lbl.grid(row=0, column=0, sticky="ew")
        make_hairline(header).grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self._header_subtitle = make_subtitle(
            header,
            "Please wait while the helper applies the changes. This usually takes a few seconds.",
        )
        self._header_subtitle.grid(row=2, column=0, sticky="ew", pady=(8, 0))

    def _build_body(self, parent: ctk.CTkFrame) -> None:
        body = ctk.CTkFrame(parent, fg_color=CANVAS, corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=8)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=0)
        body.grid_rowconfigure(1, weight=1)

        progress_card = ctk.CTkFrame(
            body,
            fg_color=CANVAS,
            corner_radius=0,
            border_width=1,
            border_color=HAIRLINE,
        )
        progress_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        progress_card.grid_columnconfigure(0, weight=1)

        self.step_label = ctk.CTkLabel(
            progress_card,
            text="[...]  preparing",
            font=heading_font(size=15),
            text_color=INK,
            anchor="w",
        )
        self.step_label.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))

        progress_track = ctk.CTkFrame(
            progress_card,
            fg_color=SURFACE_SOFT,
            corner_radius=4,
            height=10,
        )
        progress_track.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))

        self.progress = ctk.CTkProgressBar(
            progress_track,
            height=10,
            progress_color=INK,
            fg_color=SURFACE_SOFT,
        )
        self.progress.set(0.0)
        self.progress.pack(fill="x", expand=True, padx=0, pady=0)

        self._start_btn = make_primary_button(
            progress_card, "Start install  >", self._on_start_clicked
        )
        self._start_btn.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))

        log_card = make_dark_card(body)
        log_card.grid(row=1, column=0, sticky="nsew", pady=(0, 0))
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(1, weight=1)

        log_title = ctk.CTkLabel(
            log_card,
            text="$ live log",
            font=heading_font(size=13),
            text_color=ON_DARK,
            anchor="w",
        )
        log_title.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 6))

        log_divider = ctk.CTkFrame(log_card, fg_color=SURFACE_DARK_ELEVATED, height=1, corner_radius=0)
        log_divider.grid(row=0, column=0, sticky="sew", padx=20)

        self.log_box = ctk.CTkTextbox(
            log_card,
            fg_color=SURFACE_DARK,
            text_color="#d0d0d0",
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
        )
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.log_box.configure(state="disabled")

    def on_enter(self, state: WizardState) -> None:
        if not self._built:
            return
        from wizard.anim import fade_in_labels
        fade_in_labels([self._section_lbl, self._header_subtitle])
        self._abort_event.clear()
        self.progress.set(0.0)
        self.step_label.configure(text="Ready to install", text_color=MUTE)
        self._clear_log()
        self._start_btn.grid()

    def _on_start_clicked(self) -> None:
        self._start_btn.grid_forget()
        self.step_label.configure(text="[...]  preparing", text_color=INK)
        self._schedule_watchdog()
        self._start_install()

    def on_exit(self) -> None:
        if self._watchdog_after is not None:
            try:
                self.after_cancel(self._watchdog_after)
            except Exception:
                pass
            self._watchdog_after = None

    def can_advance(self) -> bool:
        return False

    def request_abort(self) -> None:
        self._append_log("[x] abort requested by user. rolling back...")
        self._abort_event.set()
        self.step_label.configure(text="[...]  aborting", text_color=DANGER)

    def _clear_log(self) -> None:
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _append_log(self, line: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _schedule_watchdog(self) -> None:
        if self._watchdog_after is not None:
            try:
                self.after_cancel(self._watchdog_after)
            except Exception:
                pass
        self._watchdog_after = self.after(
            int(WATCHDOG_SECONDS * 1000), self._watchdog_tick
        )

    def _watchdog_tick(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            self._append_log(
                f"[!] install has been running for over {int(WATCHDOG_SECONDS)}s."
            )
            self._append_log("    click Abort to stop, or wait for it to finish.")
            self._watchdog_after = self.after(
                int(WATCHDOG_SECONDS * 1000), self._watchdog_tick
            )

    def _start_install(self) -> None:
        attach_ui_queue(self._q)
        self._worker = threading.Thread(target=self._run_install, name="install", daemon=True)
        self._worker.start()
        self.after(POLL_INTERVAL_MS, self._drain)

    def _check_abort(self) -> None:
        if self._abort_event.is_set():
            raise InstallAborted("User aborted the installation.")

    def _run_install(self) -> None:
        state = self.controller.context
        state.install_succeeded = False
        state.aborted = False
        try:
            if state.needs_elevation and state.game_path:
                from core.elevation import relaunch_as_admin

                self._q.put(("log", "[!] game folder is read-only. restarting as administrator..."))
                state._resume_install = True
                relaunch_as_admin(state)
                return

            self._check_abort()
            self._run_step_backup(state)
            self._check_abort()
            self._run_step_resolution(state)
            self._check_abort()
            self._run_step_config(state)
            self._check_abort()
            self._run_step_vulkan(state)
            self._check_abort()
            self._run_step_validation(state)
            self._step("[x]  done.", 100)
            self._q.put(("done",))
        except InstallAborted as exc:
            state.aborted = True
            self._q.put(("log", f"[x] aborted: {exc}"))
            self._q.put(("aborted",))
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc()
            self._q.put(("log", f"[x] error: {exc}"))
            self._q.put(("log", tb))
            self._q.put(("error", exc))

    def _run_step_backup(self, state: WizardState) -> None:
        self._step("[...]  creating backup", 5)
        if not state.config_path:
            return
        from core.backup_manager import create_backup

        backup = create_backup(state.config_path)
        self._q.put(("log", f"[+] backup created: {backup}"))
        state.backup_paths.append(str(backup))

    def _run_step_resolution(self, state: WizardState) -> None:
        self._step("[...]  detecting resolution", 25)
        if state.resolution is not None:
            return
        from core.resolution import get_native_resolution

        state.resolution = get_native_resolution()
        self._q.put(("log", f"[+] resolution: {state.resolution[0]}x{state.resolution[1]}"))

    def _run_step_config(self, state: WizardState) -> None:
        self._step("[...]  updating configuration", 40)
        if not state.config_path:
            return
        from core.config_manager import apply_recommended_settings

        apply_recommended_settings(state.config_path, state.resolution)
        self._q.put(("log", "[+] configuration updated."))

    def _run_step_vulkan(self, state: WizardState) -> None:
        self._step("[...]  installing vulkan files", 60)
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
            self._q.put(("log", f"[x] vulkan install failed: {exc}; rolling back..."))
            vulkan_rollback(exc.result)
            raise
        except Exception as exc:
            self._q.put(("log", f"[x] vulkan install failed: {exc}"))
            raise

        state.vulkan_install_result = result.__dict__
        self._q.put(("log", "[+] vulkan files installed."))

    def _run_step_validation(self, state: WizardState) -> None:
        self._step("[...]  running validation", 90)
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
            self._q.put(("log", f"[x] failed: {msg}"))

        if not result.all_passed:
            self._q.put(("log", "[!] validation reported failures. marking install as failed."))

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
                elif kind == "aborted":
                    self._finish(success=False, aborted=True)
                    return
                elif kind == "error":
                    self._finish(success=False)
                    return
        except queue.Empty:
            pass

        if self._worker and self._worker.is_alive():
            self.after(POLL_INTERVAL_MS, self._drain)
        else:
            self._finish(success=self.controller.context.install_succeeded)

    def _finish(self, success: bool, aborted: bool = False) -> None:
        detach_ui_queue()
        if self._watchdog_after is not None:
            try:
                self.after_cancel(self._watchdog_after)
            except Exception:
                pass
            self._watchdog_after = None
        self.controller.context.install_succeeded = bool(success)
        if aborted:
            self.step_label.configure(text="[x]  aborted", text_color=DANGER)
            self.progress.set(0.0)
        else:
            self.step_label.configure(
                text="[x]  complete" if success else "[x]  completed with errors",
                text_color=INK if success else DANGER,
            )
            self.progress.set(1.0)

        next_btn = self.controller._next_btn
        next_btn.configure(
            state="normal",
            text="View results  >",
            fg_color=INK,
            hover_color=INK,
            text_color=ON_PRIMARY,
            font=font(size=BUTTON_MD, weight="bold"),
        )
        from wizard.pages._common import update_button_motion
        update_button_motion(next_btn, base=INK,
                             hover=INK_DEEP, active=INK_DEEP)
