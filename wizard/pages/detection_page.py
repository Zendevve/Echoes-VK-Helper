"""Step 2 - Detection page (auto-detect config + game + writability)."""
from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path
from tkinter import filedialog
from typing import TYPE_CHECKING

import customtkinter as ctk

from wizard.controller import (
    BG_DARK,
    DANGER,
    SUCCESS,
    SURFACE,
    SURFACE_HOVER,
    TEXT,
    TEXT_MUTED,
    WizardState,
)
from wizard.pages._common import make_card, make_subtitle, make_title

if TYPE_CHECKING:
    from wizard.controller import WizardController

logger = logging.getLogger(__name__)


class DetectionPage(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, controller: "WizardController") -> None:
        super().__init__(parent, fg_color=BG_DARK, corner_radius=0)
        self.controller = controller
        self._q: queue.Queue = queue.Queue()
        self._worker: threading.Thread | None = None
        self._built = False
        self._can_advance = False
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.grid_columnconfigure(0, weight=1)

        make_title(header, "Locate your installation").grid(row=0, column=0, sticky="ew", padx=8)
        make_subtitle(
            header,
            "Searching for your Echoes configuration file and game installation. "
            "This usually takes a few seconds.",
        ).grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 0))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=0)
        body.grid_rowconfigure(1, weight=0)
        body.grid_rowconfigure(2, weight=1)

        self.config_card, self.config_status, self.config_path_lbl, self.config_browse_btn = (
            self._build_row(body, "Configuration", "UserPreferences.echoes.ini", row=0)
        )
        self.game_card, self.game_status, self.game_path_lbl, self.game_browse_btn = (
            self._build_row(body, "Game installation", "lotroclient.exe", row=1)
        )

        self.banner = ctk.CTkLabel(
            body,
            text="",
            fg_color=SURFACE,
            text_color=TEXT_MUTED,
            corner_radius=10,
            padx=14,
            pady=10,
            anchor="w",
        )
        self.banner.grid(row=2, column=0, sticky="new", padx=8, pady=(8, 0))

        self._built = True

    def _build_row(
        self,
        parent: ctk.CTkFrame,
        title: str,
        hint: str,
        row: int,
    ) -> tuple[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkLabel, ctk.CTkButton]:
        card = make_card(parent)
        card.grid(row=row, column=0, sticky="ew", padx=8, pady=6)
        card.grid_columnconfigure(1, weight=1)

        status = ctk.CTkLabel(
            card,
            text="...",
            width=120,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_MUTED,
        )
        status.grid(row=0, column=0, rowspan=2, padx=(16, 12), pady=14)

        title_lbl = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=TEXT,
            anchor="w",
        )
        title_lbl.grid(row=0, column=1, sticky="ew", padx=8, pady=(14, 0))

        path_lbl = ctk.CTkLabel(
            card,
            text=f"Searching for {hint}...",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        path_lbl.grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 14))

        browse_btn = ctk.CTkButton(
            card,
            text="Browse",
            width=110,
            height=36,
            fg_color=SURFACE_HOVER,
            hover_color="#4a4a4a",
            text_color=TEXT,
            state="disabled",
        )
        browse_btn.grid(row=0, column=2, rowspan=2, padx=(8, 16), pady=14)
        return card, status, path_lbl, browse_btn

    def on_enter(self, state: WizardState) -> None:
        self._can_advance = False
        self._reset_banner()
        self.controller.context.needs_elevation = False
        if state.config_path and state.config_path.is_file():
            self._set_config_found(state.config_path)
        else:
            self.config_status.configure(text="Searching...", text_color=TEXT_MUTED)
            self.config_path_lbl.configure(text="Looking for UserPreferences.echoes.ini...")

        if state.game_path and state.game_path.is_dir():
            from core.game_detector import is_writable as _iw
            self._set_game_found(state.game_path, writable=_iw(state.game_path))
        else:
            self.game_status.configure(text="Searching...", text_color=TEXT_MUTED)
            self.game_path_lbl.configure(text="Looking for lotroclient.exe...")

        self._start_detection()

    def _reset_banner(self) -> None:
        self.banner.configure(text="", text_color=TEXT_MUTED)

    def on_exit(self) -> None:
        return None

    def can_advance(self) -> bool:
        return self._can_advance

    def _start_detection(self) -> None:
        from core.config_manager import find_config
        from core.game_detector import find_game_installation, is_writable
        from core.resolution import get_native_resolution

        def worker() -> None:
            try:
                cfg = find_config()
                self._q.put(("config", cfg))
                game = find_game_installation()
                self._q.put(("game", game))
                if game:
                    writable = is_writable(game)
                    self._q.put(("writable", writable))
                self._q.put(("resolution", get_native_resolution()))
            except Exception as exc:  # noqa: BLE001
                logger.exception("Detection worker failed: %s", exc)
                self._q.put(("error", exc))

        self._worker = threading.Thread(target=worker, name="detect", daemon=True)
        self._worker.start()
        self.after(120, self._drain)

    def _drain(self) -> None:
        try:
            while True:
                kind, value = self._q.get_nowait()
                if kind == "config":
                    if value:
                        self._set_config_found(value)
                    else:
                        self._set_config_missing()
                elif kind == "game":
                    if value:
                        self._set_game_found(value, writable=None)
                    else:
                        self._set_game_missing()
                elif kind == "writable":
                    self._set_writability(value)
                elif kind == "resolution":
                    self.controller.context.resolution = value
                elif kind == "error":
                    self.banner.configure(
                        text=f"Detection error: {value}",
                        text_color=DANGER,
                    )
        except queue.Empty:
            pass

        if self._worker and self._worker.is_alive():
            self.after(120, self._drain)
        else:
            self._evaluate_advance()

    def _set_config_found(self, path: Path) -> None:
        self.controller.context.config_path = path
        self.config_status.configure(text="FOUND", text_color=SUCCESS)
        self.config_path_lbl.configure(text=str(path))
        self.config_browse_btn.configure(state="normal", command=self._browse_config)
        self._evaluate_advance()

    def _set_config_missing(self) -> None:
        self.controller.context.config_path = None
        self.config_status.configure(text="NOT FOUND", text_color=DANGER)
        self.config_path_lbl.configure(text="UserPreferences.echoes.ini was not found.")
        self.config_browse_btn.configure(state="normal", command=self._browse_config)
        self._evaluate_advance()

    def _set_game_found(self, path: Path, writable: bool | None) -> None:
        self.controller.context.game_path = path
        self.game_status.configure(text="FOUND", text_color=SUCCESS)
        self.game_path_lbl.configure(text=str(path / "lotroclient.exe"))
        self.game_browse_btn.configure(state="normal", command=self._browse_game)
        if writable is not None:
            self._set_writability(writable)
        self._evaluate_advance()

    def _set_game_missing(self) -> None:
        self.controller.context.game_path = None
        self.game_status.configure(text="NOT FOUND", text_color=DANGER)
        self.game_path_lbl.configure(text="lotroclient.exe was not found.")
        self.game_browse_btn.configure(state="normal", command=self._browse_game)
        self._evaluate_advance()

    def _set_writability(self, writable: bool) -> None:
        ctx = self.controller.context
        ctx.needs_elevation = not writable
        if writable:
            self.banner.configure(
                text="Game folder is writable. No elevation needed.",
                text_color=TEXT_MUTED,
            )
        else:
            self.banner.configure(
                text="Game folder is read-only. The helper will restart with admin rights before installing.",
                text_color="#fbbf24",
            )

    def _evaluate_advance(self) -> None:
        s = self.controller.context
        self._can_advance = bool(s.config_path and s.config_path.is_file() and s.game_path and s.game_path.is_dir())
        if self._can_advance:
            self.controller._refresh_next_state()

    def _browse_config(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose UserPreferences.echoes.ini",
            filetypes=[("Echoes config", "*.ini"), ("All files", "*.*")],
        )
        if path:
            p = Path(path)
            if p.is_file():
                self._set_config_found(p)
            else:
                self._set_config_missing()

    def _browse_game(self) -> None:
        path = filedialog.askdirectory(title="Choose the folder containing lotroclient.exe")
        if not path:
            return
        p = Path(path)
        if (p / "lotroclient.exe").is_file():
            from core.game_detector import is_writable

            self._set_game_found(p, writable=is_writable(p))
        else:
            self._set_game_missing()
