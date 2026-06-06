<!-- generated-by: gsd-doc-writer -->
# Contributing

The Echoes Vulkan Helper is **distributed as a prebuilt binary**. Source
contributions are not accepted and pull requests will be closed without
merge.

If you would like to:

- **Report a bug or request a feature** in the official binary, email
  [zendevve@duck.com](mailto:zendevve@duck.com) or open a ticket through the
  purchase channel. Include the build hash shown in the wizard's *About*
  panel and the contents of the latest `logs\install.log`.
- **Bundle the binary with your own commercial product**, sign a separate
  redistribution agreement first — see [COMMERCIAL.md](./COMMERCIAL.md).
  Unsigned repackaging is not permitted.
- **Run a modified build internally** (e.g. for your own staff machines),
  the source is available under AGPL-3.0 and you may build it for
  internal use, but you may **not** distribute that build to anyone
  outside your organisation. See [LICENSE](./LICENSE) and
  [COMMERCIAL.md](./COMMERCIAL.md) for the boundary.
- **Audit or review the source** for security, you may clone the
  repository. The maintainer is happy to coordinate responsible
  disclosure at [zendevve@duck.com](mailto:zendevve@duck.com).

## Issue reporting

There are no issue templates. When reporting a bug, include:

- **What you did** and **what you expected to happen** vs. **what happened**.
- The contents of the relevant log file under `logs\` (the wizard writes a
  rotating log there at runtime).
- Your Windows version (10 vs. 11, build number).
- For game-detection problems: the path to your `Echoes of Angmar` install
  folder and whether `UserPreferences.echoes.ini` exists there.
- The build hash shown on the *About* page of the wizard.

For security or license-related reports, email
[zendevve@duck.com](mailto:zendevve@duck.com) directly rather than opening a
public issue.

## License of the source

The source in this repository is licensed under **AGPL-3.0** (see
[LICENSE](./LICENSE)). Anything you build from it is also AGPL — so if
you want to keep modifications closed or distribute a build outside your
organisation, you need a commercial licence; see
[COMMERCIAL.md](./COMMERCIAL.md). Bundled third-party components keep
their own licences:

- DXVK (`assets/vulkan/d3d9.dll`, `dinput8.dll`) — MIT, upstream at
  <https://github.com/doitsujin/dxvk>.
- PyInstaller runtime — GPL-2.0 with a bootloader exception.