# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

BASE = Path(r'C:\Users\Orion Work PC\Desktop\Antigravity Projects\Orion-Desktop-School-System')

a = Analysis(
    [str(BASE / 'main.py')],
    pathex=[str(BASE)],
    binaries=[],
    datas=[
        (str(BASE / 'assets'), 'assets'),
    ],
    hiddenimports=[
        'sqlalchemy.dialects.sqlite',
        'PySide6.QtCharts',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],                      # <-- empty: no bundled binaries (onedir mode)
    exclude_binaries=True,   # <-- key: keeps binaries separate (onedir)
    name='OrionSchoolManagementSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(BASE / 'assets' / 'sms.ico')],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OrionSchoolManagementSystem',   # output folder name inside dist/
)
