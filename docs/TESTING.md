<!-- generated-by: gsd-doc-writer -->
# Testing

Test strategy and commands for Echoes Vulkan Helper.

## Test framework

- **Framework:** `pytest` (configured in `pyproject.toml`)
- **Markers:** `smoke` for end-to-end tests, `gui` for tests requiring display
- **Coverage:** `pytest-cov` (optional, informational only — no threshold enforced)

## Running tests

```bash
# Full suite (skips GUI tests on headless runners)
pip install -r requirements.lock.txt
pip install pytest pytest-cov
PYTEST_DISABLE_GUI=1 pytest -m "not gui" --cov=core --cov=wizard --cov=tools

# Single file
pytest tests/test_uninstaller.py

# Specific test
pytest -k "test_all_files_removed"

# With coverage report
pytest -m "not gui" --cov=core --cov=wizard --cov=tools --cov-report=term-missing
```

## Test files

| File | Purpose |
|------|---------|
| `tests/smoke_e2e.py` | End-to-end wizard smoke test with stubbed data |
| `tests/smoke_gui.py` | GUI smoke tests (skipped on headless) |
| `tests/test_uninstaller.py` | Unit tests for `core/uninstaller.py` |
| `tests/test_update_vulkan.py` | Tests for `tools/update_vulkan.py` |

## Test markers

- `@pytest.mark.gui` — Requires a display. Skipped automatically when `PYTEST_DISABLE_GUI=1` is set (CI does this).
- `@pytest.mark.smoke` — End-to-end smoke tests.

## CI configuration

Tests run in `.github/workflows/ci.yml`:

| Matrix | Tests |
|--------|-------|
| Python 3.10, 3.11, 3.12 | `ruff check` → `ruff format --check` → `pytest -m "not gui" --cov=...` |
| 3.12 | Coverage artifact uploaded |

## Writing tests

- Place tests in `tests/` using `test_*.py` or `smoke_*.py` naming
- Mark GUI tests with `@pytest.mark.gui`
- Reuse fixtures from `tests/fixtures/` if present
- Tests under `tests/` ignore `B`, `N`, `SIM` rules (see `pyproject.toml`)

## Coverage targets

No minimum coverage enforced. Run with `--cov-report=term-missing` to see gaps.