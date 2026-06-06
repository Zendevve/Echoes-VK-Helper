<!-- generated-by: gsd-doc-writer -->
# Development

> **Internal — not for redistribution.** This page documents how the project
> maintainer builds and tests the official binary. Source-build instructions
> are intentionally not part of the end-user documentation set and are kept
> here for the maintainer's reference only. Do not link this page from
> `README.md` or any user-facing material.

See [README.md](../README.md) for the end-user quick start and
[Architecture](ARCHITECTURE.md) / [Configuration](CONFIGURATION.md) for
higher-level context.

## Local setup

### Prerequisites

- Windows 10 / 11 (x64) — the helper is Windows-only; it uses `pywin32` and
  UAC elevation.
- Python **3.10, 3.11, or 3.12** (matching `pyproject.toml` `requires-python`
  and the CI test matrix).
- `git` for cloning the repository.
- `pip` (bundled with the official CPython installers is fine).

### Clone and install

```bash
git clone <repository-url> echoes-vulkan-helper
cd echoes-vulkan-helper

# Reproducible install (matches CI exactly)
pip install -r requirements.lock.txt

# Dev-only extras (lint + tests + build)
pip install ruff pytest pytest-cov pyinstaller
```

> `requirements.in` is the hand-curated top-level pin set; use it only when
> you intentionally want looser constraints (for example, prototyping a new
> dependency). CI always installs from `requirements.lock.txt`.

### Optional: Vulkan runtime DLLs

The helper ships the user-visible UI, but the actual Vulkan shim DLLs
(`assets/vulkan/d3d9.dll`, `dinput8.dll`, `dinput8.ini`) must be present for
the installer to do anything. They are not committed if you are on a
slimmed-down checkout. Drop a DXVK x64 build into `assets/vulkan/` before
running end-to-end; `app.py` aborts with a clear error dialog if the files
are missing (see `_check_assets_or_warn` in `app.py`).

### First run

```bash
python app.py
```

The wizard launches immediately. Set `PYTEST_DISABLE_GUI=1` only when running
the test suite on a headless runner (CI does this automatically).

## Build commands

There is no `Makefile` and no `scripts` block — this is a pure-Python
project. The canonical commands are:

| Command | Description |
| --- | --- |
| `python app.py` | Run the wizard from source. |
| `pyinstaller --noconfirm app.spec` | Produce `dist/EchoesVulkanHelper.exe` (single-file Windows binary, includes `assets/vulkan/*` and the `customtkinter` theme via `collect_all`). |
| `pip install -r requirements.lock.txt` | Reproducible dependency install used by CI. |
| `pip install -r requirements.in` | Loose dev install (top-level pins only). |

The PyInstaller spec (`app.spec`) bakes in the data hook for
`assets/vulkan/`, the optional `.ico`, and the `customtkinter` resource
collection. You should not need to edit it for normal development; if you
add new asset files, place them under `assets/vulkan/` (already wired up)
or update `datas` in `app.spec` explicitly.

## Code style

The project uses [ruff](https://docs.astral.sh/ruff/) for both linting and
formatting. Configuration lives in `pyproject.toml` under
`[tool.ruff]`, `[tool.ruff.lint]`, and `[tool.ruff.format]`.

| Tool | Config file | Command |
| --- | --- | --- |
| ruff (lint) | `pyproject.toml` `[tool.ruff.lint]` | `ruff check .` |
| ruff (format) | `pyproject.toml` `[tool.ruff.format]` | `ruff format .` (or `ruff format --check .` in CI) |

Enabled rule families: `E`, `W`, `F`, `I`, `B`, `UP`, `N`, `SIM`, `RUF`.
Notable ignores:

- `E501` — line length is handled by the formatter (`line-length = 100`).
- `B008` — function-call-in-default-arg, common in click/FastAPI style.
- `RUF012` — mutable class attributes, reviewed per-case.

Tests under `tests/` get a relaxed per-file-ignore set (`B`, `N`, `SIM`).
Python target is `py310`, with auto-upgrade applied via the `UP` ruleset.

CI enforces both `ruff check .` and `ruff format --check .` on every push
and pull request to `main` (see `.github/workflows/ci.yml`, job `Lint (ruff)`).

## Tests

The test framework is **pytest** (>= 8.0, configured in
`pyproject.toml` under `[tool.pytest.ini_options]`). Test files live in
`tests/`:

```text
tests/
├── smoke_e2e.py        # end-to-end smoke tests
├── smoke_gui.py        # GUI smoke tests (marked `gui`)
├── test_uninstaller.py
├── test_update_vulkan.py
└── fixtures/
```

### Running tests

```bash
# Full suite, headless (skips GUI tests on runners without a display)
PYTEST_DISABLE_GUI=1 pytest -m "not gui" --cov=core --cov=wizard --cov=tools

# A single file
pytest tests/test_uninstaller.py

# With coverage report
pytest -m "not gui" --cov=core --cov=wizard --cov=tools --cov-report=term-missing
```

Pytest is configured with `--strict-markers`, `--strict-config`, and
`filterwarnings = ["error", ...]`, so unknown markers and unfiltered
deprecation warnings fail the run. The `gui` marker documents tests that
require a display; `smoke` documents end-to-end tests.

### Writing new tests

- Place new test files in `tests/` using the `test_*.py` or `smoke_*.py`
  naming convention.
- Mark any test that opens a real Tk/CustomTkinter window with
  `@pytest.mark.gui` so headless CI can skip it via `-m "not gui"`.
- Reuse fixtures from `tests/fixtures/` where possible; add shared helpers
  there rather than at module scope.

### Coverage requirements

No `coverageThreshold` block is configured in `pyproject.toml` and no
`.nycrc` / `c8` config exists, so coverage is informational only. CI
runs with `--cov=core --cov=wizard --cov=wizard --cov=tools` and uploads
the `.coverage` artifact from the Python 3.12 matrix run (retention
7 days).

## CI integration

Defined in `.github/workflows/ci.yml`. Triggers: `push` and `pull_request`
on `main`, plus `workflow_dispatch`.

| Job | Runner | What it runs |
| --- | --- | --- |
| `Lint (ruff)` | `windows-latest`, Python 3.12 | `pip install ruff` → `ruff check .` → `ruff format --check .` |
| `Tests (pytest)` | `windows-latest`, matrix `[3.10, 3.11, 3.12]` | `pip install -r requirements.lock.txt pytest pytest-cov` → `PYTEST_DISABLE_GUI=1 pytest -m "not gui" --cov=core --cov=wizard --cov=tools --cov-report=term-missing`. The 3.12 run uploads `.coverage` as an artifact. |
| `PyInstaller build smoke` | `windows-latest`, Python 3.12, after lint+test | `pip install -r requirements.lock.txt pyinstaller` → `pyinstaller --noconfirm app.spec` → asserts `dist/EchoesVulkanHelper.exe` exists and uploads it as `EchoesVulkanHelper-<sha>`. |

The smoke build runs after the lint and test jobs pass (`needs: [lint, test]`),
so a broken binary cannot ship while tests are green.

> The CI-uploaded EXE artifact is **not** the publicly distributed binary.
> The official store build is produced out-of-band, signed with the project
> owner's code-signing certificate, and never published to a CI artifact
> URL.

## Branch conventions

The default branch is **`main`** (matches the CI `branches: [main]` filter
in `.github/workflows/ci.yml`).

The repository follows a free-form `fl: <summary> why: <rationale>` commit
message style — that is the maintainer's convention, not an enforced
linter. There is no `PULL_REQUEST_TEMPLATE.md` and no pre-commit hook
configuration.

## PR process

There is no `.github/PULL_REQUEST_TEMPLATE.md` in this repository, so the
review process is informal. Use the following baseline when opening a PR
against `main`:

- Branch from a current `main` (`git fetch && git rebase origin/main`).
- Run `ruff check .` and `ruff format .` locally — both must pass before CI
  will go green.
- Run `pytest -m "not gui"` locally (or with `PYTEST_DISABLE_GUI=1` on a
  headless box) and confirm coverage output looks reasonable.
- If your change touches PyInstaller or asset bundling, also run
  `pyinstaller --noconfirm app.spec` and smoke-test
  `dist/EchoesVulkanHelper.exe` on a real Windows machine.
- In the PR description, link the issue or motivation, summarize the
  change, and call out any user-visible behavior change (the wizard is
  user-facing).
- Reference any docs you updated (this directory, the
  [README](../README.md), or `COMMERCIAL.md` if licensing is involved).