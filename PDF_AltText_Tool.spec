# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('frontend/dist', 'frontend/dist'), ('backend', 'backend')],
    hiddenimports=['uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'fastapi', 'starlette', 'starlette.staticfiles', 'starlette.responses', 'pydantic', 'fitz', 'docx', 'docx2pdf', 'PIL', 'cv2', 'numpy', 'scipy', 'shapely', 'pyclipper', 'paddleocr', 'pythoncom', 'win32com.client', 'app.main', 'app.api.upload', 'app.api.extract', 'app.api.results', 'app.api.export', 'app.api.originality', 'app.services.extraction_service', 'app.services.job_service', 'app.services.originality_service', 'app.ocr.paddle_engine', 'app.ocr.pp_structure_engine', 'app.extractors.pdf_extractor', 'app.extractors.docx_extractor'],
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
    a.binaries,
    a.datas,
    [],
    name='PDF_AltText_Tool',
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
