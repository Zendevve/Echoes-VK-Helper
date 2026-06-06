# -*- mode: python ; coding: utf-8 -*-
import os
import sys

from PyInstaller.utils.hooks import collect_all

SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
SRC_ASSETS = os.path.join(SPEC_DIR, "assets", "vulkan")
assert os.path.isdir(SRC_ASSETS), f"Vulkan asset directory missing: {SRC_ASSETS}"

datas = [(SRC_ASSETS, "assets/vulkan")]

excludes = [
    "tests",
    "pydoc",
    "doctest",
]

hiddenimports = [
    "unittest",
    "unittest.mock",
]
binaries = []

try:
    _datas, _binaries, _hiddenimports = collect_all("customtkinter")
    datas += _datas
    binaries += _binaries
    hiddenimports += _hiddenimports
except Exception:
    pass

icon_path = os.path.join(SPEC_DIR, "assets", "EchoesVulkanHelper.ico")
if not os.path.isfile(icon_path):
    icon_path = None

block_cipher = None

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="EchoesVulkanHelper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir="EchoesVulkanHelper",
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)
