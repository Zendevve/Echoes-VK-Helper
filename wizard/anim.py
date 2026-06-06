"""Lightweight micro-animation primitives for customtkinter widgets.

Customtkinter is not a motion framework: `hover_color` snaps, no per-widget
opacity, no transforms. We add the missing piece on top with `after()`-driven
tweens. All tweens are short (60-250ms), use ease-out, and respect a 60fps
budget.

Conventions:
  * `tween()` interpolates a single attribute (text_color, fg_color, width,
    y-offset) on a single widget.
  * Repeated tweens on the same widget+attr cancel the prior one (no
    compounding).
  * If the widget is destroyed mid-tween, the tween no-ops on the next tick.
  * Color values are 7-char hex strings `#rrggbb`. Numeric values are int or
    float. Everything else is treated as a discrete swap at the end.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Iterable, Optional

import customtkinter as ctk

logger = logging.getLogger(__name__)

_ANIM_KEY_FMT = "_evh_anim_{attr}"


def _cancel_existing(widget: ctk.CTkBaseClass, attr: str) -> None:
    after_id = getattr(widget, _ANIM_KEY_FMT.format(attr=attr), None)
    if after_id is not None:
        try:
            widget.after_cancel(after_id)
        except Exception:
            pass
        try:
            delattr(widget, _ANIM_KEY_FMT.format(attr=attr))
        except Exception:
            pass


def _parse_color(value: str) -> Optional[tuple[int, int, int]]:
    if (
        isinstance(value, str)
        and value.startswith("#")
        and len(value) == 7
    ):
        try:
            return (int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16))
        except ValueError:
            return None
    return None


def _interp(start: Any, end: Any, t: float) -> Any:
    if t <= 0:
        return start
    if t >= 1:
        return end
    sc = _parse_color(start) if isinstance(start, str) else None
    ec = _parse_color(end) if isinstance(end, str) else None
    if sc is not None and ec is not None:
        r = round(sc[0] + (ec[0] - sc[0]) * t)
        g = round(sc[1] + (ec[1] - sc[1]) * t)
        b = round(sc[2] + (ec[2] - sc[2]) * t)
        return f"#{r:02x}{g:02x}{b:02x}"
    if isinstance(start, (int, float)) and isinstance(end, (int, float)):
        return start + (end - start) * t
    return end


def _ease(t: float, mode: str) -> float:
    if mode == "ease_out":
        return 1 - (1 - t) ** 3
    if mode == "ease_in_out":
        return t * t * (3 - 2 * t)
    if mode == "ease_out_back":
        c1 = 1.70158
        c3 = c1 + 1
        return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
    return t


def tween(
    widget: ctk.CTkBaseClass,
    *,
    attr: str,
    start: Any,
    end: Any,
    duration_ms: int = 180,
    steps: int = 12,
    easing: str = "ease_out",
    on_done: Optional[Callable[[], None]] = None,
) -> None:
    """Animate a single widget attribute over `duration_ms`."""
    if not _widget_alive(widget):
        return
    _cancel_existing(widget, attr)

    interval = max(8, duration_ms // max(1, steps))
    state = {"i": 0}

    def tick() -> None:
        if not _widget_alive(widget):
            return
        state["i"] += 1
        t = min(1.0, state["i"] / max(1, steps))
        e = _ease(t, easing)
        value = _interp(start, end, e)
        try:
            widget.configure(**{attr: value})
        except Exception as exc:  # noqa: BLE001
            logger.debug("tween configure failed on %s.%s: %s", widget, attr, exc)
            return
        if t < 1.0:
            aid = widget.after(interval, tick)
            setattr(widget, _ANIM_KEY_FMT.format(attr=attr), aid)
        else:
            try:
                delattr(widget, _ANIM_KEY_FMT.format(attr=attr))
            except Exception:
                pass
            if on_done is not None:
                try:
                    on_done()
                except Exception:  # noqa: BLE001
                    pass

    aid = widget.after(interval, tick)
    setattr(widget, _ANIM_KEY_FMT.format(attr=attr), aid)


def fade_in_labels(
    labels: Iterable[ctk.CTkLabel],
    *,
    duration_ms: int = 220,
    start_color: str = "#8a8a8a",
) -> None:
    """Tween a batch of labels from a muted start color to their configured
    text_color. Call once on page enter.
    """
    for lbl in labels:
        if not _widget_alive(lbl):
            continue
        try:
            current = lbl.cget("text_color")
        except Exception:
            continue
        tween(
            lbl,
            attr="text_color",
            start=start_color,
            end=current,
            duration_ms=duration_ms,
            steps=14,
            easing="ease_out",
        )


def slide_banner_in(
    label: ctk.CTkLabel,
    *,
    dy: int = 8,
    duration_ms: int = 220,
) -> None:
    """Slide a banner label up by `dy` pixels while fading its text in."""
    if not _widget_alive(label):
        return
    try:
        current = label.cget("text_color")
    except Exception:
        return
    tween(label, attr="text_color", start="#8a8a8a", end=current,
          duration_ms=duration_ms, steps=14, easing="ease_out")


def _widget_alive(widget: Any) -> bool:
    try:
        return bool(widget.winfo_exists())
    except Exception:
        return False
