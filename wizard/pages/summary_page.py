"""Step 3 - Installation summary page."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import customtkinter as ctk

from wizard.controller import (
    ACCENT,
    BG_DARK,
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


class SummaryPage(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, controller: "WizardController") -> None:
        super().__init__(parent, fg_color=BG_DARK, corner_radius=0)
        self.controller = controller
        self._resolution_options: list[tuple[int, int]] = []
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        make_title(header, "Review changes").grid(row=0, column=0, sticky="ew", padx=8)
        make_subtitle(
            header,
            "The following changes will be applied. Click Install to continue.",
        ).grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 12))

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        self.config_card = self._build_section(
            body, "Configuration changes", row=0
        )
        self.files_card = self._build_section(body, "Files to install", row=1)
        self.backup_card = self._build_section(body, "Backups to create", row=2)
        self.monitor_card = self._build_section(body, "Display", row=3)

        self._populate_config_rows()
        self._populate_files_rows()
        self._populate_backup_rows()
        self._populate_monitor_row()

    def _build_section(self, parent: ctk.CTkScrollableFrame, title: str, row: int) -> ctk.CTkFrame:
        card = make_card(parent)
        card.grid(row=row, column=0, sticky="ew", padx=8, pady=6)
        card.grid_columnconfigure(0, weight=1)
        lbl = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=TEXT,
            anchor="w",
        )
        lbl.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 6))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
        body.grid_columnconfigure(0, weight=1)
        return body

    def _row(self, parent: ctk.CTkFrame, text: str, value: str = "") -> ctk.CTkFrame:
        row = self._build_check_row(parent, text)
        if value:
            val = ctk.CTkLabel(
                row,
                text=value,
                font=ctk.CTkFont(size=14),
                text_color=TEXT_MUTED,
                anchor="e",
            )
            val.grid(row=0, column=2, sticky="e", padx=(8, 0))
        return row

    def _build_check_row(self, parent: ctk.CTkFrame, text: str) -> ctk.CTkFrame:
        """Build the standard OK + label row. Returns the frame so callers can
        attach a trailing widget (e.g. resolution dropdown) in column 2."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)
        row.grid_columnconfigure(0, weight=0)
        row.grid_columnconfigure(1, weight=1)
        mark = ctk.CTkLabel(
            row,
            text="OK",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=SUCCESS,
            width=24,
        )
        mark.grid(row=0, column=0, padx=(0, 8))
        lbl = ctk.CTkLabel(
            row,
            text=text,
            font=ctk.CTkFont(size=14),
            text_color=TEXT,
            anchor="w",
        )
        lbl.grid(row=0, column=1, sticky="ew")
        return row

    def _populate_config_rows(self) -> None:
        state = self.controller.context
        self._row(self.config_card, "Fullscreen", "True")
        self._row(self.config_card, "ConfineFullScreenMouseCursor", "False")
        self._res_value_lbl = self._add_value_row(self.config_card, "Resolution")

    def _add_value_row(self, parent: ctk.CTkFrame, text: str) -> ctk.CTkLabel:
        row = self._build_check_row(parent, text)
        row.grid_columnconfigure(2, weight=0)
        state = self.controller.context
        if text == "Resolution" and state.resolution:
            val = f"{state.resolution[0]}x{state.resolution[1]}"
        else:
            val = ""
        lbl = ctk.CTkLabel(
            row,
            text=val,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT,
            anchor="e",
        )
        lbl.grid(row=0, column=2, sticky="e", padx=(8, 0))
        return lbl

    def _populate_files_rows(self) -> None:
        for name in ("dinput8.ini", "dinput8.dll", "d3d9.dll"):
            self._row(self.files_card, name, "install")

    def _populate_backup_rows(self) -> None:
        self._row(self.backup_card, "Config backup (rotated, .bak chain)", "1 file")
        self._row(self.backup_card, "Existing DLL/INI backups (rotated, .backup chain)", "as needed")

    def _populate_monitor_row(self) -> None:
        from core.resolution import curated_modes, get_native_resolution

        state = self.controller.context
        native = state.resolution or get_native_resolution()
        modes = curated_modes(native=native)
        self._resolution_options = modes

        row = self._build_check_row(self.monitor_card, "Primary monitor resolution")
        row.grid_columnconfigure(2, weight=0)

        current = state.resolution or modes[0]
        initial = f"{current[0]}x{current[1]}"
        self._res_var = ctk.StringVar(value=initial)
        self._res_menu = ctk.CTkOptionMenu(
            row,
            variable=self._res_var,
            values=[f"{w}x{h}" for w, h in modes],
            width=140,
            fg_color=SURFACE_HOVER,
            button_color=ACCENT,
            button_hover_color="#9d4ee8",
            text_color=TEXT,
            command=self._on_resolution_change,
        )
        self._res_menu.grid(row=0, column=2, sticky="e")

    def _on_resolution_change(self, value: str) -> None:
        try:
            w_str, h_str = value.lower().split("x")
            self.controller.context.resolution = (int(w_str), int(h_str))
        except (ValueError, AttributeError):
            logger.warning("Bad resolution value: %s", value)
            return
        if getattr(self, "_res_value_lbl", None) is not None:
            self._res_value_lbl.configure(text=value)

    def on_enter(self, state: WizardState) -> None:
        from core.resolution import get_native_resolution

        if state.resolution is None:
            state.resolution = get_native_resolution()
        if hasattr(self, "_res_var"):
            current = f"{state.resolution[0]}x{state.resolution[1]}"
            self._res_var.set(current)

    def on_exit(self) -> None:
        return None

    def can_advance(self) -> bool:
        return True
