"""Step 3 - Installation summary page."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import customtkinter as ctk

from wizard.controller import (
    ACCENT_HOVER,
    BODY,
    CANVAS,
    INK,
    MUTE,
    SUCCESS,
    SURFACE_CARD,
    WizardState,
    font,
    heading_font,
)
from wizard.pages._common import (
    MARK_OK,
    make_card,
    make_hairline,
    make_section_label,
    make_subtitle,
)

if TYPE_CHECKING:
    from wizard.controller import WizardController

logger = logging.getLogger(__name__)


class SummaryPage(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, controller: "WizardController") -> None:
        super().__init__(parent, fg_color=CANVAS, corner_radius=0)
        self.controller = controller
        self._resolution_options: list[tuple[int, int]] = []
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        self._build_header(self)
        self._build_body(self)

    def _build_header(self, parent: ctk.CTkFrame) -> None:
        header = ctk.CTkFrame(parent, fg_color=CANVAS, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 8))
        header.grid_columnconfigure(0, weight=1)

        make_section_label(header, "[+]  Review changes").grid(
            row=0, column=0, sticky="ew"
        )
        make_hairline(header).grid(row=1, column=0, sticky="ew", pady=(8, 0))
        make_subtitle(
            header,
            "The following changes will be applied. Click Install to continue.",
        ).grid(row=2, column=0, sticky="ew", pady=(8, 0))

    def _build_body(self, parent: ctk.CTkFrame) -> None:
        body = ctk.CTkScrollableFrame(parent, fg_color=CANVAS, corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=8)
        body.grid_columnconfigure(0, weight=1)

        self.config_card = self._build_section(body, "[+]  configuration changes", row=0)
        self.files_card = self._build_section(body, "[+]  files to install", row=1)
        self.backup_card = self._build_section(body, "[+]  backups to create", row=2)
        self.monitor_card = self._build_section(body, "[?]  display", row=3)

        self._populate_config_rows()
        self._populate_files_rows()
        self._populate_backup_rows()
        self._populate_monitor_row()

    def _build_section(self, parent: ctk.CTkScrollableFrame, title: str, row: int) -> ctk.CTkFrame:
        card = make_card(parent)
        card.grid(row=row, column=0, sticky="ew", pady=8)
        card.grid_columnconfigure(0, weight=1)

        lbl = ctk.CTkLabel(
            card,
            text=title,
            font=heading_font(size=15),
            text_color=INK,
            anchor="w",
        )
        lbl.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))

        make_hairline(card).grid(row=1, column=0, sticky="ew", padx=16)

        body = ctk.CTkFrame(card, fg_color=CANVAS, corner_radius=0)
        body.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))
        body.grid_columnconfigure(0, weight=1)
        return body

    def _row(self, parent: ctk.CTkFrame, text: str, value: str = "") -> ctk.CTkFrame:
        row = self._build_check_row(parent, text)
        if value:
            val = ctk.CTkLabel(
                row,
                text=value,
                font=font(size=14),
                text_color=INK,
                anchor="e",
            )
            val.grid(row=0, column=2, sticky="e", padx=(8, 0))
        return row

    def _build_check_row(self, parent: ctk.CTkFrame, text: str) -> ctk.CTkFrame:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=4)
        row.grid_columnconfigure(0, weight=0)
        row.grid_columnconfigure(1, weight=1)
        mark = ctk.CTkLabel(
            row,
            text=MARK_OK,
            font=font(size=14, weight="bold"),
            text_color=SUCCESS,
            width=36,
        )
        mark.grid(row=0, column=0, padx=(0, 8))
        lbl = ctk.CTkLabel(
            row,
            text=text,
            font=font(size=14),
            text_color=BODY,
            anchor="w",
        )
        lbl.grid(row=0, column=1, sticky="ew")
        return row

    def _populate_config_rows(self) -> None:
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
            font=font(size=14, weight="bold"),
            text_color=INK,
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
            width=160,
            fg_color=SURFACE_CARD,
            button_color=INK,
            button_hover_color=ACCENT_HOVER,
            text_color=INK,
            dropdown_fg_color=CANVAS,
            dropdown_text_color=INK,
            dropdown_hover_color=SURFACE_CARD,
            font=font(size=14, weight="normal"),
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
        if getattr(self, "_res_value_lbl", None) is not None:
            self._res_value_lbl.configure(text=current)

    def on_exit(self) -> None:
        return None

    def can_advance(self) -> bool:
        return True
