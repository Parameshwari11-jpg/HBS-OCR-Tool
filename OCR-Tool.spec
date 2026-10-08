# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect data files for Paddle, PyMuPDF, etc.
datas = [
    ('frontend/dist', 'frontend/dist'),
    ('backend', 'backend'),
]

# Add paddleocr / paddlex / pyclipper data files if available
try:
    datas += collect_data_files('paddleocr')
except Exception:
    pass

try:
    datas += collect_data_files('fitz')
except Exception:
    pass

hiddenimports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.httptools_impl',
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

hiddenimports += collect_submodules('backend')

a = Analysis(
    ['app_launcher.py'],
    pathex=['.', 'backend'],
    binaries=[],
    datas=datas,
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
    name='OCR-Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OCR-Tool',
)
