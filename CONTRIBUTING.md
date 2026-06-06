<!-- generated-by: gsd-doc-writer -->
# Contributing

Thanks for your interest in improving the Echoes Vulkan Helper. The source
is publicly readable under the **PolyForm Noncommercial License 1.0.0**
(`PolyForm-Noncommercial-1.0.0`, see [LICENSE](./LICENSE)) and **pull
requests are welcome**.

You can use, copy, modify, and build the source for any noncommercial
purpose — that includes personal use, research, classroom work, and
contributing back via pull request. Redistributing a binary you built
yourself to other people is commercial use, which is not allowed under
PolyForm Noncommercial; see [COMMERCIAL.md](./COMMERCIAL.md) if you need
that.

## Bug reports

When opening an issue, please include:

- **What you did** and **what you expected to happen** vs. **what happened**.
- The contents of the relevant log file under `logs\` (the wizard writes a
  rotating log there at runtime).
- Your Windows version (10 vs. 11, build number), and whether you are
  running the EXE from the official release or `python app.py` from a local
  checkout.
- For game-detection problems: the path to your `Echoes of Angmar` install
  folder and whether `UserPreferences.echoes.ini` exists there.
- For EXE build problems: the full `pyinstaller` command output and the
  contents of `build/` if present.

## Pull request guidelines

There is no `PULL_REQUEST_TEMPLATE.md` in this repository, so the
following conventions apply:

- **Branch from `main`.** Feature branches do not need a strict naming
  scheme, but a prefix such as `feat/`, `fix/`, or `chore/` is appreciated.
- **One logical change per PR.** Split refactors from behavior changes
  from asset/DXVK-version bumps.
- **Keep `assets/vulkan/` out of feature PRs unless the change is
  specifically about updating DXVK.** DXVK is MIT-licensed upstream and is
  a separate dependency; bumping it is its own concern (see
  `tools/update_vulkan.py`).
- **Tests are required for behavior changes** in `core/`, `wizard/`, and
  `tools/`. GUI-tagged tests (`@pytest.mark.gui`) are skipped on headless CI
  via `PYTEST_DISABLE_GUI=1`; non-GUI tests must pass on all three Python
  versions (3.10, 3.11, 3.12).
- **CI must be green.** The `lint`, `test`, and `build-smoke` jobs all run
  on every PR. Do not disable or skip them.
- **Commit messages:** short, imperative, sentence case is fine (e.g.
  `Add backup rotation to uninstaller`). The project does not enforce
  Conventional Commits.

For the full local setup, test commands, and CI matrix, see
[docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md).

## Contributor license

By submitting a pull request, you agree that your contribution is licensed
under the project's PolyForm Noncommercial 1.0.0 license (see
[LICENSE](./LICENSE)). Submitting a PR is noncommercial use of the
software under the license's terms, so no separate contributor agreement
is required for the act of contributing. If you are contributing on
behalf of an employer, make sure you have authority to do so. Bundled
third-party components keep their own licenses:

- DXVK (`assets/vulkan/d3d9.dll`, `dinput8.dll`) — MIT, upstream at
  <https://github.com/doitsujin/dxvk>.
- PyInstaller runtime — GPL-2.0 with a bootloader exception.

## License of the source

The source in this repository is released under the **PolyForm
Noncommercial License 1.0.0** (`PolyForm-Noncommercial-1.0.0`). See
[LICENSE](./LICENSE) for the full text. If you want a separate commercial
licence that lets you keep modifications closed or redistribute a
build, see [COMMERCIAL.md](./COMMERCIAL.md).