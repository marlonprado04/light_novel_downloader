# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

spec_dir = Path(SPECPATH)

a = Analysis(
    [str(spec_dir / 'main.py')],
    pathex=[str(spec_dir)],
    binaries=[],
    datas=[(str(spec_dir / 'web'), 'web')],
    hiddenimports=['eel', 'cloudscraper', 'bs4', 'requests', 'lxml', 'ebooklib', 'ebooklib.epub'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Light Novel Downloader',
    icon=str(spec_dir / 'icon.ico'),
    version=str(spec_dir / 'version_info.txt'),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)