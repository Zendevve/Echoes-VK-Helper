<!-- generated-by: gsd-doc-writer -->
# Configuration

Echoes Vulkan Helper is a Windows desktop wizard, not a network service. There is no `.env` file, no environment-driven feature flag system, and no dev/staging/prod split. Configuration falls into four buckets: the **game's INI** the wizard manages, the **bundled DXVK/Vulkan runtime** it ships, the **wizard's own on-disk state**, and **logging/backup rotation** that happens automatically.

This page documents every file the helper reads or writes, the environment variables it consults, and the build-time configuration in `app.spec`.

## Environment variables

The helper reads only the environment variables Windows itself provides. There is no `.env` loading and no secrets file. All values are read at runtime; none are required to be set manually.

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `LOCALAPPDATA` | Optional | Falls back to `APPDATA`, then `%USERPROFILE%\AppData\Local` | Primary location for the wizard's persisted state file. Source: `wizard/persistence.py`. |
| `APPDATA` | Optional | Falls back to `%USERPROFILE%\AppData\Local` | Used only when `LOCALAPPDATA` is unset. Source: `wizard/persistence.py`. |
| `TEMP` / `TMP` | Optional | Used implicitly via `tempfile.gettempdir()` | Fallback for the per-user data directory and for transient state files. Source: `core/paths.py`. |
| `USERPROFILE` / `HOME` | Optional | Resolved via `Path.home()` | Used to locate the user's `Documents\Lord of the Rings Online\UserPreferences.echoes.ini`. |

If none of `LOCALAPPDATA`, `APPDATA`, or `tempfile.gettempdir()` are usable, the helper creates a `EchoesVulkanHelper` subfolder under `%TEMP%`. Failures are logged at DEBUG to avoid spamming the user log on startup.

The only other "environment" signal is whether the binary is frozen by PyInstaller (`sys.frozen` and `sys._MEIPASS`); this changes how `core/paths.py` resolves bundled assets (see [Bundled assets and PyInstaller](#bundled-assets-and-pyinstaller)).

## User game config (managed INI)

The helper detects and modifies the game's own configuration file:

- **Path:** `%USERPROFILE%\Documents\Lord of the Rings Online\UserPreferences.echoes.ini`
- **Reader:** `core/config_manager.py` (`find_config`, `read_settings`)
- **Writer:** `core/config_manager.py` (`apply_recommended_settings`)
- **Encoding:** Tolerant chain — `utf-8`, then `utf-8-sig`, then `cp1252`.

The wizard writes the following keys to the `[General]` section, creating the section if absent. Other sections and other keys are preserved verbatim.

| Key | Value written | Source |
| --- | --- | --- |
| `Fullscreen` | `True` | `REQUIRED_KEYS` in `core/config_manager.py` |
| `ConfineFullScreenMouseCursor` | `False` | `REQUIRED_KEYS` in `core/config_manager.py` |
| `Resolution` | `WxH` (e.g. `1920x1080`) | Derived from the user's primary monitor via `screeninfo` |

Writes are atomic: a `UserPreferences.echoes.ini.tmp` file is written first and then renamed with `os.replace`.

### Backup of the user config

Before the helper touches the INI, `core/backup_manager.py` rotates a chain of backups in the same directory:

- **Suffix:** `.bak`
- **Default cap:** 5 (`DEFAULT_CAP` in `core/backup_manager.py`)
- **Layout:** `<name>.bak` (newest) → `<name>.bak.1` → … → `<name>.bak.N` (oldest)
- **Restore:** `restore_backup()` walks slot 0 upward and replaces the live file with the newest existing backup. The wizard's uninstall flow (`core/uninstaller.py`) calls this.

## Bundled Vulkan / DXVK runtime

The helper ships a DXVK build that gets copied into the game directory. These files are stored under `assets/vulkan/` in the source tree and bundled into the EXE at build time.

- **Bundle root (dev):** `<project_root>/assets/vulkan/`
- **Bundle root (frozen):** `sys._MEIPASS/assets/vulkan/`
- **Files (required):** `dinput8.ini`, `dinput8.dll`, `d3d9.dll` (see `ASSET_VULKAN_FILES` in `core/paths.py`)
- **Installer:** `core/vulkan_installer.py` (`install_vulkan`, `rollback`)
- **Backup suffix:** `.backup` (rotating chain, cap 5)

If any of the three files are missing from the bundle, `app.py` aborts startup with a fatal dialog (see `assert_vulkan_assets_present` in `core/paths.py`).

### `dinput8.ini` (DXVK config)

This is a standard DXVK configuration file that controls runtime behaviour for the Vulkan translation layer. The file is shipped as-is and copied verbatim into the game directory. The helper does not edit it.

| Section | Key | Value | Meaning |
| --- | --- | --- | --- |
| `[Render.DXGI]` | `FakeFullscreenMode` | `true` | Use a fake/fullscreen windowed mode that cooperates with DXVK's swapchain. |
| `[Render.DXGI]` | `AutoLowLatency` | `false` | Do not auto-engage low-latency mode by default. |
| `[Render.DXGI]` | `AutoLowLatencyTriggered` | `true` | When low-latency mode is engaged, treat it as user-triggered. |
| `[SpecialK.System]` | `ShowEULA` | `false` | Skip SpecialK EULA prompt. |
| `[SpecialK.System]` | `GlobalInjectDelay` | `0.0` | No delay before injection. |
| `[Steam.Log]` | `Silent` | `true` | Suppress Steam log noise. |
| `[Input.libScePad]` | `Enable` | `false` | Disable PlayStation pad shim. |
| `[Input.XInput]` | `Enable` | `false` | Disable XInput shim. |
| `[Input.XInput]` | `UISlot` | `4` | UI gamepad slot index. |
| `[Input.Gamepad]` | `EnableDirectInput7` | `false` | DirectInput 7 disabled. |
| `[Input.Gamepad]` | `EnableDirectInput8` | `false` | DirectInput 8 disabled. |
| `[Input.Gamepad]` | `EnableHID` | `false` | HID gamepad disabled. |
| `[Input.Gamepad]` | `EnableNativePS4` | `false` | Native PS4 input disabled. |
| `[Input.Gamepad]` | `AllowHapticUI` | `false` | No haptic feedback in UI. |
| `[Input.Keyboard]` | `CatchAltF4` | `false` | Do not trap Alt+F4. |
| `[Input.Keyboard]` | `BypassAltF4Handler` | `false` | Use the default Alt+F4 handler. |

The DXVK build itself (`d3d9.dll`, `dinput8.dll`) is sourced from the upstream DXVK release page (MIT licensed). Replace these two binaries in `assets/vulkan/` to upgrade the DXVK version; `dinput8.ini` is version-independent.

## Wizard persisted state

To avoid re-running detection on every launch, the wizard saves the last-known good paths in a small JSON file.

- **Location:** `%LOCALAPPDATA%\EchoesVKHelper\state.json` (falls back to `%APPDATA%\EchoesVKHelper\state.json`)
- **Code:** `wizard/persistence.py` (`_state_path`, `load_state`, `save_state`)
- **Schema (version 1):**

  ```json
  {
    "version": 1,
    "config_path": "C:\\Users\\<user>\\Documents\\Lord of the Rings Online\\UserPreferences.echoes.ini",
    "game_path":   "D:\\Games\\Echoes of Angmar"
  }
  ```

  Only `version` is required. `config_path` and `game_path` are filled in once the wizard has run detection successfully.

Failures (missing file, malformed JSON, permission errors) are non-fatal — the wizard simply re-runs auto-detection.

A second, transient state file is written by `core/elevation.py` (resume-elevation handshake) at `%TEMP%\EchoesVulkanHelper_state.json`. It is deleted by `app.py` after being read and is not user-editable.

## Logging

Logging is configured in `core/logger.py` and is fully automatic — no flags to set.

| Setting | Value | Source |
| --- | --- | --- |
| Log level | `INFO` | `setup_logging` in `core/logger.py` |
| Format | `%(asctime)s [%(levelname)s] %(threadName)s: %(message)s` | `_LOG_FORMAT` |
| Date format | `%Y-%m-%d %H:%M:%S` | `_DATE_FORMAT` |
| File name | `install.log` | `_attach_file_handler` |
| Max file size | 1,000,000 bytes (1 MB) | `RotatingFileHandler` |
| Backup count | 3 | `RotatingFileHandler` |
| Encoding | `utf-8` | `RotatingFileHandler` |

The log directory is `logs/` under the per-user data directory (see [Where files live on disk](#where-files-live-on-disk)). If the primary directory is not writable, logging falls back to `%TEMP%\<app_name>\logs\`.

The install page can also attach a `_UiQueueHandler` to stream formatted log lines into the GUI in real time; that handler is added/removed by `attach_ui_queue` / `detach_ui_queue`.

## Where files live on disk

The helper writes to three places at runtime. The path used depends on whether the binary is frozen (PyInstaller `--onefile`).

| Purpose | Dev (`python app.py`) | Frozen (`EchoesVulkanHelper.exe`) |
| --- | --- | --- |
| Per-user data dir | `<project_root>` | `%LOCALAPPDATA%\EchoesVulkanHelper` → `%TEMP%\EchoesVulkanHelper` → `<exe_dir>\EchoesVulkanHelper` |
| Logs | `<project_root>\logs\install.log` | `<user_data_dir>\logs\install.log` |
| Wizard state | `%LOCALAPPDATA%\EchoesVKHelper\state.json` | same |
| Resume state (transient) | `%TEMP%\EchoesVulkanHelper_state.json` | same |
| Game config backups | alongside the INI (`.bak` chain) | same |
| Vulkan backups | alongside the DLLs in the game dir (`.backup` chain) | same |

`core/paths.py:user_data_dir` returns the first directory it can successfully `mkdir`; the EXE directory is intentionally tried last because most installs are read-only under `Program Files`.

## Bundled assets and PyInstaller

`app.spec` is the build-time configuration for the single-file EXE. The relevant sections:

- **`datas`** — bundles `<project_root>/assets/vulkan/` into the EXE as `assets/vulkan/`. The spec file hard-fails the build (`assert os.path.isdir(SRC_ASSETS)`) if the source directory is missing.
- **`hiddenimports`** — includes `unittest` and `unittest.mock` so tests packaged inside the EXE still import correctly.
- **`collect_all("customtkinter")`** — pulls in CustomTkinter's theme files and platform-specific assets that PyInstaller's static analyser misses.
- **`icon_path`** — uses `assets/EchoesVulkanHelper.ico` if present; falls back to no icon otherwise.
- **`runtime_tmpdir = "EchoesVulkanHelper"`** — the unpacked bundle lives under `%TEMP%\EchoesVulkanHelper\` at runtime.
- **`excludes`** — drops `tests`, `pydoc`, `doctest` from the bundle to keep the EXE small.

Equivalent one-liner (used during local builds; see README):

```bash
pyinstaller --onefile --windowed \
  --name EchoesVulkanHelper \
  --icon=icon.ico \
  --add-data "assets/vulkan;assets/vulkan" \
  --collect-all customtkinter \
  app.py
```

## App constants

Two constants are exposed at runtime and may appear in logs and dialogs.

| Constant | Value | Source |
| --- | --- | --- |
| `__app_name__` | `"Echoes Vulkan Helper"` | `core/__init__.py` |
| `__version__` | `"0.1.0"` | `core/__init__.py` (dynamic, consumed by `pyproject.toml`) |
| `APP_NAME` | `"EchoesVulkanHelper"` | `core/paths.py` (used for log dirs and `%TEMP%` subfolder) |
| `APP_DIRNAME` | `"EchoesVKHelper"` | `wizard/persistence.py` (used for `%LOCALAPPDATA%` subfolder) |

Note the subtle distinction: `APP_NAME = "EchoesVulkanHelper"` is the filesystem/EXE stem, while `APP_DIRNAME = "EchoesVKHelper"` is the older state-file directory. They are not interchangeable. Renaming either one will break upgrade continuity for existing users.

## Required vs optional settings

There is no startup-validation step in the code; nothing throws if a setting is missing. The "required" list is, in effect, the set of files whose absence causes a fatal error dialog before the wizard opens:

- **Required (fatal if missing):** the three Vulkan files in `assets/vulkan/` (`dinput8.ini`, `dinput8.dll`, `d3d9.dll`). Checked by `assert_vulkan_assets_present()` in `app.py`.
- **Optional (degrades gracefully):** `UserPreferences.echoes.ini` (if absent, the wizard shows a manual-browse step on the Detection page).
- **Optional (regenerated on demand):** the wizard state file, the install log, and all backup chains.

## Defaults summary

| Setting | Default | Defined in |
| --- | --- | --- |
| Config backup suffix | `.bak` | `core/backup_manager.py` |
| Vulkan backup suffix | `.backup` | `core/vulkan_installer.py` |
| Backup chain cap | 5 | `DEFAULT_CAP` in `core/backup_manager.py` |
| Log file max size | 1 MB | `core/logger.py` |
| Log backup count | 3 | `core/logger.py` |
| Log level | `INFO` | `core/logger.py` |
| Vulkan files copied | `dinput8.ini`, `dinput8.dll`, `d3d9.dll` | `VULKAN_FILES` in `core/vulkan_installer.py` |
| INI keys written | `Fullscreen=True`, `ConfineFullScreenMouseCursor=False`, `Resolution=WxH` | `REQUIRED_KEYS` in `core/config_manager.py` |
| INI target section | `General` (created if missing) | `apply_recommended_settings` in `core/config_manager.py` |
| State schema version | `1` | `STATE_VERSION` in `wizard/persistence.py` |

## Per-environment overrides

There are none. The helper is a single-binary desktop tool. Build-time choices (icon, includes, runtime temp dir) live in `app.spec` and are baked into the EXE. Runtime choices (DPI, monitor) are read from the host operating system at launch.

<!-- VERIFY: Specific DXVK INI key semantics (e.g. AutoLowLatencyTriggered, SpecialK.System.GlobalInjectDelay) — values verified against the shipped file, but their behavioural effect on this particular game build is not independently confirmed from source. -->
