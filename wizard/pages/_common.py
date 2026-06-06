"""Shared helpers for wizard pages.

OpenCode-faithful design system. All page chrome composes from these helpers so
the brand vocabulary lives in one place.
"""
from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from typing import Callable, Optional

import customtkinter as ctk

from wizard.controller import (
    BODY,
    BODY_MD,
    BUTTON_MD,
    CANVAS,
    CAPTION_MD,
    DANGER,
    DISPLAY_XL,
    HAIRLINE,
    HAIRLINE_STRONG,
    HEADING_MD,
    INK,
    INK_DEEP,
    MUTE,
    ON_DARK,
    ON_PRIMARY,
    ROUNDED_NONE,
    ROUNDED_SM,
    SUCCESS,
    SURFACE_CARD,
    SURFACE_DARK,
    SURFACE_SOFT,
    font,
    heading_font,
)


def make_title(parent: ctk.CTkBaseClass, text: str, size: int = DISPLAY_XL) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent,
        text=text,
        font=font(size=size, weight="bold"),
        text_color=INK,
        anchor="w",
        justify="left",
    )


def make_section_label(
    parent: ctk.CTkBaseClass, text: str
) -> ctk.CTkLabel:
    """`heading-md` 16/700. Brand section label rendered bare, no chip bg."""
    return ctk.CTkLabel(
        parent,
        text=text,
        font=heading_font(size=HEADING_MD),
        text_color=INK,
        anchor="w",
        justify="left",
    )


def make_subtitle(parent: ctk.CTkBaseClass, text: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent,
        text=text,
        font=font(size=BODY_MD),
        text_color=BODY,
        anchor="w",
        justify="left",
        wraplength=720,
    )


def make_hairline(parent: ctk.CTkBaseClass, color: str = HAIRLINE) -> ctk.CTkFrame:
    return ctk.CTkFrame(parent, fg_color=color, height=1, corner_radius=0)


def make_card(parent: ctk.CTkBaseClass) -> ctk.CTkFrame:
    """Flat card: cream canvas + 1px hairline. No fill, no shadow."""
    return ctk.CTkFrame(
        parent,
        fg_color=CANVAS,
        corner_radius=ROUNDED_NONE,
        border_width=1,
        border_color=HAIRLINE,
    )


def make_soft_card(parent: ctk.CTkBaseClass) -> ctk.CTkFrame:
    return ctk.CTkFrame(
        parent,
        fg_color=SURFACE_SOFT,
        corner_radius=ROUNDED_SM,
        border_width=0,
    )


def make_dark_card(parent: ctk.CTkBaseClass) -> ctk.CTkFrame:
    """The single dark surface. Use only for hero TUI mockup or aborted state."""
    return ctk.CTkFrame(
        parent,
        fg_color=SURFACE_DARK,
        corner_radius=ROUNDED_NONE,
        border_width=0,
    )


def make_install_snippet(parent: ctk.CTkBaseClass, text: str) -> ctk.CTkFrame:
    """`install-snippet` component: pill on `surface-card`, 4px radius."""
    frame = ctk.CTkFrame(
        parent,
        fg_color=SURFACE_CARD,
        corner_radius=ROUNDED_SM,
        height=44,
    )
    label = ctk.CTkLabel(
        frame,
        text=text,
        font=font(size=BODY_MD, weight="normal"),
        text_color=INK,
        anchor="w",
        justify="left",
    )
    label.pack(side="left", padx=16, pady=12, fill="x", expand=True)
    return frame


def make_ascii_bullet(
    parent: ctk.CTkBaseClass,
    mark: str = "[+]",
    color: Optional[str] = None,
) -> ctk.CTkLabel:
    """`[+]` / `[-]` / `[x]` / `[?]` ASCII marker rendered as text."""
    if color is None:
        color = MUTE if mark in ("[?]", "...") else INK
    return ctk.CTkLabel(
        parent,
        text=mark,
        font=font(size=BODY_MD, weight="bold"),
        text_color=color,
        width=36,
        anchor="w",
    )


def make_open_folder_button(
    parent: ctk.CTkBaseClass,
    text: str,
    path_provider: Callable[[], Path | None],
) -> ctk.CTkButton:
    btn = ctk.CTkButton(
        parent,
        text=text,
        fg_color=CANVAS,
        hover_color=SURFACE_SOFT,
        text_color=INK,
        font=font(size=BUTTON_MD, weight="normal"),
        border_width=1,
        border_color=HAIRLINE_STRONG,
        corner_radius=ROUNDED_SM,
        height=36,
    )
    btn.configure(command=lambda: _open_in_explorer(path_provider()))
    return btn


def make_secondary_button(
    parent: ctk.CTkBaseClass,
    text: str,
    command: Callable[[], None],
) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent,
        text=text,
        fg_color=CANVAS,
        hover_color=SURFACE_SOFT,
        text_color=INK,
        font=font(size=BUTTON_MD, weight="normal"),
        border_width=1,
        border_color=HAIRLINE_STRONG,
        corner_radius=ROUNDED_SM,
        height=36,
        command=command,
    )


def make_primary_button(
    parent: ctk.CTkBaseClass,
    text: str,
    command: Callable[[], None],
) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent,
        text=text,
        fg_color=INK,
        hover_color=INK_DEEP,
        text_color=ON_PRIMARY,
        font=font(size=BUTTON_MD, weight="bold"),
        corner_radius=ROUNDED_SM,
        height=36,
        command=command,
    )


def make_danger_button(
    parent: ctk.CTkBaseClass,
    text: str,
    command: Callable[[], None],
) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent,
        text=text,
        fg_color=DANGER,
        hover_color="#d70015",
        text_color=ON_PRIMARY,
        font=font(size=BUTTON_MD, weight="bold"),
        corner_radius=ROUNDED_SM,
        height=36,
        command=command,
    )


def _open_in_explorer(target: Path | None) -> None:
    if target is None or not target.exists():
        return
    if platform.system() == "Windows":
        try:
            subprocess.Popen(["explorer", str(target)])
        except OSError:
            pass
    else:
        try:
            subprocess.Popen(["xdg-open", str(target)])
        except OSError:
            pass


# ASCII bracket markers used in list rows ---------------------------------------
MARK_OK = "[+]"
MARK_FAIL = "[x]"
MARK_PENDING = "[?]"
MARK_NO = "[-]"
MARK_DONE = "[x]"
MARK_TICK = "[x]"
