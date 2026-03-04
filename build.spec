# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icon.ico', '.'),
        ('icon.png', '.'),
    ],
    hiddenimports=[
        'clr',
        'webview',
        'pystray._win32',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TodoMateWidget',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='icon.ico',
    disable_windowed_traceback=False,
    # 버전 정보 (Windows 탐색기에서 표시됨)
    version_info={
        'CompanyName': 'TodoMate Widget',
        'FileDescription': 'TodoMate Floating Widget for Windows',
        'FileVersion': '1.0.0.0',
        'InternalName': 'TodoMateWidget',
        'OriginalFilename': 'TodoMateWidget.exe',
        'ProductName': 'TodoMate Widget',
        'ProductVersion': '1.0.0.0',
    } if False else None,  # version_info는 별도 파일로 처리 (아래 참고)
)
