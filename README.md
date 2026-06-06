<!-- generated-by: gsd-doc-writer -->
# Echoes Vulkan Helper

A lightweight Windows wizard that automates the Vulkan compatibility setup for
LOTRO: Echoes of Angmar, reducing a multi-step manual process to a few clicks.

## Download

Get the prebuilt Windows binary from the official release channel:

- **Purchase & download:** [Echoes Tools store](https://example.com/store) (link to be filled in)
- **What's in the box:** `EchoesVulkanHelper.exe` — a portable single-file
  binary built with PyInstaller. No installer, no uninstaller; just
  download, run, and delete the file when you're done.

> The official binary is **not code-signed** — Windows SmartScreen will warn
> on first run. This is expected. Click *More info* → *Run anyway* after
> confirming the file size and build hash against the values listed in your
> purchase email or on the release page.

## Features

- 5-step wizard (Welcome -> Detection -> Summary -> Install -> Complete)
- Automatic detection of `UserPreferences.echoes.ini` and the game install
- Automatic admin elevation when the game lives in a read-only folder
- Rotating backups of your config and any pre-existing Vulkan files
- Live log and progress bar during install
- Single-click recovery: restore from backup, open logs, open folders
- Single-file EXE — no Python, no toolchain, no command line required to run

## Requirements

- Windows 10 / 11 (x64)
- A legitimate copy of LOTRO: Echoes of Angmar installed on the same machine
- Administrator rights (the helper will request elevation if your game install
  lives under `Program Files`)

## Quick start (end users)

1. Download `EchoesVulkanHelper.exe` from the store link above.
2. Double-click the EXE. SmartScreen will warn (unsigned); click *More info*
   → *Run anyway* after verifying the build hash.
3. Follow the on-screen prompts from **Welcome** through **Complete**.
4. Launch your game. Done.

When you're done with the helper, just delete the EXE. It does not install
itself anywhere and leaves no system residue.

> On first run, Windows SmartScreen will show a warning because the binary
> is unsigned. Click *More info* → *Run anyway*. Verify the build hash shown
> on the wizard's *About* page against the value published in your purchase
> email before trusting the binary.

## Build from source

The source is public under the **PolyForm Noncommercial License 1.0.0**
(`PolyForm-Noncommercial-1.0.0`, see [LICENSE](./LICENSE)). Building from
source is supported and encouraged for **personal, educational, research, or
contribution** purposes. Distributing the binary you build (free or paid,
inside or outside your organisation) is commercial use and requires a
separate licence from [COMMERCIAL.md](./COMMERCIAL.md).

```bash
pip install -r requirements.lock.txt
python app.py
```

To produce your own single-file EXE (for your own non-commercial use):

```bash
pip install pyinstaller
pyinstaller --noconfirm app.spec
```

Output: `dist\EchoesVulkanHelper.exe`. See
[docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md) for the full build/test/CI
workflow.

## Support

- **Bug reports / issues:** open an issue on this repository, or email
  [zendevve@duck.com](mailto:zendevve@duck.com). Include the build hash
  shown on the wizard's *About* page and the contents of the latest
  `logs\install.log`.
- **License questions:** see [COMMERCIAL.md](./COMMERCIAL.md).
- **Security disclosures:** [zendevve@duck.com](mailto:zendevve@duck.com)
  (PGP key on request).

## License

The source in this repository is licensed under the **PolyForm
Noncommercial License 1.0.0** (`PolyForm-Noncommercial-1.0.0`) — see
[LICENSE](./LICENSE) for the full text. Pull requests and other
non-commercial use of the source are explicitly allowed. Commercial use
(including building and redistributing the prebuilt binary) requires a
separate commercial licence — see [COMMERCIAL.md](./COMMERCIAL.md).