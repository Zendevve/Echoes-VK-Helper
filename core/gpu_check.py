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

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "name": self.name,
            "reason": self.reason,
            "api_version": self.api_version,
        }


_VK_SUCCESS = 0


class _DISPLAY_DEVICEW(ctypes.Structure):
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
            ctypes.POINTER(_DISPLAY_DEVICEW),
            wintypes.DWORD,
        ]
    except AttributeError:
        return ""

    info = _DISPLAY_DEVICEW()
    info.cb = ctypes.sizeof(_DISPLAY_DEVICEW)
    if not enum_proc(None, 0, ctypes.byref(info), 0):
        return ""
    name = (info.DeviceString or "").strip()
    return name


def check_gpu() -> GpuCheckResult:
    """Return a `GpuCheckResult`. Never raises."""
    try:
        ok, api_version, reason = _probe_vulkan()
        if ok:
            name = _query_display_device() or "Vulkan-capable GPU"
            return GpuCheckResult(
                ok=True,
                name=name,
                reason=f"{reason} (Vulkan {_decode_api_version(api_version)})",
                api_version=api_version,
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
        )
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        logger.exception("Unexpected error in check_gpu: %s", exc)
        return GpuCheckResult(
            ok=False,
            name="Unknown GPU",
            reason=f"GPU check crashed: {exc}",
            api_version=0,
        )
