"""Wizard controller and shared state.

Pages are pre-instantiated and stacked; the controller switches between them with
tkraise(). A fixed bottom navigation bar is provided by the controller so page
implementations only render their content.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import customtkinter as ctk

logger = logging.getLogger(__name__)

ACCENT = "#8A2BE2"
ACCENT_HOVER = "#9d4ee8"
BG_DARK = "#1a1a1a"
SURFACE = "#2a2a2a"
SURFACE_HOVER = "#3a3a3a"
TEXT = "#ffffff"
TEXT_MUTED = "#a0a0a0"
SUCCESS = "#22c55e"
DANGER = "#ef4444"
DANGER_HOVER = "#dc2626"

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
    config_path: Optional[Path] = None
    game_path: Optional[Path] = None
    resolution: Optional[tuple[int, int]] = None
    detection_errors: list[str] = field(default_factory=list)
    needs_elevation: bool = False
    backup_paths: list[str] = field(default_factory=list)
    validation: Optional[dict[str, Any]] = None
    install_succeeded: bool = False
    gpu_check_done: bool = False
    gpu_check_ok: bool = False
    vulkan_install_result: Optional[dict[str, Any]] = None
    aborted: bool = False
    _resume_install: bool = False
    _elevated_attempted: bool = False


class WizardController(ctk.CTk):
    """Top-level application window. Owns the page stack and the nav bar."""

    def __init__(self, initial_state: Optional[WizardState] = None) -> None:
        super().__init__()

        self.title("Echoes Vulkan Helper")
        self.geometry("780x560")
        self.minsize(720, 520)
        self.configure(fg_color=BG_DARK)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.context: WizardState = initial_state or WizardState()
        self._pages: dict[str, ctk.CTkFrame] = {}
        self._current_index: int = 0
        self._nav_callbacks: dict[str, Callable[[], None]] = {}

        self._build_layout()
        self._build_pages()
        self._build_nav_bar()
        self._show_initial_page()

    def _show_initial_page(self) -> None:
        if getattr(self.context, "_resume_install", False):
            self._show_page(PAGE_NAMES.index("install"))
            self.context._resume_install = False
        else:
            self._show_page(0)

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self._content = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        self._content.grid(row=0, column=0, sticky="nsew", padx=24, pady=(24, 0))
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        self._nav_bar = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0, height=72)
        self._nav_bar.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        self._nav_bar.grid_columnconfigure(0, weight=1)
        self._nav_bar.grid_propagate(False)

    def _build_pages(self) -> None:
        from wizard.pages.welcome_page import WelcomePage
        from wizard.pages.detection_page import DetectionPage
        from wizard.pages.summary_page import SummaryPage
        from wizard.pages.install_page import InstallPage
        from wizard.pages.completion_page import CompletionPage

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

        self._nav_bar.grid_columnconfigure(0, weight=0)
        self._nav_bar.grid_columnconfigure(1, weight=1)
        self._nav_bar.grid_columnconfigure(2, weight=0)
        self._nav_bar.grid_columnconfigure(3, weight=0)

        self._back_btn = ctk.CTkButton(
            self._nav_bar,
            text="Back",
            width=120,
            height=44,
            fg_color=SURFACE_HOVER,
            hover_color="#4a4a4a",
            text_color=TEXT,
            command=self._on_back,
        )

        self._step_label = ctk.CTkLabel(
            self._nav_bar,
            text="",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=13),
        )
        self._step_label.grid(row=0, column=1, sticky="w", padx=16)

        self._cancel_btn = ctk.CTkButton(
            self._nav_bar,
            text="Cancel",
            width=120,
            height=44,
            fg_color="transparent",
            hover_color=SURFACE_HOVER,
            text_color=TEXT_MUTED,
            border_width=1,
            border_color=SURFACE_HOVER,
            command=self._on_nav_action,
        )

        self._next_btn = ctk.CTkButton(
            self._nav_bar,
            text="Next",
            width=160,
            height=44,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_next,
        )

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
        self._step_label.configure(text=f"Step {index + 1} of {total}  -  {label}")

        is_install = name == "install"

        if index == 0 or is_install:
            self._back_btn.grid_remove()
        else:
            self._back_btn.grid(row=0, column=0, padx=(20, 8), pady=14)
            self._back_btn.configure(state="normal")

        if is_install:
            self._cancel_btn.configure(
                text="Abort",
                fg_color=DANGER,
                hover_color=DANGER_HOVER,
                text_color=TEXT,
                border_width=0,
                state="normal",
            )
        else:
            self._cancel_btn.configure(
                text="Cancel",
                fg_color="transparent",
                hover_color=SURFACE_HOVER,
                text_color=TEXT_MUTED,
                border_width=1,
                border_color=SURFACE_HOVER,
                state="normal",
            )
        self._cancel_btn.grid(row=0, column=2, padx=8, pady=14)

        self._next_btn.configure(state="disabled" if is_install else "normal")
        self._next_btn.grid(row=0, column=3, padx=(8, 20), pady=14)

        if name == "summary":
            self._next_btn.configure(text="Install", state="normal")
        elif name == "completion":
            self._next_btn.configure(text="Finish", state="normal")
        else:
            self._next_btn.configure(text="Next")

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
