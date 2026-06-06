<!-- generated-by: gsd-doc-writer -->
# Echoes Vulkan Helper

A lightweight Windows wizard that automates the Vulkan compatibility setup for
LOTRO: Echoes of Angmar, reducing a multi-step manual process to a few clicks.

## Download

Get the signed, ready-to-run Windows installer from the official release
channel:

- **Purchase & download:** [Echoes Tools store](https://example.com/store) (link to be filled in)
- **What's in the box:** `EchoesVulkanHelper-setup.exe` plus an optional portable
  `EchoesVulkanHelper.exe` that requires no installation.

> The binary is signed by the project owner. An unsigned or repackaged copy is
> **not** an official build — do not trust it. Always verify the publisher
> certificate before running.

## Features

- 5-step wizard (Welcome -> Detection -> Summary -> Install -> Complete)
- Automatic detection of `UserPreferences.echoes.ini` and the game install
- Automatic admin elevation when the game lives in a read-only folder
- Rotating backups of your config and any pre-existing Vulkan files
- Live log and progress bar during install
- Single-click recovery: restore from backup, open logs, open folders
- Signed single-file EXE — no Python, no toolchain, no command line required

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

> Note: on first run of the installer, Windows SmartScreen will show a warning
> because the binary is from a small publisher. Click *More info* → *Run anyway*.
> The official builds are signed — check the publisher name in the SmartScreen
> dialog before clicking through.

## Support

- **Bug reports / issues:** open a ticket at the support email below or use the
  in-app "Open logs" / "Open folder" buttons to gather diagnostics first.
- **License questions:** see [COMMERCIAL.md](./COMMERCIAL.md).
- **Security disclosures:** [zendevve@duck.com](mailto:zendevve@duck.com) (PGP
  key on request).

## License

The project source is AGPL-3.0 (see [LICENSE](./LICENSE)). The **prebuilt
binary you purchased** is covered by a separate, perpetual commercial license
that lets you use the wizard on as many of your own machines as you like — see
[COMMERCIAL.md](./COMMERCIAL.md) for the full terms.

Reselling or repackaging the binary is **not** permitted under the commercial
license; redistribution requires a separate written agreement.