"""Quick GUI smoke test: launch the wizard and capture a screenshot."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import customtkinter as ctk

ctk.set_appearance_mode("dark")

from wizard.controller import WizardController, WizardState


def main() -> int:
    out_dir = Path(__file__).resolve().parent.parent / "_screenshots"
    out_dir.mkdir(exist_ok=True)

    app = WizardController()
    app.geometry("900x640")
    app.update_idletasks()
    app.update()

    # Screenshot each page
    page_names = ["welcome", "detection", "summary", "install", "completion"]
    for i, name in enumerate(page_names):
        app._show_page(i)
        app.update_idletasks()
        app.update()
        time_delay = 1.5 if name in ("install", "completion") else 0.4
        # Wait for any auto-detection threads
        if name == "detection":
            import time as _t
            _t.sleep(2.0)
        else:
            import time as _t
            _t.sleep(time_delay)
        app.update_idletasks()
        app.update()
        path = out_dir / f"page_{i+1}_{name}.png"
        try:
            import subprocess
            # PowerShell screenshot of the window
            ps = (
                f"Add-Type -AssemblyName System.Drawing,System.Windows.Forms;"
                f"$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
                f"$bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height;"
                f"$g=[System.Drawing.Graphics]::FromImage($bmp);"
                f"$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size);"
                f"$bmp.Save('{path.as_posix()}');"
                f"$g.Dispose();$bmp.Dispose();"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=False)
            print(f"Captured {name}: {path}")
        except Exception as exc:
            print(f"Failed to capture {name}: {exc}")
        app.update_idletasks()
        app.update()

    app.destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
