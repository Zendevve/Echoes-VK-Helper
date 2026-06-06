"""Wizard controller and shared state.

Pages are pre-instantiated and stacked; the controller switches between them with
tkraise(). A fixed bottom navigation bar is provided by the controller so page
implementations only render their content.

Design system: OpenCode-faithful. Berkeley Mono typography (Consolas fallback on
Windows), warm cream canvas, ASCII bracket glyphs, 4px radius on interactive
elements, 0px on containers. The single dark surface (INK) is reserved for the
welcome-page hero TUI mockup and the install-page aborted state.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import customtkinter as ctk

logger = logging.getLogger(__name__)


# --- Brand & accent ---------------------------------------------------------
INK = "#f5f5f5"
INK_DEEP = "#ffffff"
ON_PRIMARY = "#1a1a1a"
ON_DARK = "#f5f5f5"

# --- Surface -----------------------------------------------------------------
CANVAS = "#1a1a1a"
SURFACE_SOFT = "#202020"
SURFACE_CARD = "#252525"
SURFACE_DARK = "#0d0d0d"
SURFACE_DARK_ELEVATED = "#2a2a2a"
HAIRLINE = "#2a2a2a"
HAIRLINE_STRONG = "#4a4a4a"

# --- Text ladder -------------------------------------------------------------
CHARCOAL = "#e0e0e0"
BODY = "#d0d0d0"
MUTE = "#8a8a8a"
STONE = "#787878"
ASH = "#5a5a5a"

# --- Semantic (Apple HIG ramp) -----------------------------------------------
ACCENT = "#007aff"
ACCENT_HOVER = "#339cff"
ACCENT_ACTIVE = "#66b3ff"
DANGER = "#ff3b30"
DANGER_HOVER = "#ff5e54"
DANGER_ACTIVE = "#ff8077"
WARNING = "#ff9f0a"
WARNING_HOVER = "#ffb340"
WARNING_ACTIVE = "#ffc773"
SUCCESS = "#30d158"
SUCCESS_HOVER = "#5ddc7d"
SUCCESS_ACTIVE = "#8ae6a3"

# --- Typography --------------------------------------------------------------
# Berkeley Mono is the brand face. On Windows it is not preinstalled, so the
# fallback is Consolas, which is monospaced, widely deployed, and renders the
# ASCII block characters correctly. To enable Berkeley, install the font and
# change this constant to "Berkeley Mono".
FONT_FAMILY = "Consolas"

DISPLAY_XL = 38
HEADING_MD = 16
BODY_MD = 16
BODY_STRONG_W = 500
BUTTON_MD = 16
CAPTION_MD = 14

# --- Radius ------------------------------------------------------------------
ROUNDED_NONE = 0
ROUNDED_SM = 4
ROUNDED_FULL = 9999

# --- Layout ------------------------------------------------------------------
SECTION_GAP = 96
BRAND_BAR_HEIGHT = 56
NAV_BAR_HEIGHT = 72

PAGE_NAMES: tuple[str, ...] = (
    "welcome",
    "detection",
    "summary",
    "install",
    "completion",
)

PAGE_LABELS: dict[str, str] = {
    "welcome": "Welcome",
    "detection": "Detection",
    "summary": "Review",
    "install": "Install",
    "completion": "Done",
}


@dataclass
class WizardState:
    config_path: Path | None = None
    game_path: Path | None = None
    resolution: tuple[int, int] | None = None
    detection_errors: list[str] = field(default_factory=list)
    needs_elevation: bool = False
    backup_paths: list[str] = field(default_factory=list)
    validation: dict[str, Any] | None = None
    install_succeeded: bool = False
    gpu_check_done: bool = False
    gpu_check_ok: bool = False
    vulkan_install_result: dict[str, Any] | None = None
    aborted: bool = False
    _resume_install: bool = False
    _elevated_attempted: bool = False


def font(size: int = BODY_MD, weight: str = "normal") -> ctk.CTkFont:
    """Build a brand monospace font. weight: 'normal' | 'bold'."""
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)


def heading_font(size: int = HEADING_MD) -> ctk.CTkFont:
    return font(size, "bold")


WORDMARK = "[ EVH ]"


class WizardController(ctk.CTk):
    """Top-level application window. Owns the page stack, brand bar, and nav bar."""

    def __init__(self, initial_state: WizardState | None = None) -> None:
        super().__init__()

        self.title("Echoes Vulkan Helper")
        self.geometry("960x680")
        self.minsize(860, 640)
        self.configure(fg_color=CANVAS)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.context: WizardState = initial_state or WizardState()
        self._pages: dict[str, ctk.CTkFrame] = {}
        self._current_index: int = 0
        self._nav_callbacks: dict[str, Callable[[], None]] = {}

        self._restore_persisted_paths()
        self._build_layout()
        self._build_pages()
        self._build_brand_bar()
        self._build_nav_bar()
        self._show_initial_page()

    def _restore_persisted_paths(self) -> None:
        """Reload last-known config + game paths from disk so the user does
        not have to re-browse on every run. Stale paths are dropped silently
        and auto-detection runs as normal.
        """
        try:
            from wizard.persistence import apply_to_context, load_state

            data = load_state()
            if data:
                apply_to_context(self.context, data)
        except Exception as exc:
            logger.warning("Persisted state restore failed: %s", exc)

    def _show_initial_page(self) -> None:
        if getattr(self.context, "_resume_install", False):
            self._show_page(PAGE_NAMES.index("install"))
            self.context._resume_install = False
        else:
            self._show_page(0)

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        self._brand_bar = ctk.CTkFrame(
            self,
            fg_color=CANVAS,
            corner_radius=ROUNDED_NONE,
            height=BRAND_BAR_HEIGHT,
            border_width=1,
            border_color=HAIRLINE,
        )
        self._brand_bar.grid(row=0, column=0, sticky="ew")
        self._brand_bar.grid_propagate(False)
        self._brand_bar.grid_columnconfigure(0, weight=0)
        self._brand_bar.grid_columnconfigure(1, weight=1)
        self._brand_bar.grid_columnconfigure(2, weight=0)

        self._content = ctk.CTkFrame(self, fg_color=CANVAS, corner_radius=ROUNDED_NONE)
        self._content.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        self._nav_bar = ctk.CTkFrame(
            self,
            fg_color=CANVAS,
            corner_radius=ROUNDED_NONE,
            height=NAV_BAR_HEIGHT,
            border_width=1,
            border_color=HAIRLINE,
        )
        self._nav_bar.grid(row=2, column=0, sticky="ew")
        self._nav_bar.grid_propagate(False)
        self._nav_bar.grid_columnconfigure(0, weight=0)
        self._nav_bar.grid_columnconfigure(1, weight=1)
        self._nav_bar.grid_columnconfigure(2, weight=0)
        self._nav_bar.grid_columnconfigure(3, weight=0)

    def _build_brand_bar(self) -> None:
        wordmark = ctk.CTkLabel(
            self._brand_bar,
            text=WORDMARK,
            font=font(size=20, weight="bold"),
            text_color=INK,
            anchor="w",
        )
        wordmark.grid(row=0, column=0, sticky="w", padx=(20, 12), pady=8)

        name_lbl = ctk.CTkLabel(
            self._brand_bar,
            text="Echoes Vulkan Helper",
            font=heading_font(size=HEADING_MD),
            text_color=INK,
            anchor="w",
        )
        name_lbl.grid(row=0, column=1, sticky="w", padx=(4, 12))

        version_lbl = ctk.CTkLabel(
            self._brand_bar,
            text="v0.1.0  ·  DXVK 2.x",
            font=font(size=CAPTION_MD),
            text_color=MUTE,
            anchor="e",
        )
        version_lbl.grid(row=0, column=2, sticky="e", padx=(12, 20))

    def _build_pages(self) -> None:
        from wizard.pages.completion_page import CompletionPage
        from wizard.pages.detection_page import DetectionPage
        from wizard.pages.install_page import InstallPage
        from wizard.pages.summary_page import SummaryPage
        from wizard.pages.welcome_page import WelcomePage

        page_classes: dict[str, type] = {
            "welcome": WelcomePage,
            "detection": DetectionPage,
            "summary": SummaryPage,
            "install": InstallPage,
            "completion": CompletionPage,
        }

        for name, cls in page_classes.items():
            page = cls(self._content, self)
            page.grid(row=0, column=0, sticky="nsew")
            self._pages[name] = page

    def _build_nav_bar(self) -> None:
        for w in self._nav_bar.winfo_children():
            w.destroy()

        from wizard.pages._common import _wire_button_motion

        self._back_btn = ctk.CTkButton(
            self._nav_bar,
            text="Back",
            width=120,
            height=36,
            fg_color=CANVAS,
            hover_color=CANVAS,
            text_color=INK,
            font=font(size=BUTTON_MD, weight="normal"),
            border_width=1,
            border_color=HAIRLINE_STRONG,
            corner_radius=ROUNDED_SM,
            command=self._on_back,
        )
        _wire_button_motion(self._back_btn, base=CANVAS, hover=SURFACE_SOFT, active=SURFACE_CARD)

        self._step_label = ctk.CTkLabel(
            self._nav_bar,
            text="",
            text_color=MUTE,
            font=font(size=CAPTION_MD),
        )
        self._step_label.grid(row=0, column=1, sticky="w", padx=16)

        self._cancel_btn = ctk.CTkButton(
            self._nav_bar,
            text="Cancel",
            width=120,
            height=36,
            fg_color=CANVAS,
            hover_color=CANVAS,
            text_color=MUTE,
            border_width=1,
            border_color=HAIRLINE_STRONG,
            corner_radius=ROUNDED_SM,
            font=font(size=BUTTON_MD, weight="normal"),
            command=self._on_nav_action,
        )
        _wire_button_motion(self._cancel_btn, base=CANVAS, hover=SURFACE_SOFT, active=SURFACE_CARD)

        self._next_btn = ctk.CTkButton(
            self._nav_bar,
            text="Next",
            width=160,
            height=36,
            fg_color=INK,
            hover_color=INK,
            text_color=ON_PRIMARY,
            font=font(size=BUTTON_MD, weight="bold"),
            corner_radius=ROUNDED_SM,
            command=self._on_next,
        )
        _wire_button_motion(self._next_btn, base=INK, hover=INK_DEEP, active=INK_DEEP)

    def _show_page(self, index: int) -> None:
        if index < 0 or index >= len(PAGE_NAMES):
            return
        self._current_index = index
        name = PAGE_NAMES[index]
        page = self._pages[name]
        page.tkraise()
        page.on_enter(self.context)

        total = len(PAGE_NAMES)
        label = PAGE_LABELS.get(name, name.title())
        self._step_label.configure(text=f"step {index + 1}/{total}  ·  {label.lower()}")

        is_install = name == "install"

        if index == 0 or is_install:
            self._back_btn.grid_forget()
        else:
            self._back_btn.grid(row=0, column=0, padx=(20, 8), pady=18)
            self._back_btn.configure(state="normal")

        if is_install:
            self._cancel_btn.configure(
                text="Abort",
                fg_color=DANGER,
                hover_color=DANGER,
                text_color=ON_PRIMARY,
                border_width=0,
                state="normal",
                font=font(size=BUTTON_MD, weight="bold"),
            )
            from wizard.pages._common import update_button_motion

            update_button_motion(
                self._cancel_btn, base=DANGER, hover=DANGER_HOVER, active=DANGER_ACTIVE
            )
        else:
            self._cancel_btn.configure(
                text="Cancel",
                fg_color=CANVAS,
                hover_color=CANVAS,
                text_color=MUTE,
                border_width=1,
                border_color=HAIRLINE_STRONG,
                state="normal",
                font=font(size=BUTTON_MD, weight="normal"),
            )
            from wizard.pages._common import update_button_motion

            update_button_motion(
                self._cancel_btn, base=CANVAS, hover=SURFACE_SOFT, active=SURFACE_CARD
            )
        self._cancel_btn.grid(row=0, column=2, padx=8, pady=18)

        self._next_btn.configure(state="disabled" if is_install else "normal")
        self._next_btn.grid(row=0, column=3, padx=(8, 20), pady=18)

        if name == "summary":
            self._next_btn.configure(text="Install  >", state="normal")
        elif name == "completion":
            self._next_btn.configure(text="Finish", state="normal")
        else:
            self._next_btn.configure(text="Next  >")

        self._refresh_next_state()

    def _refresh_next_state(self) -> None:
        name = PAGE_NAMES[self._current_index]
        if name == "install":
            return
        page = self._pages[name]
        try:
            ok = page.can_advance()
        except Exception:
            ok = True
        if name == "completion":
            return
        if not ok:
            self._next_btn.configure(state="disabled")
        else:
            if self._next_btn.cget("state") == "disabled":
                self._next_btn.configure(state="normal")

    def _on_back(self) -> None:
        if self._current_index <= 0:
            return
        self._show_page(self._current_index - 1)

    def _on_next(self) -> None:
        name = PAGE_NAMES[self._current_index]
        page = self._pages[name]
        try:
            page.on_exit()
        except Exception as exc:
            logger.exception("on_exit failed on %s: %s", name, exc)

        if name == "completion":
            self.quit()
            return

        self._show_page(self._current_index + 1)

    def _on_nav_action(self) -> None:
        name = PAGE_NAMES[self._current_index]
        if name == "install":
            self._on_abort()
        else:
            self._on_cancel()

    def _on_cancel(self) -> None:
        from tkinter import messagebox

        if not messagebox.askyesno(
            "Quit helper",
            "Quit the helper? Any progress will be lost.",
            parent=self,
        ):
            return
        self.quit()

    def _on_abort(self) -> None:
        from tkinter import messagebox

        if not messagebox.askyesno(
            "Abort install",
            "Abort the installation? Files may be left in a partial state. "
            "You can restore from a backup on the next screen.",
            parent=self,
        ):
            return
        page = self._pages.get("install")
        if page is not None and hasattr(page, "request_abort"):
            page.request_abort()

    def go_next(self) -> None:
        """Public hook for pages that want to advance programmatically."""
        self._on_next()

    def go_to(self, name: str) -> None:
        if name in PAGE_NAMES:
            self._show_page(PAGE_NAMES.index(name))
