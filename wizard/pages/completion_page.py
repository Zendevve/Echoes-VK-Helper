"""Step 5 - Completion page (success or failure state)."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

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
from wizard.pages._common import (
    make_card,
    make_open_folder_button,
    make_subtitle,
    make_title,
)

if TYPE_CHECKING:
    from wizard.controller import WizardController

logger = logging.getLogger(__name__)


class CompletionPage(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, controller: "WizardController") -> None:
        super().__init__(parent, fg_color=BG_DARK, corner_radius=0)
        self.controller = controller
        self._built = False
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.grid_columnconfigure(0, weight=1)
        self._title = make_title(header, "")
        self._title.grid(row=0, column=0, sticky="ew", padx=8)
        self._subtitle = make_subtitle(header, "")
        self._subtitle.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 0))

        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)

        self._built = True

    def _status_row(self, parent: ctk.CTkFrame, label: str, ok: bool, row: int) -> None:
        card = make_card(parent)
        card.grid(row=row, column=0, sticky="ew", padx=8, pady=4)
        card.grid_columnconfigure(1, weight=1)

        mark = ctk.CTkLabel(
            card,
            text="OK" if ok else "X",
            width=28,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=SUCCESS if ok else DANGER,
        )
        mark.grid(row=0, column=0, padx=(16, 8), pady=12)
        lbl = ctk.CTkLabel(
            card,
            text=label,
            font=ctk.CTkFont(size=14),
            text_color=TEXT,
            anchor="w",
        )
        lbl.grid(row=0, column=1, sticky="ew", padx=8, pady=12)

    def _populate_success(self) -> None:
        self._title.configure(text="Installation complete")
        self._subtitle.configure(
            text="Echoes Vulkan Helper is ready. You can launch the game when you're set.",
        )

        for w in self.body.winfo_children():
            w.destroy()

        lines = [
            "Configuration updated successfully.",
            "Vulkan files installed successfully.",
            "Backups created successfully.",
            "Validation passed.",
        ]
        for i, line in enumerate(lines):
            self._status_row(self.body, line, ok=True, row=i)

        actions = ctk.CTkFrame(self.body, fg_color="transparent")
        actions.grid(row=10, column=0, sticky="ew", padx=8, pady=(12, 8))
        for c in range(4):
            actions.grid_columnconfigure(c, weight=1)

        ctk.CTkButton(
            actions,
            text="Launch Echoes",
            height=44,
            fg_color=ACCENT,
            hover_color="#9d4ee8",
            text_color=TEXT,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._launch_game,
        ).grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        make_open_folder_button(actions, "Open Game Folder", self._game_folder).grid(
            row=0, column=1, padx=4, pady=4, sticky="ew"
        )
        make_open_folder_button(actions, "Open Config Folder", self._config_folder).grid(
            row=0, column=2, padx=4, pady=4, sticky="ew"
        )
        restore_btn = ctk.CTkButton(
            actions,
            text="Restore Backup",
            height=44,
            fg_color="transparent",
            hover_color=SURFACE_HOVER,
            border_width=1,
            border_color=SURFACE_HOVER,
            text_color=TEXT_MUTED,
            command=self._restore_backup,
        )
        restore_btn.grid(row=0, column=3, padx=4, pady=4, sticky="ew")

        uninstall_row = ctk.CTkFrame(self.body, fg_color="transparent")
        uninstall_row.grid(row=11, column=0, sticky="ew", padx=8, pady=(0, 8))
        uninstall_row.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            uninstall_row,
            text="Uninstall Vulkan Files",
            height=44,
            fg_color="transparent",
            hover_color=SURFACE_HOVER,
            border_width=1,
            border_color=SURFACE_HOVER,
            text_color=TEXT_MUTED,
            command=self._uninstall_vulkan,
        ).grid(row=0, column=0, padx=4, pady=4, sticky="ew")

    def _populate_failure(self) -> None:
        self._title.configure(text="Installation completed with errors", text_color=DANGER)
        self._subtitle.configure(
            text="Some checks did not pass. You can restore the original config and inspect the logs.",
        )

        for w in self.body.winfo_children():
            w.destroy()

        state = self.controller.context
        validation = state.validation or {}
        checks = [
            ("Configuration file present", bool(validation.get("config_found"))),
            ("Config backup present", bool(validation.get("backup_found"))),
            ("Game installation present", bool(validation.get("game_found"))),
            ("Recommended settings applied", bool(validation.get("settings_applied"))),
            ("Vulkan files installed", bool(validation.get("vulkan_installed"))),
            ("Fullscreen = True", bool(validation.get("fullscreen_set"))),
            ("ConfineFullScreenMouseCursor = False", bool(validation.get("cursor_unconfined"))),
            ("Resolution set", bool(validation.get("resolution_set"))),
            ("All DLL files present", bool(validation.get("dll_files_present"))),
        ]
        for i, (label, ok) in enumerate(checks):
            self._status_row(self.body, label, ok, row=i)

        actions = ctk.CTkFrame(self.body, fg_color="transparent")
        actions.grid(row=20, column=0, sticky="ew", padx=8, pady=(12, 8))
        for c in range(4):
            actions.grid_columnconfigure(c, weight=1)

        ctk.CTkButton(
            actions,
            text="Restore Backup",
            height=44,
            fg_color=ACCENT,
            hover_color="#9d4ee8",
            text_color=TEXT,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._restore_backup,
        ).grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        logs_btn = ctk.CTkButton(
            actions,
            text="Open Logs",
            height=44,
            fg_color=SURFACE_HOVER,
            hover_color="#4a4a4a",
            text_color=TEXT,
            command=self._open_logs,
        )
        logs_btn.grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        make_open_folder_button(actions, "Open Game Folder", self._game_folder).grid(
            row=0, column=2, padx=4, pady=4, sticky="ew"
        )
        make_open_folder_button(actions, "Open Config Folder", self._config_folder).grid(
            row=0, column=3, padx=4, pady=4, sticky="ew"
        )

        actions_row2 = ctk.CTkFrame(self.body, fg_color="transparent")
        actions_row2.grid(row=21, column=0, sticky="ew", padx=8, pady=(0, 8))
        actions_row2.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            actions_row2,
            text="Uninstall Vulkan Files",
            height=44,
            fg_color="transparent",
            hover_color=SURFACE_HOVER,
            border_width=1,
            border_color=SURFACE_HOVER,
            text_color=TEXT_MUTED,
            command=self._uninstall_vulkan,
        ).grid(row=0, column=0, padx=4, pady=4, sticky="ew")

    def _render_actions(
        self,
        row: int,
        primary: tuple[str, callable, str],
        secondary_buttons: list[tuple[str, callable]],
        outline: tuple[str, callable] | None = None,
    ) -> None:
        actions = ctk.CTkFrame(self.body, fg_color="transparent")
        actions.grid(row=row, column=0, sticky="ew", padx=8, pady=(12, 8))
        cols = 1 + len(secondary_buttons) + (1 if outline else 0)
        for c in range(cols):
            actions.grid_columnconfigure(c, weight=1)

        col = 0
        label, fn, style = primary
        primary_btn = ctk.CTkButton(
            actions,
            text=label,
            height=44,
            fg_color=ACCENT if style == "accent" else SURFACE_HOVER,
            hover_color="#9d4ee8" if style == "accent" else "#4a4a4a",
            text_color=TEXT,
            font=ctk.CTkFont(size=14, weight="bold") if style == "accent" else ctk.CTkFont(size=14),
            command=fn,
        )
        primary_btn.grid(row=0, column=col, padx=4, pady=4, sticky="ew")
        col += 1

        for text, fn in secondary_buttons:
            btn = ctk.CTkButton(
                actions,
                text=text,
                height=44,
                fg_color=SURFACE_HOVER,
                hover_color="#4a4a4a",
                text_color=TEXT,
                command=fn,
            )
            btn.grid(row=0, column=col, padx=4, pady=4, sticky="ew")
            col += 1

        if outline is not None:
            text, fn = outline
            btn = ctk.CTkButton(
                actions,
                text=text,
                height=44,
                fg_color="transparent",
                hover_color=SURFACE_HOVER,
                border_width=1,
                border_color=SURFACE_HOVER,
                text_color=TEXT_MUTED,
                command=fn,
            )
            btn.grid(row=0, column=col, padx=4, pady=4, sticky="ew")

    def on_enter(self, state: WizardState) -> None:
        if state.install_succeeded:
            self._populate_success()
        else:
            self._populate_failure()

    def on_exit(self) -> None:
        return None

    def can_advance(self) -> bool:
        return True

    def _game_folder(self) -> Path | None:
        return self.controller.context.game_path

    def _config_folder(self) -> Path | None:
        cfg = self.controller.context.config_path
        return cfg.parent if cfg else None

    def _open_logs(self) -> None:
        from core.paths import logs_dir
        from wizard.pages._common import _open_in_explorer

        _open_in_explorer(logs_dir())

    def _launch_game(self) -> None:
        state = self.controller.context
        if not state.game_path:
            return
        exe = state.game_path / "lotroclient.exe"
        if not exe.is_file():
            return
        try:
            subprocess.Popen([str(exe)], cwd=str(state.game_path))
            logger.info("Launched %s", exe)
        except OSError as exc:
            logger.error("Could not launch %s: %s", exe, exc)

    def _restore_backup(self) -> None:
        state = self.controller.context
        if not state.config_path:
            return
        from core.backup_manager import restore_backup

        ok = restore_backup(state.config_path)
        if ok:
            self._append_status("Backup restored.")
        else:
            self._append_status("No backup found to restore.")

    def _uninstall_vulkan(self) -> None:
        from tkinter import messagebox

        from core.uninstaller import uninstall_all

        state = self.controller.context
        if not state.game_path:
            self._append_status("Cannot uninstall: no game folder known.")
            return
        if not messagebox.askyesno(
            "Uninstall Vulkan files",
            "Remove dinput8.ini, dinput8.dll, and d3d9.dll from the game folder?\n\n"
            "Backups (if present) will be restored. The config will also be reverted "
            "to its pre-install state if a backup is available.",
        ):
            return
        result = uninstall_all(state.game_path, state.config_path)
        if result.has_errors:
            logger.warning("Uninstall completed with errors: %s", result.errors)
            self._append_status("Uninstall finished with errors. See logs.")
        else:
            self._append_status("Vulkan files uninstalled. Config: " + result.config_action + ".")
        for line in result.summary_lines():
            self._append_status(line)

    def _append_status(self, message: str) -> None:
        lbl = ctk.CTkLabel(
            self.body,
            text=message,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_MUTED,
        )
        lbl.grid(row=99, column=0, sticky="ew", padx=16, pady=8)
