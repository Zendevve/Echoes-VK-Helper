"""Validation dataclass and the 9-check validation function."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from core.config_manager import read_settings

logger = logging.getLogger(__name__)

VULKAN_FILES: tuple[str, ...] = ("dinput8.ini", "dinput8.dll", "d3d9.dll")


@dataclass
class ValidationResult:
    config_found: bool = False
    backup_found: bool = False
    game_found: bool = False
    settings_applied: bool = False
    vulkan_installed: bool = False
    fullscreen_set: bool = False
    cursor_unconfined: bool = False
    resolution_set: bool = False
    dll_files_present: bool = False

    @property
    def all_passed(self) -> bool:
        return all(
            (
                self.config_found,
                self.backup_found,
                self.game_found,
                self.settings_applied,
                self.vulkan_installed,
                self.fullscreen_set,
                self.cursor_unconfined,
                self.resolution_set,
                self.dll_files_present,
            )
        )

    def failed(self) -> list[str]:
        out: list[str] = []
        if not self.config_found:
            out.append("Config not found")
        if not self.backup_found:
            out.append("No config backup present")
        if not self.game_found:
            out.append("Game installation not found")
        if not self.settings_applied:
            out.append("Recommended settings not applied")
        if not self.vulkan_installed:
            out.append("Vulkan files not fully installed")
        if not self.fullscreen_set:
            out.append("Fullscreen != True")
        if not self.cursor_unconfined:
            out.append("ConfineFullScreenMouseCursor != False")
        if not self.resolution_set:
            out.append("Resolution not set")
        if not self.dll_files_present:
            out.append("One or more DLL files missing")
        return out


def run_validation(
    config_path: Path | None,
    backup_path: Path | None,
    game_path: Path | None,
) -> ValidationResult:
    """Run all 9 checks. Never raises; missing pieces return False."""
    result = ValidationResult()

    if config_path and config_path.is_file():
        result.config_found = True
        try:
            parser = read_settings(config_path)
            sections = parser.sections()
            fullscreen = None
            cursor = None
            resolution = None
            for s in sections:
                if parser.has_option(s, "Fullscreen"):
                    fullscreen = parser.get(s, "Fullscreen", fallback=None)
                if parser.has_option(s, "ConfineFullScreenMouseCursor"):
                    cursor = parser.get(s, "ConfineFullScreenMouseCursor", fallback=None)
                if parser.has_option(s, "Resolution"):
                    resolution = parser.get(s, "Resolution", fallback=None)

            result.fullscreen_set = (fullscreen or "").strip().lower() == "true"
            result.cursor_unconfined = (cursor or "").strip().lower() == "false"
            result.resolution_set = bool(resolution) and "x" in (resolution or "")
            result.settings_applied = (
                result.fullscreen_set and result.cursor_unconfined and result.resolution_set
            )
        except OSError as exc:
            logger.warning("Validation: could not read config: %s", exc)

    if backup_path and backup_path.is_file():
        result.backup_found = True

    if game_path and game_path.is_dir() and (game_path / "lotroclient.exe").is_file():
        result.game_found = True

    if game_path and game_path.is_dir():
        dlls_present = all((game_path / name).is_file() for name in VULKAN_FILES)
        result.dll_files_present = dlls_present
        result.vulkan_installed = dlls_present and (game_path / "dinput8.ini").is_file()

    return result
