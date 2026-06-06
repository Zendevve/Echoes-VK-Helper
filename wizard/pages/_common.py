"""Shared helpers for wizard pages."""
from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from typing import Callable

import customtkinter as ctk

from wizard.controller import SURFACE, SURFACE_HOVER, TEXT, TEXT_MUTED


def make_title(parent: ctk.CTkFrame, text: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent,
        text=text,
        font=ctk.CTkFont(size=26, weight="bold"),
        text_color=TEXT,
        anchor="w",
    )


def make_subtitle(parent: ctk.CTkFrame, text: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent,
        text=text,
        font=ctk.CTkFont(size=14),
        text_color=TEXT_MUTED,
        anchor="w",
        wraplength=680,
        justify="left",
    )


def make_card(parent: ctk.CTkFrame) -> ctk.CTkFrame:
    return ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=12)


def make_open_folder_button(
    parent: ctk.CTkFrame,
    text: str,
    path_provider: Callable[[], Path | None],
) -> ctk.CTkButton:
    """Button that opens the folder returned by path_provider() in Explorer."""
    btn = ctk.CTkButton(
        parent,
        text=text,
        fg_color=SURFACE_HOVER,
        hover_color="#4a4a4a",
        text_color=TEXT,
    )
    btn.configure(command=lambda: _open_in_explorer(path_provider()))
    return btn


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
