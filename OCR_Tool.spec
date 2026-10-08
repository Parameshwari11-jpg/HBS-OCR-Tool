# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT_DIR = Path(os.getcwd())

datas = [
    ('frontend/dist', 'frontend/dist'),
    ('backend', 'backend'),
]

binaries = []

try:
    import paddle
    paddle_dir = Path(paddle.__file__).parent
    paddle_libs = paddle_dir / "libs"
    if paddle_libs.exists():
        datas.append((str(paddle_libs), "paddle/libs"))
        datas.append((str(paddle_libs), "paddle/base/../libs"))
        for dll_file in paddle_libs.glob("*.dll"):
            binaries.append((str(dll_file), "."))
            binaries.append((str(dll_file), "paddle/libs"))
        print(f"Collected {len(list(paddle_libs.glob('*.dll')))} Paddle C++ engine DLLs.")
except Exception as e:
    print(f"Spec warning during paddle DLL collection: {e}")

try:
    paddle_datas = collect_data_files('paddleocr', include_py_files=True)
    datas += paddle_datas
    print(f"Spec file collected {len(paddle_datas)} PaddleOCR files.")
except Exception as e:
    print(f"Spec warning during paddleocr data collection: {e}")

hiddenimports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'fastapi',
    'starlette',
    'starlette.staticfiles',
    'starlette.responses',
    'pydantic',
    'fitz',
    'docx',
    'docx2pdf',
    'PIL',
    'cv2',
    'numpy',
    'scipy',
    'shapely',
    'pyclipper',
    'paddleocr',
    'pythoncom',
    'win32com.client',
    'app.main',
    'app.api.upload',
    'app.api.extract',
    'app.api.results',
    'app.api.export',
    'app.api.originality',
    'app.services.extraction_service',
    'app.services.job_service',
    'app.services.originality_service',
    'app.ocr.paddle_engine',
    'app.ocr.pp_structure_engine',
    'app.extractors.pdf_extractor',
    'app.extractors.docx_extractor',
]

try:
    hiddenimports += collect_submodules('paddleocr')
except Exception:
    pass

a = Analysis(
    ['app_launcher.py'],
    pathex=['.', 'backend'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='OCR_Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
