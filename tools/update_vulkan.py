"""Update the bundled Vulkan / DXVK compatibility files from a provider zip.

Usage:
    python tools/update_vulkan.py path/to/dxvk-2.4-gpl.zip
    python tools/update_vulkan.py --check path/to/dxvk-2.4-gpl.zip
    python tools/update_vulkan.py --rollback
    python tools/update_vulkan.py --dest assets/vulkan path/to/foo.zip

The provider's zip is expected to contain EXACTLY these three files at the
archive root: dinput8.dll, d3d9.dll, dinput8.ini. Any other entry causes the
script to refuse the install - a stale or unrelated file in the archive is
the most common way an update silently breaks.

Run this with the helper EXE closed - Windows will refuse to overwrite a DLL
that's currently mapped into a running process.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

REQUIRED_FILES: tuple[str, ...] = ("dinput8.dll", "d3d9.dll", "dinput8.ini")
PREVIOUS_DIRNAME = ".previous"
MANIFEST_NAME = "manifest.json"
MIN_SIZE_RATIO = 0.5


@dataclass
class FileInfo:
    name: str
    size: int
    sha256: str

    def to_dict(self) -> dict:
        return {"name": self.name, "size": self.size, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, d: dict) -> FileInfo:
        return cls(name=d["name"], size=int(d["size"]), sha256=d["sha256"])


class UpdateError(RuntimeError):
    pass


def _hash_file(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _info_for(path: Path) -> FileInfo:
    return FileInfo(name=path.name, size=path.stat().st_size, sha256=_hash_file(path))


def verify_zip(zip_path: Path) -> dict[str, FileInfo]:
    """Inspect zip and return name->FileInfo for each required file.

    Raises UpdateError if any required file is missing, or if the archive
    contains anything else (no nested dirs, no extras).
    """
    if not zip_path.is_file():
        raise UpdateError(f"Zip not found: {zip_path}")

    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            bad = [n for n in names if n != Path(n).name]
            if bad:
                raise UpdateError("Archive contains files in subdirectories: " + ", ".join(bad))

            present = set(names)
            missing = [r for r in REQUIRED_FILES if r not in present]
            if missing:
                raise UpdateError("Archive is missing required files: " + ", ".join(missing))

            extras = sorted(present - set(REQUIRED_FILES))
            if extras:
                raise UpdateError("Archive contains unexpected files: " + ", ".join(extras))

            infos: dict[str, FileInfo] = {}
            for name in REQUIRED_FILES:
                entry = zf.getinfo(name)
                with zf.open(entry) as fh:
                    data = fh.read()
                infos[name] = FileInfo(
                    name=name,
                    size=len(data),
                    sha256=hashlib.sha256(data).hexdigest(),
                )
    except zipfile.BadZipFile as exc:
        raise UpdateError(f"Archive is not a valid zip: {exc}") from exc

    return infos


def _dest_path(root: Path) -> Path:
    if not root.is_dir():
        raise UpdateError(f"Destination directory does not exist: {root}")
    return root


def _snapshot_current(dest: Path) -> Path:
    snapshot = dest / PREVIOUS_DIRNAME
    if snapshot.is_dir():
        rotated = dest / f"{PREVIOUS_DIRNAME}.1"
        if rotated.is_dir():
            shutil.rmtree(rotated)
        snapshot.rename(rotated)

    snapshot.mkdir()
    manifest: dict[str, dict] = {}
    for name in REQUIRED_FILES:
        src = dest / name
        if not src.is_file():
            raise UpdateError(
                f"Cannot snapshot: {src} missing. Refusing to install over an incomplete set."
            )
        info = _info_for(src)
        shutil.copy2(src, snapshot / name)
        manifest[name] = info.to_dict()
    (snapshot / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return snapshot


def _check_size_guard(new_size: int, old_info: FileInfo | None) -> None:
    if old_info is None:
        return
    threshold = int(old_info.size * MIN_SIZE_RATIO)
    if new_size < threshold:
        raise UpdateError(
            f"Refusing to install {old_info.name}: new file is {new_size} bytes, "
            f"below the {threshold}-byte guard (50% of prior {old_info.size} bytes). "
            "Archive is likely truncated or corrupt."
        )


def _atomic_replace(zip_path: Path, dest: Path) -> list[tuple[str, int, int, str, str]]:
    staging = dest / ".staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()

    new_infos = verify_zip(zip_path)
    report: list[tuple[str, int, int, str, str]] = []

    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(staging)

        for name in REQUIRED_FILES:
            new_file = staging / name
            if not new_file.is_file():
                raise UpdateError(f"Extraction failed: {new_file} missing.")
            new_info = new_infos[name]
            target = dest / name
            old_info = _info_for(target) if target.is_file() else None
            _check_size_guard(new_info.size, old_info)
            os.replace(new_file, target)
            old_size = old_info.size if old_info else 0
            old_hash = old_info.sha256 if old_info else "(none)"
            report.append((name, old_size, new_info.size, old_hash, new_info.sha256))
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    return report


def _print_diff(report: list[tuple[str, int, int, str, str]]) -> None:
    name_w = max(len(r[0]) for r in report)
    print()
    print(f"{'file'.ljust(name_w)}  {'old':>10}  {'new':>10}  changed")
    print("-" * (name_w + 2 + 10 + 2 + 10 + 2 + 7))
    for name, old, new, _oh, _nh in report:
        delta = f"{old:>10}  {new:>10}"
        mark = "" if old == new else "*"
        print(f"{name.ljust(name_w)}  {delta}  {mark}")


def _git_stage(dest: Path) -> None:
    rel = dest.as_posix()
    try:
        subprocess.run(
            ["git", "add", "--", rel],
            check=True,
            capture_output=True,
            text=True,
        )
        result = subprocess.run(
            ["git", "status", "--short", "--", rel],
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            print("\ngit status:")
            print(result.stdout.rstrip())
        else:
            print("\nNo staged changes (new files are byte-identical to current).")
    except FileNotFoundError:
        print("\n(skipping git stage: `git` not on PATH)")
    except subprocess.CalledProcessError as exc:
        print(f"\n(git stage failed: {exc.stderr.strip() or exc})")


def _confirm(prompt: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    try:
        reply = input(f"{prompt} [y/N] ").strip().lower()
    except EOFError:
        return False
    return reply in ("y", "yes")


def cmd_install(args: argparse.Namespace) -> int:
    dest = _dest_path(args.dest.resolve())
    new_infos = verify_zip(args.zip.resolve())
    print(f"Archive OK. {len(new_infos)} files detected:")
    for info in new_infos.values():
        print(f"  - {info.name}  {info.size:>10} bytes  sha256={info.sha256[:12]}...")

    if args.check:
        print("\n(--check: not installing)")
        return 0

    print(f"\nDestination: {dest}")
    if not _confirm("Snapshot current files and install?", args.yes):
        print("Aborted.")
        return 130

    snapshot = _snapshot_current(dest)
    print(f"Snapshot: {snapshot}")

    report = _atomic_replace(args.zip.resolve(), dest)
    _print_diff(report)
    _git_stage(dest)
    print("\nDone. Review `git status`, then commit and push.")
    return 0


def cmd_rollback(args: argparse.Namespace) -> int:
    dest = _dest_path(args.dest.resolve())
    snapshot = dest / PREVIOUS_DIRNAME
    manifest_path = snapshot / MANIFEST_NAME
    if not manifest_path.is_file():
        raise UpdateError(f"No rollback manifest at {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(f"Rollback plan from {snapshot}:")
    for name, raw in manifest.items():
        print(f"  - {name}  size={raw['size']}  sha256={raw['sha256'][:12]}...")

    if not _confirm("Restore these files into the destination?", args.yes):
        print("Aborted.")
        return 130

    for name, _raw in manifest.items():
        src = snapshot / name
        target = dest / name
        if not src.is_file():
            raise UpdateError(f"Snapshot missing {src}; refusing to half-restore.")
        os.replace(src, target)
        print(f"  restored {target}")
    _git_stage(dest)
    print("\nRollback complete. Snapshot dir preserved for re-rollback if needed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="update_vulkan",
        description="Update bundled Vulkan / DXVK files from a provider zip.",
    )
    p.add_argument(
        "zip", nargs="?", type=Path, help="Path to the provider's zip (required unless --rollback)."
    )
    p.add_argument(
        "--dest",
        type=Path,
        default=Path("assets/vulkan"),
        help="Destination directory (default: assets/vulkan).",
    )
    p.add_argument("--check", action="store_true", help="Verify the zip only; do not install.")
    p.add_argument(
        "--rollback",
        action="store_true",
        help="Restore the previous snapshot taken by the last install.",
    )
    p.add_argument("--yes", action="store_true", help="Skip confirmation prompts.")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose logging.")
    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.DEBUG if "-v" in (argv or sys.argv) else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.rollback:
            return cmd_rollback(args)
        if args.zip is None:
            parser.error("zip path is required (or pass --rollback)")
        return cmd_install(args)
    except UpdateError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
