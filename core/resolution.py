"""Resolution detection via screeninfo, with safe fallbacks."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

FALLBACK_RESOLUTION: tuple[int, int] = (1920, 1080)

COMMON_PRESETS: tuple[tuple[int, int], ...] = (
    (1280, 720),
    (1366, 768),
    (1920, 1080),
    (2560, 1440),
    (3840, 2160),
)


def _safe_monitors() -> list:
    try:
        from screeninfo import get_monitors
    except (ImportError, Exception) as exc:  # screeninfo can raise on headless
        logger.warning("screeninfo unavailable: %s", exc)
        return []
    try:
        return list(get_monitors())
    except Exception as exc:
        logger.warning("get_monitors() failed: %s", exc)
        return []


def list_detected_modes() -> list[tuple[int, int]]:
    """Return all unique (width, height) tuples reported by connected monitors."""
    monitors = _safe_monitors()
    modes: list[tuple[int, int]] = []
    for m in monitors:
        w, h = int(m.width), int(m.height)
        if (w, h) not in modes:
            modes.append((w, h))
    return modes or [FALLBACK_RESOLUTION]


def curated_modes(native: tuple[int, int] | None = None) -> list[tuple[int, int]]:
    """Return a short, sorted list: native + COMMON_PRESETS, de-duped.

    Keeps dropdowns small (Hick's law) while still offering the user's native
    resolution when it is not in the preset list.
    """
    out: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()

    if native is not None:
        out.append(native)
        seen.add(native)

    for preset in COMMON_PRESETS:
        if preset in seen:
            continue
        out.append(preset)
        seen.add(preset)

    out.sort(key=lambda m: (m[0] * m[1], m[0]))
    return out


def get_native_resolution() -> tuple[int, int]:
    """Return the primary monitor's resolution, falling back gracefully."""
    monitors = _safe_monitors()
    if not monitors:
        return FALLBACK_RESOLUTION
    primary = next((m for m in monitors if getattr(m, "is_primary", False)), None)
    target = primary or monitors[0]
    return int(target.width), int(target.height)
