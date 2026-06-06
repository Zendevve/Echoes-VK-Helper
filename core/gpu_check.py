"""Detect the primary GPU and confirm a Vulkan loader is reachable.

Strategy:
  1. Probe the Vulkan loader (`vulkan-1.dll`) via ctypes. Call
     `vkEnumerateInstanceVersion` to confirm Vulkan 1.x is supported. This is
     the canonical signal that a real ICD is installed.
  2. If the loader is missing or the call fails, fall back to GDI's
     `EnumDisplayDevicesW` to at least surface the active adapter's name. We
     treat a non-empty `DeviceString` as a weak "GPU present" signal.
  3. Never raise. The wizard must still render even on broken systems.

The result is a `GpuCheckResult` dataclass that the welcome page renders.
"""

from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GpuCheckResult:
    ok: bool
    name: str
    reason: str
    api_version: int  # raw VK_MAKE_API_VERSION; 0 if unknown
    vulkan_version: tuple[int, int, int] | None = None  # decoded (major, minor, patch)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "name": self.name,
            "reason": self.reason,
            "api_version": self.api_version,
            "vulkan_version": list(self.vulkan_version) if self.vulkan_version is not None else None,
        }


_VK_SUCCESS = 0


class _DisplayDeviceW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("DeviceName", ctypes.c_wchar * 32),
        ("DeviceString", ctypes.c_wchar * 128),
        ("StateFlags", wintypes.DWORD),
        ("DeviceID", ctypes.c_wchar * 128),
        ("DeviceKey", ctypes.c_wchar * 128),
    ]


def _decode_api_version(raw: int) -> str:
    if raw <= 0:
        return "unknown"
    major = (raw >> 22) & 0x7F
    minor = (raw >> 12) & 0x3FF
    patch = raw & 0xFFF
    return f"{major}.{minor}.{patch}"


def _decode_version_tuple(raw: int) -> tuple[int, int, int] | None:
    """Decode raw VK_MAKE_VERSION into (major, minor, patch) or None on failure."""
    if raw <= 0:
        return None
    return (
        (raw >> 22) & 0x7F,
        (raw >> 12) & 0x3FF,
        raw & 0xFFF,
)


def _probe_vulkan() -> tuple[bool, int, str]:
    """Try `vkEnumerateInstanceVersion`. Returns (ok, api_version_raw, reason)."""
    if not sys.platform.startswith("win"):
        return False, 0, "Vulkan check only runs on Windows."

    try:
        vk = ctypes.WinDLL("vulkan-1.dll")
    except OSError as exc:
        return False, 0, f"vulkan-1.dll not loadable: {exc}"

    try:
        proc = vk.vkEnumerateInstanceVersion
        proc.restype = ctypes.c_int
        proc.argtypes = [ctypes.POINTER(ctypes.c_uint32)]
    except AttributeError as exc:
        return False, 0, f"vulkan-1.dll missing vkEnumerateInstanceVersion: {exc}"

    api_version = ctypes.c_uint32(0)
    try:
        rc = proc(ctypes.byref(api_version))
    except OSError as exc:
        return False, 0, f"vkEnumerateInstanceVersion raised: {exc}"

    if rc != _VK_SUCCESS:
        return False, 0, f"vkEnumerateInstanceVersion returned VkResult={rc}"

    return True, int(api_version.value), "Vulkan loader reports a working ICD."


def _query_display_device() -> str:
    """Best-effort adapter name via GDI. Empty string on any failure."""
    if not sys.platform.startswith("win"):
        return ""
    try:
        user32 = ctypes.WinDLL("user32.dll", use_last_error=True)
    except OSError:
        return ""
    try:
        enum_proc = user32.EnumDisplayDevicesW
        enum_proc.restype = wintypes.BOOL
        enum_proc.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.POINTER(_DisplayDeviceW),
            wintypes.DWORD,
        ]
    except AttributeError:
        return ""

    info = _DisplayDeviceW()
    info.cb = ctypes.sizeof(_DisplayDeviceW)
    if not enum_proc(None, 0, ctypes.byref(info), 0):
        return ""
    name = (info.DeviceString or "").strip()
    return name


def _version_to_str(v: tuple[int, int, int]) -> str:
    return f"{v[0]}.{v[1]}.{v[2]}"


def check_vulkan_support(
    min_version: tuple[int, int, int] = (1, 3, 0),
) -> GpuCheckResult:
    """Return a GpuCheckResult. Never raises.

    `min_version` defaults to Vulkan 1.3, the baseline LOTRO requires.
    """
    try:
        ok, api_version, reason = _probe_vulkan()
        detected = _decode_version_tuple(api_version)

        if ok and detected is not None:
            name = _query_display_device() or "Vulkan-capable GPU"
            meets_min = (
                detected[0] > min_version[0]
                or (
                    detected[0] == min_version[0]
                    and (
                        detected[1] > min_version[1]
                        or (
                            detected[1] == min_version[1]
                            and detected[2] >= min_version[2]
                        )
                    )
                )
            )
            if meets_min:
                return GpuCheckResult(
                    ok=True,
                    name=name,
                    reason=f"{reason} (Vulkan {_decode_api_version(api_version)})",
                    api_version=api_version,
                    vulkan_version=detected,
                )
            return GpuCheckResult(
                ok=False,
                name=name,
                reason=(
                    f"Vulkan {_decode_api_version(api_version)} is below the "
                    f"required {_version_to_str(min_version)}. Update your GPU driver."
                ),
                api_version=api_version,
                vulkan_version=detected,
            )

        if ok:
            name = _query_display_device() or "Vulkan-capable GPU"
            return GpuCheckResult(
                ok=False,
                name=name,
                reason=(
                    f"{reason} Version metadata was unreadable; cannot confirm "
                    f"Vulkan >= {_version_to_str(min_version)}."
                ),
                api_version=api_version,
                vulkan_version=None,
            )

        # Vulkan probe failed. Fall back to GDI: we can at least confirm a
        # display adapter is registered with the OS, which is enough to tell
        # the user "GPU detected" even if the loader chain is broken.
        name = _query_display_device()
        if name:
            return GpuCheckResult(
                ok=False,
                name=name,
                reason=(
                    f"{reason} Display adapter '{name}' is registered, but the "
                    "Vulkan runtime is missing or broken. Reinstall the latest "
                    "GPU driver before continuing."
                ),
                api_version=0,
                vulkan_version=None,
            )

        logger.warning("GPU check failed: %s", reason)
        return GpuCheckResult(
            ok=False,
            name="Unknown GPU",
            reason=(
                f"{reason} No display adapter could be enumerated either. "
                "Check that a GPU driver is installed."
            ),
            api_version=0,
            vulkan_version=None,
        )
    except Exception as exc:
        logger.exception("Unexpected error in check_vulkan_support: %s", exc)
        return GpuCheckResult(
            ok=False,
            name="Unknown GPU",
            reason=f"GPU check crashed: {exc}",
            api_version=0,
            vulkan_version=None,
        )


def check_gpu() -> GpuCheckResult:
    """Deprecated: use check_vulkan_support(). Default minimum is (1,3,0)."""
    return check_vulkan_support()
