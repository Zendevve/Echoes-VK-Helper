"""Step 1 - Welcome page."""
from __future__ import annotations

import configparser
import logging
import queue
import shutil
import threading
from pathlib import Path
from tkinter import filedialog
from typing import TYPE_CHECKING

import customtkinter as ctk

from core.backup_manager import create_backup
from core.gpu_check import check_gpu
from wizard.controller import (
    ACCENT,
    BG_DARK,
    DANGER,
    SUCCESS,
    SURFACE,
    SURFACE_HOVER,
    TEXT,
    TEXT_MUTED,
)
from wizard.pages._common import make_subtitle, make_title

if TYPE_CHECKING:
    from wizard.controller import WizardController, WizardState

logger = logging.getLogger(__name__)

CONFIG_RELATIVE = Path("Lord of the Rings Online") / "UserPreferences.echoes.ini"


class WelcomePage(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, controller: "WizardController") -> None:
        super().__init__(parent, fg_color=BG_DARK, corner_radius=0)
        self.controller = controller
        self._gpu_q: queue.Queue = queue.Queue()
        self._gpu_worker: threading.Thread | None = None
        self._tools_expanded = False
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        body = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        body.grid(row=0, column=0, sticky="nsew", pady=(20, 0))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=0)
        body.grid_rowconfigure(1, weight=0)
        body.grid_rowconfigure(2, weight=0)
        body.grid_rowconfigure(3, weight=1)

        title = make_title(body, "Echoes Vulkan Helper")
        title.grid(row=0, column=0, sticky="ew", padx=8, pady=(0, 8))

        intro = make_subtitle(
            body,
            "This wizard will configure LOTRO: Echoes of Angmar with the recommended "
            "Vulkan compatibility layer in a few clicks.",
        )
        intro.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 16))

        self._gpu_card, self._gpu_status, self._gpu_name_lbl = self._build_gpu_card(body)
        self._gpu_card.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 12))

        checks = ctk.CTkFrame(body, fg_color=SURFACE, corner_radius=12)
        checks.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))
        checks.grid_columnconfigure(0, weight=1)

        self._step_labels: list[ctk.CTkLabel] = []
        self._step_marks: list[ctk.CTkLabel] = []
        step_texts = [
            "Detect your configuration and game folder",
            "Review the changes that will be made",
            "Create automatic backups of your files",
            "Install Vulkan compatibility files",
            "Verify the installation",
        ]
        for i, text in enumerate(step_texts):
            row = ctk.CTkFrame(checks, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", padx=20, pady=10)
            row.grid_columnconfigure(0, weight=0)
            row.grid_columnconfigure(1, weight=1)
            mark = ctk.CTkLabel(
                row,
                text="\u2022",
                font=ctk.CTkFont(size=18),
                text_color=TEXT_MUTED,
                width=20,
            )
            mark.grid(row=0, column=0, padx=(0, 12))
            lbl = ctk.CTkLabel(
                row,
                text=text,
                font=ctk.CTkFont(size=15),
                text_color=TEXT,
                anchor="w",
            )
            lbl.grid(row=0, column=1, sticky="ew")
            self._step_labels.append(lbl)
            self._step_marks.append(mark)

        reassurance = ctk.CTkLabel(
            body,
            text="No existing files will be deleted. Backups are created automatically.",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_MUTED,
        )
        reassurance.grid(row=4, column=0, sticky="ew", padx=8, pady=(8, 0))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_columnconfigure(1, weight=0)

        self._tools_toggle = ctk.CTkButton(
            footer,
            text="Troubleshoot \u25BE",
            fg_color="transparent",
            hover_color=SURFACE_HOVER,
            text_color=TEXT_MUTED,
            width=200,
            height=32,
            command=self._toggle_tools,
        )
        self._tools_toggle.grid(row=0, column=0, sticky="w", padx=8)

        self._tools_panel = ctk.CTkFrame(footer, fg_color="transparent")
        self._tools_panel.grid_columnconfigure(0, weight=1)
        self._tools_panel.grid_columnconfigure(1, weight=1)

        restore_link = ctk.CTkButton(
            self._tools_panel,
            text="Restore from a previous backup",
            fg_color=SURFACE_HOVER,
            hover_color="#4a4a4a",
            text_color=TEXT,
            height=36,
            command=self._on_restore_clicked,
        )
        restore_link.grid(row=0, column=0, sticky="ew", padx=4, pady=4)

        uninstall_link = ctk.CTkButton(
            self._tools_panel,
            text="Uninstall Vulkan helper",
            fg_color=SURFACE_HOVER,
            hover_color="#4a4a4a",
            text_color=TEXT,
            height=36,
            command=self._on_uninstall_clicked,
        )
        uninstall_link.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

    def _toggle_tools(self) -> None:
        self._tools_expanded = not self._tools_expanded
        if self._tools_expanded:
            self._tools_panel.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 0))
            self._tools_toggle.configure(text="Troubleshoot \u25B4")
        else:
            self._tools_panel.grid_forget()
            self._tools_toggle.configure(text="Troubleshoot \u25BE")

    def _mark_step_done(self, index: int) -> None:
        if 0 <= index < len(self._step_marks):
            self._step_marks[index].configure(text="\u2713", text_color=SUCCESS)

    def _build_gpu_card(
        self, parent: ctk.CTkFrame
    ) -> tuple[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkLabel]:
        card = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=12)
        card.grid_columnconfigure(1, weight=1)

        status = ctk.CTkLabel(
            card,
            text="Checking...",
            width=120,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_MUTED,
        )
        status.grid(row=0, column=0, rowspan=2, padx=(16, 12), pady=14)

        title_lbl = ctk.CTkLabel(
            card,
            text="Graphics adapter",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=TEXT,
            anchor="w",
        )
        title_lbl.grid(row=0, column=1, sticky="ew", padx=8, pady=(14, 0))

        name_lbl = ctk.CTkLabel(
            card,
            text="Detecting your GPU and Vulkan runtime...",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
            anchor="w",
            wraplength=520,
            justify="left",
        )
        name_lbl.grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 14))

        return card, status, name_lbl

    def on_enter(self, state: "WizardState") -> None:
        state.gpu_check_done = False
        state.gpu_check_ok = False
        self._set_gpu_checking()
        self._start_gpu_check()

    def on_exit(self) -> None:
        return None

    def can_advance(self) -> bool:
        state: "WizardState" = self.controller.context
        return state.gpu_check_done and state.gpu_check_ok

    def _set_gpu_checking(self) -> None:
        self._gpu_status.configure(text="Checking...", text_color=TEXT_MUTED)
        self._gpu_name_lbl.configure(
            text="Detecting your GPU and Vulkan runtime...",
            text_color=TEXT_MUTED,
        )

    def _start_gpu_check(self) -> None:
        if self._gpu_worker and self._gpu_worker.is_alive():
            return

        def worker() -> None:
            try:
                self._gpu_q.put(("result", check_gpu()))
            except Exception as exc:  # noqa: BLE001
                logger.exception("GPU check worker raised: %s", exc)
                self._gpu_q.put(("error", exc))

        self._gpu_worker = threading.Thread(target=worker, name="gpu-check", daemon=True)
        self._gpu_worker.start()
        self.after(120, self._drain_gpu)

    def _drain_gpu(self) -> None:
        try:
            while True:
                kind, value = self._gpu_q.get_nowait()
                if kind == "result":
                    self._apply_gpu_result(value)
                elif kind == "error":
                    self._apply_gpu_failure(str(value))
        except queue.Empty:
            pass

        if self._gpu_worker and self._gpu_worker.is_alive():
            self.after(120, self._drain_gpu)

    def _apply_gpu_result(self, result) -> None:
        state: "WizardState" = self.controller.context
        state.gpu_check_done = True
        state.gpu_check_ok = bool(result.ok)
        if result.ok:
            self._gpu_status.configure(text="OK", text_color=SUCCESS)
            self._gpu_name_lbl.configure(
                text=f"{result.name}  -  {result.reason}",
                text_color=TEXT,
            )
        else:
            self._gpu_status.configure(text="FAIL", text_color=DANGER)
            self._gpu_name_lbl.configure(
                text=f"{result.name}  -  {result.reason}",
                text_color=DANGER,
            )
        self.controller._refresh_next_state()

    def _apply_gpu_failure(self, message: str) -> None:
        state: "WizardState" = self.controller.context
        state.gpu_check_done = True
        state.gpu_check_ok = False
        self._gpu_status.configure(text="FAIL", text_color=DANGER)
        self._gpu_name_lbl.configure(
            text=f"GPU check failed: {message}",
            text_color=DANGER,
        )
        self.controller._refresh_next_state()

    def _target_config(self) -> Path:
        return Path.home() / "Documents" / CONFIG_RELATIVE

    def _on_restore_clicked(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose a config backup to restore",
            filetypes=[("Echoes config backup", "*.bak *.bak.*"), ("All files", "*.*")],
        )
        if not path:
            return

        src = Path(path)
        target = self._target_config()

        try:
            self._validate_backup_ini(src)
        except ValueError as exc:
            logger.warning("Restore rejected: %s", exc)
            self._show_toast(f"Restore rejected: {exc}")
            return

        if not self._confirm_restore(src, target):
            return

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_file():
                backup = create_backup(target)
                logger.info("Pre-restore backup: %s", backup)
            shutil.copy2(src, target)
            logger.info("Restored backup %s -> %s", src, target)
            self._show_toast(f"Restored from {src.name}")
        except OSError as exc:
            logger.error("Restore failed: %s", exc)
            self._show_toast(f"Restore failed: {exc}")

    def _validate_backup_ini(self, path: Path) -> None:
        if not path.is_file():
            raise ValueError("Selected file does not exist.")
        parser = configparser.ConfigParser(strict=False, interpolation=None)
        parser.optionxform = str
        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                parser.read_file(fh)
        except (OSError, configparser.Error) as exc:
            raise ValueError(f"Could not parse as INI: {exc}") from exc
        if not parser.sections():
            raise ValueError("File has no sections — not a valid Echoes config.")

    def _confirm_restore(self, src: Path, target: Path) -> bool:
        from tkinter import messagebox

        msg = (
            f"Restore config from\n{src}\n\nto\n{target}\n\n"
            "The current config will be backed up first. Continue?"
        )
        try:
            return messagebox.askyesno("Confirm restore", msg)
        except Exception:
            return True

    def _on_uninstall_clicked(self) -> None:
        from tkinter import filedialog, messagebox

        from core.uninstaller import uninstall_all

        config = self._target_config()
        if not config.is_file():
            self._show_toast("No config found to uninstall.")
            return
        if not any(config.with_name(config.name + s).is_file() for s in (".bak", ".bak.1", ".bak.2", ".bak.3", ".bak.4", ".bak.5")):
            self._show_toast("No config backup found; nothing to undo.")
            return

        game_dir_str = filedialog.askdirectory(
            title="Select the LOTRO game folder (the one containing dinput8.dll / d3d9.dll)",
            initialdir=str(Path("C:/")),
        )
        if not game_dir_str:
            return
        game_dir = Path(game_dir_str)

        msg = (
            f"Remove Vulkan files from:\n{game_dir}\n\n"
            f"And restore config:\n{config}\n\n"
            "Backups will be kept on disk. Continue?"
        )
        if not messagebox.askyesno("Confirm uninstall", msg):
            return

        result = uninstall_all(game_dir, config)
        if result.has_errors:
            logger.warning("Uninstall finished with errors: %s", result.errors)
            self._show_toast("Uninstall finished with errors. See logs.")
        else:
            self._show_toast("Uninstalled. Vulkan files removed; config restored.")
        for line in result.summary_lines():
            logger.info("Uninstall: %s", line)

    def _show_toast(self, message: str) -> None:
        toast = ctk.CTkLabel(
            self,
            text=message,
            fg_color=SURFACE_HOVER,
            text_color=TEXT,
            corner_radius=8,
            padx=12,
            pady=8,
        )
        toast.place(relx=0.5, rely=0.92, anchor="center")
        self.after(2500, toast.destroy)
