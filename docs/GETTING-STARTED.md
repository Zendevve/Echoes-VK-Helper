<!-- generated-by: gsd-doc-writer -->
# Getting Started

This guide walks a new **purchaser** of the Echoes Vulkan Helper binary from a
clean Windows machine to a working Vulkan install for LOTRO: Echoes of Angmar.

If you are looking to build the wizard from source, you are in the wrong place
— the source is not distributed for end users. See [COMMERCIAL.md](../COMMERCIAL.md)
if you need a redistribution agreement.

## Prerequisites

- **OS:** Windows 10 or Windows 11 (x64)
- **Disk space:** ~200 MB free (most of it is the bundled DXVK/Vulkan runtime
  packed inside the EXE at build time)
- **Administrator rights:** the helper will request elevation if your game
  install lives under `Program Files`; if UAC is disabled group policy-wide,
  move the game out of `Program Files` or run the helper as administrator
  manually
- **A legitimate copy of LOTRO: Echoes of Angmar** installed and patched to a
  version the game client considers current
- The game should be at least once-run so `UserPreferences.echoes.ini` exists in
  `Documents\Lord of the Rings Online\` (the helper auto-detects this)

## Install

1. Download `EchoesVulkanHelper.exe` from the purchase email or the
   official store link sent after payment.
2. SmartScreen will show a warning because the binary is unsigned — this
   is normal. Click *More info* → *Run anyway* after confirming the file
   size and build hash against your purchase email.
3. Double-click the EXE. If Windows asks for UAC, accept it — the wizard
   needs admin to write to the game folder if it lives under
   `Program Files`. The wizard window opens immediately after.
4. The EXE does not install anything to your system. When you are done,
   just delete the file. There is no uninstaller.

## First run

The 5-step wizard opens immediately:

1. **Welcome** — introduction and "Get started" button
2. **Detection** — auto-locates `UserPreferences.echoes.ini` and the game
   install folder
3. **Summary** — shows what was found and what will change
4. **Install** — copies the Vulkan DLLs, creates rotating backups, and writes
   the config (the helper will request admin elevation if the game folder is
   read-only, e.g. under `Program Files`)
5. **Complete** — links to launch the game, open logs, or restore a backup

## Verify your purchase

The "About" panel inside the wizard (last page, top-right corner) shows the
build hash and the license key associated with your purchase. If those fields
are blank, your copy is **not** a genuine paid build — please contact support
before running it.

## Common issues

- **"SmartScreen prevented an unrecognized app from starting"** when running
  the EXE. This is expected for an unsigned binary. Click *More info* →
  *Run anyway*, but **only after** confirming the file size and build hash
  match the values in your purchase email.

- **Game folder is in `Program Files` and the install step fails with
  permission errors.** The wizard will detect the read-only folder and pop
  the standard Windows UAC elevation prompt. Accept it.

- **The wizard reports the game is not detected.** Open `Documents\Lord of the
  Rings Online\` in Explorer and confirm `UserPreferences.echoes.ini` exists.
  If it does not, launch the game once and let it create the file, then
  re-run the helper.

- **EXE crashes immediately on launch.** Capture the Windows Event Viewer
  entry under *Windows Logs → Application* and email it to support.

- **Roll back a bad install.** The completion page has a *Restore from
  backup* button. The helper keeps a rotating chain of `.bak` /
  `.backup[.N]` files, so most broken installs are recoverable with a single
  click.

## Next steps

- [README.md](../README.md) — feature overview and quick start.
- [docs/CONFIGURATION.md](./CONFIGURATION.md) — where runtime state is persisted,
  how backups are rotated, and any environment variables the app reads.
- [COMMERCIAL.md](../COMMERCIAL.md) — your purchased license terms.
- [LICENSE](../LICENSE) — the PolyForm Noncommercial 1.0.0 terms that cover
  the source code (you are using the binary you purchased, so the
  noncommercial restrictions don't bind your use of the EXE — see
  [COMMERCIAL.md](../COMMERCIAL.md) for the licence that lets you build
  and redistribute the binary yourself).