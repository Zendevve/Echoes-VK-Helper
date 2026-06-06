# Echoes Vulkan Helper — Implementation Plan

## Goal

Ship a single-file Windows EXE (`EchoesVulkanHelper.exe`) that walks a non-technical LOTRO player from launch to a working Vulkan install in a few clicks. 5-step CustomTkinter wizard with auto-detection, automatic admin elevation, hardcoded recovery, and graceful failure containment.

## Resolved Design Decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Failure UX | Single Completion page. On failure: red status rows, primary buttons replaced with **Restore Backup** + **Open Logs**; **Finish** stays. |
| 2 | Elevation | Probe writability at Detection step. If read-only, show "Helper will restart with admin rights", then `ShellExecuteW(NULL, "runas", exe, "--resume state.json", NULL, SW_SHOWNORMAL)` to relaunch. State is serialized to `%TEMP%\evh_state.json` before the relaunch. |
| 3 | Vulkan binaries | Plan documents DXVK release sourcing. Default `dinput8.ini` is committed (LOTRO-tuned options). Implementation agent verifies files are present before building. |
| 4 | Monitor | Primary monitor via `screeninfo.get_monitors()` filtered by `is_primary`. Summary page shows the value with a "Change..." combobox of all detected modes. Final fallback `(1920, 1080)`. |
| 5 | GPU pre-flight | **Addendum.** Welcome page runs `vkEnumerateInstanceVersion` before any install work. Vulkan < 1.3 blocks the wizard with a red card + driver-update guidance. Saves the user from a doomed install. |

## Project Structure

```
echoes-vulkan-helper/
├── app.py                    # Entry point. Boots logger, creates App, wraps mainloop in try/except.
├── core/
│   ├── logger.py             # Thread-safe logging to logs/install.log + queue handler for UI.
│   ├── config_manager.py     # find_config(), apply_recommended_settings(), read_setting()
│   ├── game_detector.py      # find_game_installation(), search_steam_libraries(), is_writable()
│   ├── backup_manager.py     # create_backup(), restore_backup() with rotation cap of 5
│   ├── vulkan_installer.py   # install_vulkan() with *.backup rename for pre-existing files
│   ├── validator.py          # ValidationResult dataclass + run_validation() — 9 checks
│   ├── gpu_check.py          # check_vulkan_support() via vkEnumerateInstanceVersion (Addendum)
│   └── elevation.py          # relaunch_as_admin(), load_resume_state(), save_resume_state()
├── wizard/
│   ├── controller.py         # WizardController, WizardState dataclass, page registry
│   ├── pages/
│   │   ├── welcome_page.py   # Step 1 — intro + "Restore from backup" footer link
│   │   ├── detection_page.py # Step 2 — auto-detect + Browse buttons + writability probe
│   │   ├── summary_page.py   # Step 3 — change list + resolution override dropdown
│   │   ├── install_page.py   # Step 4 — progress bar + live log + queue drain
│   │   └── completion_page.py# Step 5 — success or failure state, Restore/Open Logs/Folder/Launch
├── assets/vulkan/
│   ├── dinput8.ini           # LOTRO-tuned default (see "Asset Content" below)
│   ├── dinput8.dll           # USER-SUPPLIED: DXVK release (x64)
│   └── d3d9.dll              # USER-SUPPLIED: DXVK release (x64)
├── logs/                     # Created at runtime, install.log written here
├── icon.ico                  # USER-SUPPLIED
├── requirements.txt
└── README.md
```

## Threading & UI Safety Model

- One install worker thread, started by the controller when Step 4 is entered.
- Worker uses a `queue.Queue` for all UI-bound output. Events:
  - `("log", line)` — append a line to the log textbox
  - `("step", name, pct)` — bump the progress bar and the step label
  - `("done", ValidationResult)` — terminal event
  - `("error", exc)` — terminal event on unhandled exception
- Install page polls the queue via `self.after(100, self._drain)`. **No widget is ever touched from the worker thread.**
- The worker wraps its entire run in a top-level `try/except`; any unhandled exception is enqueued as `("error", exc)` so the UI never freezes.

## Wizard Flow & Page Contracts

Every page subclasses a common `WizardPage(ctk.CTkFrame)` and implements:

- `on_enter(ctx: WizardState) -> None` — populate widgets from context
- `on_exit() -> dict` — return updated context fields
- `can_advance() -> bool` — gate the Next button

`WizardState` (dataclass, owned by controller):

```
config_path: Path | None
game_path: Path | None
resolution: tuple[int, int] | None
detection_errors: list[str]
needs_elevation: bool
backup_paths: list[Path]
validation: ValidationResult | None
install_succeeded: bool
```

Page transitions use `tkraise()` on a shared `CTkFrame` container. Buttons are provided by a fixed bottom bar owned by the controller so page implementations only render content.

## Per-Step Behavior

### Step 1 — Welcome
- Static content from PRD. Big "Next" + "Cancel".
- Footer link: "Restore from a previous backup" → opens a `RestoreDialog` (file picker for any `.bak` in the config dir, restores, then exits with toast).

### Step 2 — Detection
- On enter: kick off detection in a worker thread (same queue pattern).
  - `find_config()` — check `Documents\Lord of the Rings Online\UserPreferences.echoes.ini`. Return `Path` or `None`.
  - `find_game_installation()` — check in order: registry (`HKLM\SOFTWARE\StandingStoneGames\LOTRO` install path), `Program Files`, `Program Files (x86)`, Steam `libraryfolders.vdf` parsed for `lotroclient.exe`, common custom locations (`D:\Games`, `C:\Games`, `E:\Games`, `C:\LOTRO`, `D:\LOTRO`).
  - `is_writable(game_path.parent)` — if `False`, set `state.needs_elevation = True` and show the elevation prompt.
- UI shows "Searching..." then ✓/✗ for each row.
- "Browse Config" and "Browse Game Folder" buttons always available.
- Next disabled until both files exist.

### Step 3 — Summary
- Read current values from `UserPreferences.echoes.ini` and show what will change.
- Resolution row shows detected value with a "Change..." `CTkOptionMenu` populated with all detected monitor modes.
- Install button starts the install worker.

### Step 4 — Install (worker thread)

| Step | % | What happens |
|------|---|--------------|
| Creating backup | 0–20 | `create_backup(config_path)` rotates `.bak`→`.bak.1`→...→`.bak.5`. Also rotates `dinput8.ini.backup`, `dinput8.dll.backup`, `d3d9.dll.backup` (cap 5). |
| Detecting resolution | 20–30 | Already done in detection, just re-confirm. |
| Updating config | 30–55 | `apply_recommended_settings()` via `configparser`. Preserve all other keys. Write to a temp file, then `os.replace()` for atomicity. |
| Installing Vulkan files | 55–85 | For each of the 3 source files: if dest exists, rename to `*.backup` (rotated). Copy source → dest with `shutil.copy2`. |
| Running validation | 85–100 | `run_validation()` returns `ValidationResult`. Enqueue `("done", result)` or `("error", ...)` on failure. |

- Live log: `CTkTextbox` (read-only, `state="disabled"`, dark background). Worker enqueues lines; UI thread appends on poll.
- Progress bar: `CTkProgressBar`, determinate, driven by the % events.

### Step 5 — Completion
- On enter: read `state.validation` and `state.install_succeeded`.
- **Success state:** green checkmark rows, 4 PRD-listed success lines. Primary buttons: **Open Game Folder**, **Open Config Folder**, **Launch Echoes**, **Finish**. "Launch Echoes" runs `subprocess.Popen([str(game_path / "lotroclient.exe")], cwd=game_path)` non-blocking.
- **Failure state:** red ✗ rows showing which checks failed. Primary buttons: **Restore Backup**, **Open Logs**, **Finish**. **Open Game Folder** and **Open Config Folder** stay as secondary actions.
- "Open Folder" uses `os.startfile(path)`. "Open Logs" opens the log file in Notepad via `os.startfile(log_path)`.

## Core Module Specs

### `core/logger.py`
- `setup_logging(log_dir: Path) -> logging.Logger` — returns the root logger.
- File handler: `RotatingFileHandler("install.log", maxBytes=1MB, backupCount=3, encoding="utf-8")`.
- Stdout handler for dev runs.
- `QueueHandler` shim that pushes records to the wizard's UI queue when Step 4 is active. Thread-safe by virtue of `QueueHandler`.

### `core/config_manager.py`
- `find_config() -> Path | None`
- `read_settings(path: Path) -> configparser.ConfigParser` — opens with `encoding="utf-8"`, tolerates `;` and `#` comments, falls back to `encoding="utf-8-sig"` if BOM.
- `apply_recommended_settings(path: Path, resolution: tuple[int, int]) -> None`
  - Open the file, parse, set `Fullscreen = True`, `ConfineFullScreenMouseCursor = False`, `Resolution = "{w}x{h}"`.
  - If a key is missing, add it under the existing section (do not create a new section if one already exists; otherwise `[General]`).
  - Write to `path.with_suffix(".ini.tmp")`, then `os.replace()` for atomicity.
- `read_setting(path: Path, key: str) -> str | None` — used by Summary page.

### `core/game_detector.py`
- `find_game_installation() -> Path | None` — returns the folder containing `lotroclient.exe`.
- `search_steam_libraries() -> list[Path]` — reads `libraryfolders.vdf` from `C:\Program Files (x86)\Steam\steamapps\`, `D:\Steam\steamapps\`, and the registry (`HKCU\Software\Valve\Steam\SteamPath`). Parses the VDF manually (simple key/value pattern; no need for a full VDF library).
- `is_writable(path: Path) -> bool` — try `os.access(path, os.W_OK)` and a probe `open(path / ".evh_write_test", "w").close()` then delete.

### `core/backup_manager.py`
- Rotation: cap at 5 (`.bak`, `.bak.1`, ... `.bak.5`).
- `create_backup(path: Path, suffix: str = ".bak") -> Path`:
  1. If `<path><suffix>.5` exists, delete it.
  2. Shift chain: `.bak.4`→`.bak.5`, ..., `.bak`→`.bak.1`.
  3. Copy `<path>` → `<path>.bak`.
  4. Return the new backup path.
- `restore_backup(path: Path, suffix: str = ".bak") -> bool`:
  1. Find the newest existing backup (`.bak` first, then `.bak.1`, ...).
  2. Copy backup → original. Atomic via `os.replace()`.

### `core/vulkan_installer.py`
- `install_vulkan(game_dir: Path, source_dir: Path) -> None`
- For each of `[dinput8.ini, dinput8.dll, d3d9.dll]`:
  1. If `dest` exists, call `create_backup(dest, suffix=".backup")` first.
  2. `shutil.copy2(source, dest)`.
- Logs each file copied and any backup created.

### `core/validator.py`
- `ValidationResult` dataclass with bool fields: `config_found, backup_found, game_found, settings_applied, vulkan_installed, fullscreen_set, cursor_unconfined, resolution_set, dll_files_present`. Plus a derived `all_passed` property.
- `run_validation(state: WizardState) -> ValidationResult` — runs all 9 checks. Never raises; returns a result with `False` for the failed check and logs the reason.

### `core/elevation.py`
- `is_writable(path: Path) -> bool`
- `relaunch_as_admin(state: WizardState) -> None`:
  - Serialize `state` to `%TEMP%\evh_state.json`.
  - `ShellExecuteW(NULL, "runas", sys.executable, f'"{sys.argv[0]}" --resume "{state_path}"', NULL, SW_SHOWNORMAL)`.
  - `sys.exit(0)` after launch.
- `load_resume_state() -> WizardState | None` — called at app startup when `--resume` is in `sys.argv`.

## Asset Content

### `assets/vulkan/dinput8.ini` (default; user can edit)
```ini
[dinput8]
# LOTRO Vulkan compatibility — DXVK defaults overridden for stability

[d3d9]
maxFrameLatency = 1
presentInterval = 1
```

(Plan: keep the file minimal. Add a header comment in the actual file pointing to https://github.com/doitsujin/dxvk/wiki for tuning.)

### `assets/vulkan/dinput8.dll`, `d3d9.dll`
Sourced by the user from **https://github.com/doitsujin/dxvk/releases** (latest stable, `dxvk-<ver>.tar.gz` → `dxvk-<ver>/x64/`). MIT licensed. The implementation agent must refuse to build the EXE if these files are missing — print a clear error and exit.

## App Entry & Failure Containment

```python
# app.py sketch
def main():
    setup_logging(Path("logs"))
    logger.info("Startup")
    try:
        state = load_resume_state() or WizardState()
        app = WizardController(initial_state=state)
        app.mainloop()
    except Exception as exc:
        logger.exception("Unexpected error")
        show_fatal_dialog(exc)  # ctk.CTkInputDialog or a small modal
        sys.exit(1)
```

## Build

`requirements.txt`:
```
customtkinter>=5.2.0
screeninfo>=0.8.1
```

`pyinstaller` build command (Windows, run from project root):
```
pyinstaller --onefile --windowed ^
  --name EchoesVulkanHelper ^
  --icon=icon.ico ^
  --add-data "assets/vulkan;assets/vulkan" ^
  --collect-all customtkinter ^
  app.py
```

Output: `dist\EchoesVulkanHelper.exe`.

**Prerequisite guard:** `app.py` checks at startup that `resource_path("assets/vulkan/d3d9.dll")` exists. If missing, show a modal "Vulkan binaries are missing from the installation. Please reinstall." and exit. This catches a botched `pip install` of an asset that the user later deleted.

## Implementation Task Order

The implementation agent should execute in this order. Each task is independently testable.

1. **Scaffold & logger.** Create the directory layout, write `core/logger.py`, write `app.py` skeleton that just opens an empty window and logs "Startup".
2. **Resource path helper & asset guard.** Add `resource_path()` to a new `core/paths.py`. Wire it into `app.py`'s startup check.
3. **Config manager.** Implement `core/config_manager.py` with `find_config()`, `read_settings()`, `apply_recommended_settings()`. Write a small test fixture INI in `tests/fixtures/` to validate.
4. **Game detector.** Implement `core/game_detector.py` with registry + Program Files + Steam VDF + custom paths. Manual test by pointing at a known LOTRO install.
5. **Backup manager.** Implement `core/backup_manager.py` with the rotation chain. Test that 6+ calls cap at `.bak.5`.
6. **Vulkan installer.** Implement `core/vulkan_installer.py` with the `*.backup` rename.
7. **Validator.** Implement `core/validator.py` with the 9 checks.
8. **Elevation helper.** Implement `core/elevation.py` with `ShellExecuteW` via `pywin32` or `ctypes` (prefer `subprocess` with `creationflags` for the relaunch if ShellExecuteW turns out to be flaky; fall back to `ctypes.windll.shell32.ShellExecuteW`).
9. **Wizard controller & bottom bar.** Implement `wizard/controller.py` and a fixed bottom navigation bar.
10. **Welcome page.** Static content + "Restore from backup" footer link + restore dialog.
11. **Detection page.** Wire `find_config` + `find_game_installation` to a worker thread; render ✓/✗; wire Browse buttons; gate Next.
12. **Summary page.** Read current INI, render change list, add resolution override dropdown.
13. **Install page.** Build the queue protocol, progress bar, live log textbox, drain loop. Disable Back/Cancel.
14. **Completion page.** Render success or failure state from `ValidationResult`. Wire Open Folder / Open Logs / Launch / Finish / Restore.
15. **Top-level error containment.** Wrap `mainloop()` in `app.py` with the fatal dialog.
16. **Build & smoke test.** Run `pyinstaller` with the command above. Smoke test on a clean Windows VM: install LOTRO into a non-Program Files folder, run the EXE, confirm all 5 steps complete, confirm `d3d9.dll` and friends are in the game folder, launch the game.
17. **README.** Document the build, the DXVK sourcing step, and the elevation flow.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| `screeninfo` fails on headless / RDP sessions | Catch exception, fall back to `(1920, 1080)`, log warning, still allow Next. |
| `dinput8.ini` content drift (DXVK config schema changes) | Keep the default minimal (3 lines). Surface the file in `assets/vulkan/` so the user can edit. |
| Steam `libraryfolders.vdf` format changes | Hand-parse the simple key=value pattern; on failure, log and skip Steam path. |
| UAC relaunch loses state | Serialize `WizardState` to `%TEMP%\evh_state.json` before relaunch. `app.py` checks for `--resume` and loads it. |
| PyInstaller `--onefile` slow startup | Acceptable for the audience (one-time setup wizard, not a daily driver). Add a small splash `CTkLabel("Loading...")` if first-run startup >2s. |
| `UserPreferences.echoes.ini` encoding edge case | Try `utf-8`, then `utf-8-sig`, then `cp1252`. Never crash on read; if all fail, show "Config file is not readable" and offer Browse. |
| User clicks "Launch Echoes" but game fails to start | No special handling. The subprocess is non-blocking. If we wanted to be thorough: poll for the process to stay alive for 3s and toast a warning. Out of scope for MVP. |

## Validation (matches PRD MVP success criteria)

Each item maps to a test the implementer can run end-to-end on a clean VM:

- [ ] Wizard navigates Welcome → Detection → Summary → Install → Completion.
- [ ] Detection finds a config in the default Documents location without user input.
- [ ] Detection finds a game in `D:\Games\StandaloneLotro\` (or wherever) without user input.
- [ ] Browse buttons set a manual path and unblock Next.
- [ ] A backup `UserPreferences.echoes.ini.bak` exists after Install.
- [ ] Resolution value in the config matches the detected primary monitor.
- [ ] `dinput8.ini`, `dinput8.dll`, `d3d9.dll` exist in the game folder after Install.
- [ ] Pre-existing `dinput8.dll` is renamed to `dinput8.dll.backup` (not overwritten).
- [ ] `run_validation()` returns `all_passed=True` on a clean install.
- [ ] `restore_backup()` reverses the config change.
- [ ] `logs/install.log` contains entries for startup, detection, backup, resolution, config update, install, validation.
- [ ] Install page progress bar moves 0→100 and the log textbox populates live.
- [ ] Completion page shows green checkmarks on success.
- [ ] Completion page shows red ✗ + Restore Backup + Open Logs on a forced failure (simulate by deleting a Vulkan file mid-install in dev).
- [ ] `dist\EchoesVulkanHelper.exe` launches and runs on a clean Windows 10/11 VM with no Python installed.
- [ ] Full user journey (launch → next → next → install → finish) is fewer than 5 clicks.

## Out of Scope (for MVP)

- Unit tests (`pytest`). Can be added in a follow-up phase; the core modules are designed to be testable.
- A "Restore from backup" entry point other than the Welcome footer and the Completion failure state. (No menu, no separate utility.)
- Auto-update. The helper is a one-shot installer.
- Localization. English only.
- Telemetry / crash reporting. Logs are local only.
- A "Settings" or "About" page. Out of scope.
- Code signing. The EXE will be unsigned; Windows SmartScreen will show a warning on first run. Document this in the README with a note for community distributors.

## Open Items

- **Tests:** Recommend deferring to a follow-up. Confirm if the user wants `pytest` scaffolding now.
- **Icon:** ~~User must supply `icon.ico`.~~ Resolved: `assets/EchoesVulkanHelper.ico` (220,293 B / 215 KB) is in place. `app.spec` auto-resolves it.
- **UAC relaunch UX on Windows 11 with SmartScreen:** The unsigned EXE will hit SmartScreen before the UAC prompt. The README should explain "More info → Run anyway" for first-time users.
- **DXVK binaries:** Resolved. `assets/vulkan/dinput8.dll` (11.47 MB), `dinput8.dll` (11.47 MB), `d3d9.dll` (2.28 MB), `dinput8.ini` (904 B) all present. Source: DXVK release at https://github.com/doitsujin/dxvk/releases.

---

## Addendum: GPU / Vulkan 1.3 Pre-Flight Check

### Why
Wasting the user's time installing DXVK on a GPU/driver that cannot run Vulkan 1.3 is the worst possible UX. The check must run **before** the user invests clicks in detection/install.

### New Module: `core/gpu_check.py`
Single function `check_vulkan_support(min_version=(1,3,0)) -> GpuCheckResult`. Best-effort, never raises.

```python
@dataclass
class GpuCheckResult:
    supported: bool
    vulkan_version: tuple[int, int, int] | None
    gpu_name: str | None
    error: str | None
```

### Probes
1. **Vulkan version** — `ctypes.WinDLL("vulkan-1.dll").vkEnumerateInstanceVersion(uint32_t*)`:
   - `dll not loadable` → `vulkan_version=None`, `error="Vulkan runtime not found..."`
   - Return code `!= 0` → same
   - Decode `VK_MAKE_VERSION(major, minor, patch)` from packed uint32:
     - `major = (v >> 22) & 0x7F`
     - `minor = (v >> 12) & 0x3FF`
     - `patch = v & 0xFFF`
2. **GPU name** — `EnumDisplayDevicesW(None, 0, ...)` on the primary display via `ctypes.windll.user32`. Avoids DXGI/COM IID plumbing. `DISPLAY_DEVICEW.DeviceString` is the user-facing name (e.g. "NVIDIA GeForce RTX 4070").

### Comparison
- Supported iff `vulkan_version >= min_version`. Tuple compare is correct because Vulkan uses semantic versioning.
- On fail, `error` text includes the detected version + actionable guidance ("update your GPU drivers").

### Wizard Wiring
Run on **Welcome page** `on_enter` in a worker thread (same pattern as `DetectionPage`):

```python
def on_enter(self, state: WizardState) -> None:
    if state.gpu_check_done:
        return
    threading.Thread(target=self._check_gpu, daemon=True).start()
    self.after(120, self._drain_gpu_check)

def _check_gpu(self) -> None:
    from core.gpu_check import check_vulkan_support
    result = check_vulkan_support()
    self._q.put(("gpu", result))
```

UI:
- Add a card to Welcome page (above the existing "What this wizard will do" card).
- Three states: **Checking...** (spinner text), **OK** (green badge + GPU name + Vulkan version), **FAIL** (red badge + GPU name + error + driver-update help link).
- On fail, store `state.gpu_check_ok = False` and `state.gpu_check_done = True`.

### Blocking
- `WelcomePage.can_advance()` returns `state.gpu_check_done and state.gpu_check_ok`.
- Controller's existing `_refresh_next_state()` is called on every page enter (controller.py:188), so the Next button auto-disables when `can_advance()` flips to False.
- `gpu_check_done` must be True even on failure — otherwise user sees a perpetual "Checking..." state if the probe crashed.

### Edge Cases
- **No `vulkan-1.dll`** (rare on modern Windows; common on locked-down corporate machines): `supported=False`, error explains driver install.
- **`vulkan-1.dll` present but `vkEnumerateInstanceVersion` missing** (old loader, pre-1.1): treated as `supported=False` with version-specific error.
- **Probe crashes** (defensive `try/except Exception` in `check_vulkan_support`): returns `supported=False, error="Vulkan probe failed: <exc>"`.

### Unit Test
Extend `tests/smoke_e2e.py` with a `gpu_check` assertion section. Since most test machines have Vulkan, expect `supported=True` on dev hardware. The negative path is covered by `min_version=(99,0,0)` in a separate test block.

### Files Changed
- **NEW** `core/gpu_check.py` — module (≈80 lines)
- **MOD** `wizard/pages/welcome_page.py` — add GPU card + worker + state plumbing
- **MOD** `wizard/controller.py` — `WizardState.gpu_check_ok: bool = False`, `gpu_check_done: bool = False`
- **MOD** `tests/smoke_e2e.py` — add gpu_check assertion

### Acceptance Criteria
- [ ] On a Vulkan 1.3+ GPU, the Welcome page shows a green OK card with GPU name and version, and Next is enabled.
- [ ] On a Vulkan < 1.3 GPU (simulated via `min_version=(99,0,0)` in test), the card shows red FAIL with actionable text, Next is disabled, and the user cannot proceed.
- [ ] On a machine without `vulkan-1.dll`, the card shows the "Vulkan runtime not found" error and Next is disabled.
- [ ] The check never crashes the app (probe wrapped in `try/except`).
- [ ] `tests/smoke_e2e.py` passes including the new gpu_check assertion.

