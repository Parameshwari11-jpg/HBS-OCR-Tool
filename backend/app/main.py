import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import upload, extract, results, export, originality

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

app = FastAPI(
    title="Text Extractor Tool API",
    description="Extract text from PDF and Word documents including images, OCR, and layered content.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(extract.router)
app.include_router(results.router)
app.include_router(export.router)
app.include_router(originality.router)

@app.get("/api/health")
async def root():
    return {
        "app": "Text Extractor Tool API",
        "status": "online",
        "ocr_engine": "PaddleOCR + PP-StructureV3"
    }

def _warmup_ocr_engines():
    try:
        import threading
        from app.services.extraction_service import extraction_service
        logger.info("Initializing and pre-warming PaddleOCR & PPStructure engines in background...")
        extraction_service.paddle_ocr._init_ocr()
        extraction_service.pp_structure._init_engine()
        logger.info("OCR and PPStructure engines warmed up and ready in memory.")
    except Exception as e:
        logger.warning(f"Engine warm-up exception: {e}")

@app.on_event("startup")
def startup_event():
    import threading
    threading.Thread(target=_warmup_ocr_engines, daemon=True).start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
