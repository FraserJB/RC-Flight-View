# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

added_files = [
    ('splash.png', '.'),
    ('defaults.cfg', '.'),
    ('defaults_ardu.cfg', '.'),
    ('defaults_inav.cfg', '.'),
    ('defaults_edge.cfg', '.'),
    ('defaults_gpx.cfg', '.'),
    ('icon.png', '.'),
    ('LICENSE', '.')
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
        'pyvista', 'vtk', 'pandas', 'numpy', 'matplotlib', 'scipy', 'screeninfo'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['blackbox-tools'],
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
    name='RC Flight View',
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
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RC Flight View',
)
