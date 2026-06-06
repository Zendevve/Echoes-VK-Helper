"""Install the bundled Vulkan compatibility files into the game directory."""
from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from core.backup_manager import create_backup
from core.paths import resource_path

logger = logging.getLogger(__name__)

VULKAN_FILES: tuple[str, ...] = ("dinput8.ini", "dinput8.dll", "d3d9.dll")
BACKUP_SUFFIX = ".backup"


@dataclass
class VulkanInstallResult:
    """Record of every mutation made during install, for rollback."""
    installed: list[Path] = field(default_factory=list)
    rotated_backups: list[Path] = field(default_factory=list)

    def is_clean(self) -> bool:
        return not self.installed and not self.rotated_backups


def vulkan_source_dir() -> Path:
    return resource_path("assets") / "vulkan"


def find_latest_backup(target: Path) -> Path | None:
    """Return the most recent `.backup[.N]` for `target`, or None if missing.

    Walks the rotation chain: target.backup, target.backup.1, target.backup.2, ...
    """
    candidates = [target.with_suffix(target.suffix + BACKUP_SUFFIX)]
    candidates += [target.with_suffix(target.suffix + f"{BACKUP_SUFFIX}.{i}") for i in range(1, 10)]
    for cand in candidates:
        if cand.is_file():
            return cand
    return None


class VulkanInstallError(OSError):
    """Raised when install_vulkan fails partway. Carries the partial result."""

    def __init__(self, original: BaseException, result: VulkanInstallResult) -> None:
        super().__init__(str(original))
        self.result = result
        self.__cause__ = original


def install_vulkan(game_dir: Path, source_dir: Path | None = None) -> VulkanInstallResult:
    """Copy the three Vulkan files into `game_dir`.

    Pre-existing files are renamed to `<name>.backup` (rotated) before being overwritten.
    Raises `VulkanInstallError` on first failure; the exception carries the partial
    `VulkanInstallResult` so the caller can call `rollback(result)`.
    """
    src_root = source_dir or vulkan_source_dir()
    if not src_root.is_dir():
        raise FileNotFoundError(f"Vulkan source directory not found: {src_root}")
    if not game_dir.is_dir():
        raise FileNotFoundError(f"Game directory not found: {game_dir}")

    game_dir.mkdir(parents=True, exist_ok=True)

    result = VulkanInstallResult()

    for filename in VULKAN_FILES:
        src = src_root / filename
        dst = game_dir / filename
        try:
            if not src.is_file():
                raise FileNotFoundError(f"Missing bundled asset: {src}")
            if dst.is_file():
                backup = create_backup(dst, suffix=BACKUP_SUFFIX)
                result.rotated_backups.append(backup)
                logger.info("Existing %s backed up to %s", dst.name, backup)
            shutil.copy2(src, dst)
            result.installed.append(dst)
            logger.info("Installed %s -> %s", src, dst)
        except OSError as exc:
            raise VulkanInstallError(exc, result) from exc

    return result


def rollback(result: VulkanInstallResult) -> None:
    """Undo a partial install. Best-effort: never raises.

    Pairs each `installed` entry with its corresponding `rotated_backups` entry
    by install order: rotated_backups[i] is the .backup that replaced
    installed[i] before the new file was copied. If the backup still exists,
    it is moved back over the installed file. Any installed entries that had
    no matching backup (or whose backup was lost) are unlinked.
    """
    incomplete = False

    pairs = min(len(result.installed), len(result.rotated_backups))
    for i in range(pairs):
        backup = result.rotated_backups[i]
        original = result.installed[i]
        try:
            if backup.is_file():
                shutil.move(str(backup), str(original))
                logger.info("Rollback: restored %s -> %s", backup, original)
            else:
                if original.is_file():
                    original.unlink()
                    logger.info("Rollback: removed %s (backup missing)", original)
                incomplete = True
        except OSError as exc:
            logger.warning("Rollback failed to restore %s: %s", backup, exc)
            incomplete = True

    for j in range(pairs, len(result.installed)):
        dst = result.installed[j]
        try:
            if dst.is_file():
                dst.unlink()
                logger.info("Rollback: removed %s", dst)
        except OSError as exc:
            logger.warning("Rollback failed to remove %s: %s", dst, exc)
            incomplete = True

    for j in range(pairs, len(result.rotated_backups)):
        backup = result.rotated_backups[j]
        if backup.is_file():
            try:
                backup.unlink()
                logger.info("Rollback: removed orphan backup %s", backup)
            except OSError as exc:
                logger.warning("Rollback failed to remove orphan %s: %s", backup, exc)
                incomplete = True
        else:
            incomplete = True

    if incomplete:
        logger.warning(
            "Rollback incomplete: game folder may be in an inconsistent state; "
            "see logs for details."
        )
