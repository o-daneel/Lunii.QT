# -*- mode: python ; coding: utf-8 -*-
import sys

block_cipher = None


a = Analysis(
    ['lunii-qt.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
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

# Exclude splash screen for MacOS
if sys.platform != 'darwin':
    splash = Splash(
        './res/lunii_splash_pyinst.png',
        binaries=a.binaries,
        datas=a.datas,
        text_pos=(42, 405),
        text_size=8,
        minify_script=True,
        always_on_top=True,
    )
else:
    splash = []

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    splash,
    splash.binaries if hasattr(splash, 'binaries') else [],
    [],
    name='lunii-qt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='res/lunii.ico'
)
