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
    BODY,
    CANVAS,
    DANGER,
    HAIRLINE,
    INK,
    MUTE,
    SUCCESS,
    WARNING,
    WizardState,
    font,
    heading_font,
)
from wizard.pages._common import (
    MARK_FAIL,
    MARK_OK,
    MARK_PENDING,
    make_ascii_bullet,
    make_card,
    make_hairline,
    make_install_snippet,
    make_secondary_button,
    make_section_label,
    make_subtitle,
    set_status,
)

if TYPE_CHECKING:
    from wizard.controller import WizardController

logger = logging.getLogger(__name__)


class DetectionPage(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, controller: "WizardController") -> None:
        super().__init__(parent, fg_color=CANVAS, corner_radius=0)
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
        self.grid_rowconfigure(2, weight=0)

        self._build_header(self)
        self._build_body(self)
        self._build_footer(self)

        self._built = True

    def _build_header(self, parent: ctk.CTkFrame) -> None:
        header = ctk.CTkFrame(parent, fg_color=CANVAS, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 8))
        header.grid_columnconfigure(0, weight=1)

        self._section_lbl = make_section_label(header, "[?]  Locate your installation")
        self._section_lbl.grid(row=0, column=0, sticky="ew")
        make_hairline(header).grid(row=1, column=0, sticky="ew", pady=(8, 0))

        self._subtitle_lbl = make_subtitle(
            header,
            "Searching for your Echoes configuration file and game installation. "
            "This usually takes a few seconds.",
        )
        self._subtitle_lbl.grid(row=2, column=0, sticky="ew", pady=(8, 0))

    def _build_body(self, parent: ctk.CTkFrame) -> None:
        body = ctk.CTkFrame(parent, fg_color=CANVAS, corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=8)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=0)
        body.grid_rowconfigure(1, weight=0)
        body.grid_rowconfigure(2, weight=1)

        self.config_card, self.config_status, self.config_path_lbl, self.config_browse_btn = (
            self._build_row(body, "[?]  configuration", "UserPreferences.echoes.ini", row=0)
        )
        self.game_card, self.game_status, self.game_path_lbl, self.game_browse_btn = (
            self._build_row(body, "[?]  game installation", "lotroclient.exe", row=1)
        )

        self.banner = ctk.CTkLabel(
            body,
            text="",
            fg_color=CANVAS,
            text_color=MUTE,
            corner_radius=4,
            padx=12,
            pady=8,
            font=font(size=13),
            anchor="w",
            justify="left",
            wraplength=720,
        )
        self.banner.grid(row=2, column=0, sticky="new", pady=(12, 0))

    def _build_footer(self, parent: ctk.CTkFrame) -> None:
        footer = ctk.CTkFrame(parent, fg_color=CANVAS, corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 24))
        footer.grid_columnconfigure(0, weight=1)

        make_hairline(footer).grid(row=0, column=0, sticky="ew")
        hint = ctk.CTkLabel(
            footer,
            text="[!]  if auto-detect fails, click Browse to point at the file or folder manually.",
            font=font(size=13),
            text_color=MUTE,
            anchor="w",
            justify="left",
        )
        hint.grid(row=1, column=0, sticky="ew", pady=(8, 0))

    def _build_row(
        self,
        parent: ctk.CTkFrame,
        title: str,
        hint: str,
        row: int,
    ) -> tuple[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkLabel, ctk.CTkButton]:
        card = make_card(parent)
        card.grid(row=row, column=0, sticky="ew", pady=8)
        card.grid_columnconfigure(1, weight=1)

        status = ctk.CTkLabel(
            card,
            text=MARK_PENDING,
            width=80,
            font=font(size=15, weight="bold"),
            text_color=MUTE,
        )
        status.grid(row=0, column=0, rowspan=2, padx=(16, 12), pady=14)

        title_lbl = ctk.CTkLabel(
            card,
            text=title,
            font=heading_font(size=15),
            text_color=INK,
            anchor="w",
        )
        title_lbl.grid(row=0, column=1, sticky="ew", padx=8, pady=(14, 0))

        path_lbl = ctk.CTkLabel(
            card,
            text=f"Searching for {hint}...",
            font=font(size=13),
            text_color=BODY,
            anchor="w",
            wraplength=520,
            justify="left",
        )
        path_lbl.grid(row=1, column=1, sticky="ew", padx=8, pady=(0, 14))

        browse_btn = make_secondary_button(card, "Browse", lambda: None)
        browse_btn.configure(state="disabled")
        browse_btn.grid(row=0, column=2, rowspan=2, padx=(8, 16), pady=14)
        return card, status, path_lbl, browse_btn

    def on_enter(self, state: WizardState) -> None:
        self._can_advance = False
        self._reset_banner()
        self.controller.context.needs_elevation = False

        from wizard.anim import fade_in_labels, slide_banner_in
        fade_in_labels([self._section_lbl, self._subtitle_lbl])
        slide_banner_in(self.banner)

        config_known = bool(state.config_path and state.config_path.is_file())
        game_known = bool(state.game_path and state.game_path.is_dir())

        if config_known:
            self._set_config_found(state.config_path)
        else:
            set_status(self.config_status, MARK_PENDING, MUTE)
            self.config_path_lbl.configure(text="Looking for UserPreferences.echoes.ini...")

        if game_known:
            from core.game_detector import is_writable as _iw
            self._set_game_found(state.game_path, writable=_iw(state.game_path))
        else:
            set_status(self.game_status, MARK_PENDING, MUTE)
            self.game_path_lbl.configure(text="Looking for lotroclient.exe...")

        if config_known and game_known and state.resolution is not None:
            return

        self._start_detection()

    def _reset_banner(self) -> None:
        self.banner.configure(text="", text_color=MUTE)

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
                    elif not self.controller.context.config_path:
                        self._set_config_missing()
                elif kind == "game":
                    if value:
                        self._set_game_found(value, writable=None)
                    elif not self.controller.context.game_path:
                        self._set_game_missing()
                elif kind == "writable":
                    self._set_writability(value)
                elif kind == "resolution":
                    if (
                        value
                        and not self.controller.context.resolution
                    ):
                        self.controller.context.resolution = value
                        self._persist()
                elif kind == "error":
                    self.banner.configure(
                        text=f"[x]  detection error: {value}",
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
        set_status(self.config_status, MARK_OK, SUCCESS)
        self.config_path_lbl.configure(text=str(path))
        self.config_browse_btn.configure(state="normal", command=self._browse_config)
        self._persist()
        self._evaluate_advance()

    def _set_config_missing(self) -> None:
        self.controller.context.config_path = None
        set_status(self.config_status, MARK_FAIL, DANGER)
        self.config_path_lbl.configure(text="UserPreferences.echoes.ini was not found.")
        self.config_browse_btn.configure(state="normal", command=self._browse_config)
        self._evaluate_advance()

    def _set_game_found(self, path: Path, writable: bool | None) -> None:
        self.controller.context.game_path = path
        set_status(self.game_status, MARK_OK, SUCCESS)
        self.game_path_lbl.configure(text=str(path / "lotroclient.exe"))
        self.game_browse_btn.configure(state="normal", command=self._browse_game)
        if writable is not None:
            self._set_writability(writable)
        self._persist()
        self._evaluate_advance()

    def _set_game_missing(self) -> None:
        self.controller.context.game_path = None
        set_status(self.game_status, MARK_FAIL, DANGER)
        self.game_path_lbl.configure(text="lotroclient.exe was not found.")
        self.game_browse_btn.configure(state="normal", command=self._browse_game)
        self._evaluate_advance()

    def _set_writability(self, writable: bool) -> None:
        ctx = self.controller.context
        ctx.needs_elevation = not writable
        from wizard.anim import slide_banner_in
        if writable:
            self.banner.configure(
                text="[+]  game folder is writable, no elevation needed",
                text_color=MUTE,
            )
        else:
            self.banner.configure(
                text="[!]  game folder is read-only. the helper will restart as administrator before installing.",
                text_color="#cc7f08",
            )
        slide_banner_in(self.banner)

    def _evaluate_advance(self) -> None:
        s = self.controller.context
        self._can_advance = bool(s.config_path and s.config_path.is_file() and s.game_path and s.game_path.is_dir())
        if self._can_advance:
            self.controller._refresh_next_state()

    def _browse_config(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose UserPreferences.echoes.ini",
            filetypes=[("Echoes config", "UserPreferences.echoes.ini"),
                       ("All files", "*.*")],
        )
        if not path:
            return
        p = Path(path)
        if not p.is_file():
            self._set_config_missing()
            return
        if p.name.lower() != "userpreferences.echoes.ini":
            from wizard.anim import slide_banner_in
            self.banner.configure(
                text=f"[!]  please pick UserPreferences.echoes.ini, not '{p.name}'",
                text_color=WARNING,
            )
            slide_banner_in(self.banner)
            return
        self._set_config_found(p)

    def _persist(self) -> None:
        try:
            from wizard.persistence import save_state

            save_state(self.controller.context)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to persist detection state: %s", exc)

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
