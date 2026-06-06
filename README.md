<!-- generated-by: gsd-doc-writer -->
# Echoes Vulkan Helper

A lightweight Windows wizard that automates the Vulkan compatibility setup for
LOTRO: Echoes of Angmar, reducing a multi-step manual process to a few clicks.

## Download

Get the prebuilt Windows binary from the official release channel:

- **Purchase & download:** [Echoes Tools store](https://example.com/store) (link to be filled in)
- **What's in the box:** `EchoesVulkanHelper-setup.exe` (installer) and/or a
  portable `EchoesVulkanHelper.exe` that requires no installation.

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

1. Download `EchoesVulkanHelper-setup.exe` from the store link above.
2. Double-click the installer and follow the prompts.
3. Launch **Echoes Vulkan Helper** from the Start menu.
4. Follow the on-screen prompts from **Welcome** through **Complete**.
5. Launch your game. Done.

> On first run, Windows SmartScreen will show a warning because the binary
> is unsigned. Click *More info* → *Run anyway*. Verify the build hash shown
> on the wizard's *About* page against the value published in your purchase
> email before trusting the binary.

## Build from source

The source is public under a source-available license (see
[LICENSE](./LICENSE)). Building from source is supported and encouraged for
auditing, modification, and personal use:

```bash
pip install -r requirements.lock.txt
python app.py
```

To produce your own single-file EXE:

```bash
pip install pyinstaller
pyinstaller --noconfirm app.spec
```

Output: `dist\EchoesVulkanHelper.exe`. See [docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md)
for the full build/test/CI workflow.

> Distributing a build you produced yourself is permitted only under the
> terms of [LICENSE](./LICENSE) and, if you want to keep modifications
> closed, a separate [COMMERCIAL.md](./COMMERCIAL.md) agreement.

## Support

- **Bug reports / issues:** open an issue on this repository, or email
  [zendevve@duck.com](mailto:zendevve@duck.com). Include the build hash
  shown on the wizard's *About* page and the contents of the latest
  `logs\install.log`.
- **License questions:** see [COMMERCIAL.md](./COMMERCIAL.md).
- **Security disclosures:** [zendevve@duck.com](mailto:zendevve@duck.com) (PGP
  key on request).

## License

The source code in this repository is released under a source-available
license — see [LICENSE](./LICENSE) for the full text. The prebuilt binary
is also distributed under that license; commercial users who want to keep
modifications closed can buy a separate perpetual licence via
[COMMERCIAL.md](./COMMERCIAL.md).