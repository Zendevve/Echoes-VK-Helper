# Echoes Vulkan Helper

A lightweight Windows wizard that automates the Vulkan compatibility setup for
LOTRO: Echoes of Angmar. Reduce a multi-step manual process to a few clicks.

## Features

- 5-step wizard (Welcome -> Detection -> Summary -> Install -> Complete)
- Automatic detection of `UserPreferences.echoes.ini` and the game install
- Automatic admin elevation when the game lives in a read-only folder
- Rotating backups of your config and any pre-existing Vulkan files
- Live log and progress bar during install
- Single-click recovery: restore from backup, open logs, open folders
- Single-file EXE build via PyInstaller

## Requirements

- Windows 10 / 11 (x64)
- Python 3.12+ (for dev runs)
- The bundled `assets/vulkan/d3d9.dll` and `dinput8.dll` (DXVK build, x64)
  - Source: https://github.com/doitsujin/dxvk/releases (MIT licensed)

## Dev Run

```bash
pip install -r requirements.txt
python app.py
```

## Build the EXE

```bash
pyinstaller --onefile --windowed ^
  --name EchoesVulkanHelper ^
  --icon=icon.ico ^
  --add-data "assets/vulkan;assets/vulkan" ^
  --collect-all customtkinter ^
  app.py
```

Output: `dist\EchoesVulkanHelper.exe`.

> Note: an unsigned EXE will trigger a Windows SmartScreen warning on first run.
> Community distributors should sign the binary.

## Project Layout

```
echoes-vulkan-helper/
├── app.py
├── core/
│   ├── backup_manager.py
│   ├── config_manager.py
│   ├── elevation.py
│   ├── game_detector.py
│   ├── logger.py
│   ├── paths.py
│   ├── resolution.py
│   ├── validator.py
│   └── vulkan_installer.py
├── wizard/
│   ├── controller.py
│   └── pages/
│       ├── completion_page.py
│       ├── detection_page.py
│       ├── install_page.py
│       ├── summary_page.py
│       └── welcome_page.py
├── assets/vulkan/
│   ├── dinput8.ini
│   ├── dinput8.dll   <- drop DXVK build here
│   └── d3d9.dll      <- drop DXVK build here
└── logs/
```
