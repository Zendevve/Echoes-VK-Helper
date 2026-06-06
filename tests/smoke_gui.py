"""Quick GUI smoke test: launch the wizard and capture screenshots of the app window only."""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import customtkinter as ctk

ctk.set_appearance_mode("dark")

from wizard.controller import WizardController  # noqa: E402


def _capture_hwnd(hwnd: int, out_path: Path) -> bool:
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    rect = wt.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return False
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    if w <= 0 or h <= 0:
        return False

    hdc_window = user32.GetDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_window)
    hbm = gdi32.CreateCompatibleBitmap(hdc_window, w, h)
    gdi32.SelectObject(hdc_mem, hbm)

    PW_RENDERFULLCONTENT = 0x00000002
    user32.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wt.DWORD),
            ("biWidth", ctypes.c_long),
            ("biHeight", ctypes.c_long),
            ("biPlanes", wt.WORD),
            ("biBitCount", wt.WORD),
            ("biCompression", wt.DWORD),
            ("biSizeImage", wt.DWORD),
            ("biXPelsPerMeter", ctypes.c_long),
            ("biYPelsPerMeter", ctypes.c_long),
            ("biClrUsed", wt.DWORD),
            ("biClrImportant", wt.DWORD),
        ]

    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth = w
    bmi.biHeight = -h
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0

    buf = (ctypes.c_ubyte * (w * h * 4))()
    gdi32.GetDIBits(hdc_mem, hbm, 0, h, buf, ctypes.byref(bmi), 0)

    gdi32.DeleteObject(hbm)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hwnd, hdc_window)

    from PIL import Image

    img = Image.frombuffer("RGBA", (w, h), bytes(buf), "raw", "BGRA", 0, 1)
    img = img.convert("RGB")
    img.save(out_path)
    return True


def main() -> int:
    out_dir = Path(__file__).resolve().parent.parent / "_screenshots"
    out_dir.mkdir(exist_ok=True)

    app = WizardController()
    app.geometry("900x640+200+200")
    app.update_idletasks()
    app.update()
    time.sleep(0.5)

    hwnd = int(app.winfo_id())
    top = ctypes.windll.user32.GetParent(hwnd) or hwnd
    top = ctypes.windll.user32.GetAncestor(hwnd, 2) or top

    page_names = ["welcome", "detection", "summary", "install", "completion"]
    for i, name in enumerate(page_names):
        app._show_page(i)
        app.update_idletasks()
        app.update()
        wait = 2.0 if name == "detection" else 0.4
        time.sleep(wait)
        app.update_idletasks()
        app.update()
        path = out_dir / f"page_{i+1}_{name}.png"
        ok = _capture_hwnd(top, path)
        print(f"Captured {name}: {path} ({'ok' if ok else 'FAIL'})")

    app.destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
