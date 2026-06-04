# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules


block_cipher = None


def not_tests(module_name):
    return ".tests" not in module_name and not module_name.endswith(".tests")


hiddenimports = (
    ["matplotlib.backends.backend_qtagg"]
    + collect_submodules("h5netcdf", filter=not_tests)
    + collect_submodules("netCDF4", filter=not_tests)
    + collect_submodules("h5py", filter=not_tests)
    + collect_submodules("igor2", filter=not_tests)
    + collect_submodules("openpyxl", filter=not_tests)
    + collect_submodules("xarray", filter=not_tests)
)

a = Analysis(
    ["converter_app.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="converter_app",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="converter_app",
)
