"""Step 5 - Completion page (success or failure state)."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from wizard.controller import (
    BODY,
    CANVAS,
    DANGER,
    INK,
    ON_DARK,
    SUCCESS,
    WizardState,
    font,
    heading_font,
)
from wizard.pages._common import (
    MARK_FAIL,
    MARK_OK,
    make_card,
    make_danger_button,
    make_hairline,
    make_open_folder_button,
    make_primary_button,
    make_section_label,
    make_secondary_button,
    make_subtitle,
)

if TYPE_CHECKING:
    from wizard.controller import WizardController

logger = logging.getLogger(__name__)


class CompletionPage(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, controller: "WizardController") -> None:
        super().__init__(parent, fg_color=CANVAS, corner_radius=0)
        self.controller = controller
        self._built = False
        self._details_widgets: list[ctk.CTkBaseClass] = []
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=CANVAS, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 8))
        header.grid_columnconfigure(0, weight=1)

        self._title_lbl = make_section_label(header, "[x]  ...")
        self._title_lbl.grid(row=0, column=0, sticky="ew")
        make_hairline(header).grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self._subtitle_lbl = make_subtitle(header, "")
        self._subtitle_lbl.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        self.body = ctk.CTkScrollableFrame(self, fg_color=CANVAS, corner_radius=0)
        self.body.grid(row=1, column=0, sticky="nsew", padx=24, pady=8)
        self.body.grid_columnconfigure(0, weight=1)

        self._built = True

    def _status_row(
        self,
        parent: ctk.CTkFrame,
        label: str,
        ok: bool,
        row: int,
    ) -> None:
        card = make_card(parent)
        card.grid(row=row, column=0, sticky="ew", pady=4)
        card.grid_columnconfigure(1, weight=1)

        mark = ctk.CTkLabel(
            card,
            text=MARK_OK if ok else MARK_FAIL,
            width=48,
            font=font(size=14, weight="bold"),
            text_color=SUCCESS if ok else DANGER,
        )
        mark.grid(row=0, column=0, padx=(16, 8), pady=12)
        lbl = ctk.CTkLabel(
            card,
            text=label,
            font=font(size=14),
            text_color=INK,
            anchor="w",
        )
        lbl.grid(row=0, column=1, sticky="ew", padx=8, pady=12)

    def _populate_success(self) -> None:
        self._title_lbl.configure(text="[x]  Installation complete")
        self._subtitle_lbl.configure(
            text="Echoes Vulkan Helper is ready. Launch the game when you're set.",
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

        actions = ctk.CTkFrame(self.body, fg_color=CANVAS, corner_radius=0)
        actions.grid(row=10, column=0, sticky="ew", pady=(16, 8))
        for c in range(4):
            actions.grid_columnconfigure(c, weight=1)

        make_primary_button(actions, ">>  launch echoes", self._launch_game).grid(
            row=0, column=0, padx=4, pady=4, sticky="ew"
        )
        make_open_folder_button(actions, "open game folder", self._game_folder).grid(
            row=0, column=1, padx=4, pady=4, sticky="ew"
        )
        make_open_folder_button(actions, "open config folder", self._config_folder).grid(
            row=0, column=2, padx=4, pady=4, sticky="ew"
        )
        make_secondary_button(actions, "[-]  restore backup", self._restore_backup).grid(
            row=0, column=3, padx=4, pady=4, sticky="ew"
        )

        uninstall_row = ctk.CTkFrame(self.body, fg_color=CANVAS, corner_radius=0)
        uninstall_row.grid(row=11, column=0, sticky="ew", pady=(0, 8))
        uninstall_row.grid_columnconfigure(0, weight=1)
        make_danger_button(
            uninstall_row, "[-]  uninstall vulkan files", self._uninstall_vulkan
        ).grid(row=0, column=0, padx=4, pady=4, sticky="ew")

    def _populate_failure(self) -> None:
        self._title_lbl.configure(text="[x]  Installation completed with errors", text_color=DANGER)
        self._subtitle_lbl.configure(
            text="Some checks did not pass. Restore the original config and inspect the logs.",
        )

        for w in self.body.winfo_children():
            w.destroy()

        state = self.controller.context
        if state.aborted:
            self._render_aborted()
            return

        groups = self._build_failure_groups(state.validation or {})
        for i, (name, passed, total) in enumerate(groups):
            self._group_summary_row(self.body, name, passed, total, row=i)

        details_btn_row = 10
        details_frame = ctk.CTkFrame(self.body, fg_color=CANVAS, corner_radius=0)
        details_frame.grid(
            row=details_btn_row, column=0, sticky="ew", pady=(8, 0)
        )
        details_frame.grid_columnconfigure(0, weight=1)

        self._details_visible = False
        toggle_btn = make_secondary_button(
            details_frame, "[+]  show details", lambda: self._toggle_failure_details(groups, details_btn_row + 1)
        )
        toggle_btn.grid(row=0, column=0, sticky="w")
        self._failure_details_toggle = toggle_btn
        self._failure_details_groups = groups
        self._failure_details_parent = details_frame

        actions = ctk.CTkFrame(self.body, fg_color=CANVAS, corner_radius=0)
        actions.grid(row=20, column=0, sticky="ew", pady=(16, 8))
        for c in range(4):
            actions.grid_columnconfigure(c, weight=1)

        make_primary_button(actions, ">>  restore backup", self._restore_backup).grid(
            row=0, column=0, padx=4, pady=4, sticky="ew"
        )
        make_secondary_button(actions, "open logs", self._open_logs).grid(
            row=0, column=1, padx=4, pady=4, sticky="ew"
        )
        make_open_folder_button(actions, "open game folder", self._game_folder).grid(
            row=0, column=2, padx=4, pady=4, sticky="ew"
        )
        make_open_folder_button(actions, "open config folder", self._config_folder).grid(
            row=0, column=3, padx=4, pady=4, sticky="ew"
        )

        actions_row2 = ctk.CTkFrame(self.body, fg_color=CANVAS, corner_radius=0)
        actions_row2.grid(row=21, column=0, sticky="ew", pady=(0, 8))
        actions_row2.grid_columnconfigure(0, weight=1)
        make_danger_button(
            actions_row2, "[-]  uninstall vulkan files", self._uninstall_vulkan
        ).grid(row=0, column=0, padx=4, pady=4, sticky="ew")

    def _build_failure_groups(self, validation: dict) -> list[tuple[str, int, int]]:
        checks = [
            ("[+]  setup", [
                ("configuration file present", bool(validation.get("config_found"))),
                ("config backup present", bool(validation.get("backup_found"))),
                ("game installation present", bool(validation.get("game_found"))),
            ]),
            ("[+]  settings", [
                ("recommended settings applied", bool(validation.get("settings_applied"))),
                ("Fullscreen = True", bool(validation.get("fullscreen_set"))),
                ("ConfineFullScreenMouseCursor = False", bool(validation.get("cursor_unconfined"))),
                ("resolution set", bool(validation.get("resolution_set"))),
            ]),
            ("[+]  vulkan files", [
                ("vulkan files installed", bool(validation.get("vulkan_installed"))),
                ("all DLL files present", bool(validation.get("dll_files_present"))),
            ]),
        ]
        out: list[tuple[str, int, int]] = []
        for name, items in checks:
            total = len(items)
            passed = sum(1 for _, ok in items if ok)
            out.append((name, passed, total))
        return out

    def _group_summary_row(
        self,
        parent: ctk.CTkFrame,
        group: str,
        passed: int,
        total: int,
        row: int,
    ) -> None:
        card = make_card(parent)
        card.grid(row=row, column=0, sticky="ew", pady=4)
        card.grid_columnconfigure(1, weight=1)

        ok = passed == total
        mark_text = MARK_OK if ok else MARK_FAIL
        mark_color = SUCCESS if ok else DANGER

        mark = ctk.CTkLabel(
            card,
            text=mark_text,
            width=48,
            font=font(size=14, weight="bold"),
            text_color=mark_color,
        )
        mark.grid(row=0, column=0, padx=(16, 8), pady=12)
        lbl = ctk.CTkLabel(
            card,
            text=group,
            font=font(size=14, weight="bold"),
            text_color=INK,
            anchor="w",
        )
        lbl.grid(row=0, column=1, sticky="ew", padx=8, pady=12)
        count = ctk.CTkLabel(
            card,
            text=f"{passed}/{total}",
            font=font(size=14),
            text_color=mark_color,
            anchor="e",
        )
        count.grid(row=0, column=2, padx=(8, 16), pady=12)

    def _toggle_failure_details(
        self, groups: list[tuple[str, int, int]], start_row: int
    ) -> None:
        self._details_visible = not self._details_visible
        toggle = self._failure_details_toggle
        for w in self._details_widgets:
            w.destroy()
        self._details_widgets = []
        if not self._details_visible:
            toggle.configure(text="[+]  show details")
            return
        toggle.configure(text="[-]  hide details")
        validation = self.controller.context.validation or {}
        flat = self._flatten_failure_checks(validation)
        for i, (label, ok) in enumerate(flat):
            self._status_row(self._failure_details_parent, label, ok, row=start_row + i)
            self._details_widgets.append(self._failure_details_parent.winfo_children()[-1])

    def _flatten_failure_checks(self, validation: dict) -> list[tuple[str, bool]]:
        return [
            ("configuration file present", bool(validation.get("config_found"))),
            ("config backup present", bool(validation.get("backup_found"))),
            ("game installation present", bool(validation.get("game_found"))),
            ("recommended settings applied", bool(validation.get("settings_applied"))),
            ("Fullscreen = True", bool(validation.get("fullscreen_set"))),
            ("ConfineFullScreenMouseCursor = False", bool(validation.get("cursor_unconfined"))),
            ("resolution set", bool(validation.get("resolution_set"))),
            ("vulkan files installed", bool(validation.get("vulkan_installed"))),
            ("all DLL files present", bool(validation.get("dll_files_present"))),
        ]

    def _render_aborted(self) -> None:
        info = ctk.CTkLabel(
            self.body,
            text=(
                "[x]  the install was cancelled before it finished. your files may be "
                "in a partial state. you can restore from a backup below."
            ),
            font=font(size=13),
            text_color=DANGER,
            anchor="w",
            justify="left",
            wraplength=720,
        )
        info.grid(row=0, column=0, sticky="ew", pady=12)

        actions = ctk.CTkFrame(self.body, fg_color=CANVAS, corner_radius=0)
        actions.grid(row=1, column=0, sticky="ew", pady=(12, 8))
        for c in range(2):
            actions.grid_columnconfigure(c, weight=1)

        make_primary_button(actions, ">>  restore backup", self._restore_backup).grid(
            row=0, column=0, padx=4, pady=4, sticky="ew"
        )
        make_secondary_button(actions, "open logs", self._open_logs).grid(
            row=0, column=1, padx=4, pady=4, sticky="ew"
        )

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
            self._append_status("[x]  cannot restore: no config file is known.")
            logger.warning("Restore requested but state.config_path is None.")
            return
        from core.backup_manager import restore_backup

        ok = restore_backup(state.config_path)
        if ok:
            self._append_status("[+]  backup restored.")
        else:
            self._append_status("[x]  no backup found to restore.")

    def _uninstall_vulkan(self) -> None:
        from tkinter import messagebox

        from core.uninstaller import uninstall_all

        state = self.controller.context
        if not state.game_path:
            self._append_status("[x]  cannot uninstall: no game folder known.")
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
            self._append_status("[!]  uninstall finished with errors. see logs.")
        else:
            self._append_status(f"[+]  vulkan files uninstalled. config: {result.config_action}.")
        for line in result.summary_lines():
            self._append_status(line)

    def _append_status(self, message: str) -> None:
        lbl = ctk.CTkLabel(
            self.body,
            text=message,
            font=font(size=13),
            text_color=BODY,
        )
        lbl.grid(row=99, column=0, sticky="ew", padx=16, pady=8)
