"""Uninstall the Vulkan compatibility layer.

Removes the three DXVK files from the game folder and restores the pre-install
config snapshot. Pre-existing `.backup` and `.bak` chains are preserved on disk
as orphans so a future re-install can use them.

Behavior per file (e.g. `d3d9.dll`):
  1. If `<name>.backup[.N]` chain exists -> restore newest -> live position.
  2. Else if live file exists -> unlink.
  3. Else -> no-op.

Never raises. Returns an `UninstallResult` carrying per-file outcomes and any
captured `OSError`s so the UI can report them.
"""
from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from core.backup_manager import restore_backup
from core.vulkan_installer import VULKAN_FILES, find_latest_backup

logger = logging.getLogger(__name__)


@dataclass
class FileOutcome:
    name: str
    action: str  # "restored_from_backup" | "removed" | "skipped"
    error: str | None = None


@dataclass
class UninstallResult:
    vulkan_outcomes: list[FileOutcome] = field(default_factory=list)
    config_restored: bool = False
    config_action: str = "skipped"  # "restored" | "no_backup" | "skipped"
    errors: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors) or any(o.error for o in self.vulkan_outcomes)

    def summary_lines(self) -> list[str]:
        out: list[str] = []
        for o in self.vulkan_outcomes:
            if o.error:
                out.append(f"  ! {o.name}: {o.error}")
            else:
                out.append(f"  - {o.name}: {o.action}")
        if self.config_action == "restored":
            out.append("  - config: restored from backup")
        elif self.config_action == "no_backup":
            out.append("  - config: no backup found; left as-is")
        return out


def _uninstall_one(name: str, game_dir: Path) -> FileOutcome:
    target = game_dir / name
    if not target.is_file():
        return FileOutcome(name=name, action="skipped")

    backup = find_latest_backup(target)
    if backup is not None:
        try:
            shutil.move(str(backup), str(target))
            logger.info("Uninstall: restored %s from %s", target, backup)
            return FileOutcome(name=name, action="restored_from_backup")
        except OSError as exc:
            msg = f"could not restore from {backup.name}: {exc}"
            logger.warning("Uninstall: %s (%s)", target, msg)
            return FileOutcome(name=name, action="skipped", error=msg)

    try:
        target.unlink()
        logger.info("Uninstall: removed %s", target)
        return FileOutcome(name=name, action="removed")
    except OSError as exc:
        msg = f"could not remove: {exc}"
        logger.warning("Uninstall: %s (%s)", target, msg)
        return FileOutcome(name=name, action="skipped", error=msg)


def uninstall_vulkan_files(game_dir: Path | None) -> list[FileOutcome]:
    """Restore-or-delete all DXVK files under `game_dir`. Returns per-file outcomes."""
    if game_dir is None or not game_dir.is_dir():
        return []
    return [_uninstall_one(name, game_dir) for name in VULKAN_FILES]


def uninstall_config(config_path: Path | None) -> tuple[bool, str]:
    """Restore `config_path` from its `.bak` chain. Returns (restored, action)."""
    if config_path is None or not config_path.is_file():
        return False, "skipped"
    if restore_backup(config_path):
        return True, "restored"
    return False, "no_backup"


def uninstall_all(
    game_dir: Path | None,
    config_path: Path | None,
) -> UninstallResult:
    """Combined: DXVK files + config. Never raises."""
    result = UninstallResult()
    result.vulkan_outcomes = uninstall_vulkan_files(game_dir)
    result.config_restored, result.config_action = uninstall_config(config_path)
    for o in result.vulkan_outcomes:
        if o.error:
            result.errors.append(f"{o.name}: {o.error}")
    return result
