"""Shared helpers for wizard pages.

OpenCode-faithful design system. All page chrome composes from these helpers so
the brand vocabulary lives in one place.
"""

from __future__ import annotations

import contextlib
import platform
import subprocess
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from wizard.anim import tween
from wizard.controller import (
    BODY,
    BODY_MD,
    BUTTON_MD,
    CANVAS,
    DANGER,
    DISPLAY_XL,
    HAIRLINE,
    HAIRLINE_STRONG,
    HEADING_MD,
    INK,
    INK_DEEP,
    MUTE,
    ON_PRIMARY,
    ROUNDED_NONE,
    ROUNDED_SM,
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


def make_section_label(parent: ctk.CTkBaseClass, text: str) -> ctk.CTkLabel:
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
    color: str | None = None,
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


def _wire_button_motion(
    btn: ctk.CTkButton,
    *,
    base: str,
    hover: str,
    active: str,
) -> ctk.CTkButton:
    """Install hover/press tweens on a customtkinter button.

    Customtkinter's built-in ``hover_color`` snaps instantly; we disable it by
    setting it equal to the base color and drive the fg_color transition
    ourselves via ``wizard.anim.tween``.
    """
    btn.configure(hover_color=base)
    state = {"hovered": False, "pressed": False, "base": base, "hover": hover, "active": active}

    def _target() -> str:
        if state["pressed"]:
            return state["active"]
        if state["hovered"]:
            return state["hover"]
        return state["base"]

    def _animate() -> None:
        tween(
            btn,
            attr="fg_color",
            start=state["base"],
            end=_target(),
            duration_ms=100,
            steps=8,
            easing="ease_out",
        )

    btn.bind("<Enter>", lambda _e: (state.__setitem__("hovered", True), _animate()))
    btn.bind(
        "<Leave>",
        lambda _e: (
            state.__setitem__("hovered", False),
            state.__setitem__("pressed", False),
            _animate(),
        ),
    )
    btn.bind("<Button-1>", lambda _e: (state.__setitem__("pressed", True), _animate()))
    btn.bind("<ButtonRelease-1>", lambda _e: (state.__setitem__("pressed", False), _animate()))
    btn._evh_motion_state = state
    return btn


def update_button_motion(
    btn: ctk.CTkButton,
    *,
    base: str,
    hover: str,
    active: str,
) -> None:
    """Re-target the hover/press tween colors for a button whose style was
    updated externally (e.g. nav-bar buttons in the controller).
    """
    state = getattr(btn, "_evh_motion_state", None)
    if state is None:
        return
    state["base"] = base
    state["hover"] = hover
    state["active"] = active
    btn.configure(hover_color=base)
    with contextlib.suppress(Exception):
        btn.configure(fg_color=base)


def make_open_folder_button(
    parent: ctk.CTkBaseClass,
    text: str,
    path_provider: Callable[[], Path | None],
) -> ctk.CTkButton:
    btn = ctk.CTkButton(
        parent,
        text=text,
        fg_color=CANVAS,
        hover_color=CANVAS,
        text_color=INK,
        font=font(size=BUTTON_MD, weight="normal"),
        border_width=1,
        border_color=HAIRLINE_STRONG,
        corner_radius=ROUNDED_SM,
        height=36,
    )
    btn.configure(command=lambda: _open_in_explorer(path_provider()))
    return _wire_button_motion(btn, base=CANVAS, hover=SURFACE_SOFT, active=SURFACE_CARD)


def make_secondary_button(
    parent: ctk.CTkBaseClass,
    text: str,
    command: Callable[[], None],
) -> ctk.CTkButton:
    btn = ctk.CTkButton(
        parent,
        text=text,
        fg_color=CANVAS,
        hover_color=CANVAS,
        text_color=INK,
        font=font(size=BUTTON_MD, weight="normal"),
        border_width=1,
        border_color=HAIRLINE_STRONG,
        corner_radius=ROUNDED_SM,
        height=36,
        command=command,
    )
    return _wire_button_motion(btn, base=CANVAS, hover=SURFACE_SOFT, active=SURFACE_CARD)


def make_primary_button(
    parent: ctk.CTkBaseClass,
    text: str,
    command: Callable[[], None],
) -> ctk.CTkButton:
    btn = ctk.CTkButton(
        parent,
        text=text,
        fg_color=INK,
        hover_color=INK,
        text_color=ON_PRIMARY,
        font=font(size=BUTTON_MD, weight="bold"),
        corner_radius=ROUNDED_SM,
        height=36,
        command=command,
    )
    return _wire_button_motion(btn, base=INK, hover=INK_DEEP, active=INK_DEEP)


def make_danger_button(
    parent: ctk.CTkBaseClass,
    text: str,
    command: Callable[[], None],
) -> ctk.CTkButton:
    btn = ctk.CTkButton(
        parent,
        text=text,
        fg_color=DANGER,
        hover_color=DANGER,
        text_color=ON_PRIMARY,
        font=font(size=BUTTON_MD, weight="bold"),
        corner_radius=ROUNDED_SM,
        height=36,
        command=command,
    )
    return _wire_button_motion(btn, base=DANGER, hover="#d70015", active="#a50011")


def set_status(
    label: ctk.CTkLabel,
    mark: str,
    color: str,
    *,
    duration_ms: int = 180,
) -> None:
    """Animate a status marker (e.g. ``[?]`` -> ``[+]``) with a color tween.

    The marker text swaps immediately so the user gets feedback at the same
    beat, but the color eases in so the change reads as alive.
    """
    label.configure(text=mark)
    tween(
        label,
        attr="text_color",
        start="#8a8a8a",
        end=color,
        duration_ms=duration_ms,
        steps=12,
        easing="ease_out",
    )


def _open_in_explorer(target: Path | None) -> None:
    if target is None or not target.exists():
        return
    if platform.system() == "Windows":
        with contextlib.suppress(OSError):
            subprocess.Popen(["explorer", str(target)])
    else:
        with contextlib.suppress(OSError):
            subprocess.Popen(["xdg-open", str(target)])


# ASCII bracket markers used in list rows ---------------------------------------
MARK_OK = "[+]"
MARK_FAIL = "[x]"
MARK_PENDING = "[?]"
MARK_NO = "[-]"
MARK_DONE = "[x]"
MARK_TICK = "[x]"
