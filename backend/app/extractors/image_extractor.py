import os
import logging
from typing import List, Dict, Any, Optional
from PIL import Image
from app.ocr.paddle_ocr_engine import PaddleOCREngine

logger = logging.getLogger("image_extractor")

class ImageExtractor:
    def __init__(self, ocr_engine: Optional[PaddleOCREngine] = None):
        self.ocr_engine = ocr_engine or PaddleOCREngine()

    def process_image(self, image_path: str, page_num: int = 1, image_id: str = "img_1") -> List[Dict[str, Any]]:
        """Extracts OCR text from an image file."""
        if not os.path.exists(image_path):
            return []
        
        ocr_results = self.ocr_engine.run_ocr(image_path, page_num=page_num)
        for idx, res in enumerate(ocr_results):
            res["image_id"] = image_id
        return ocr_results
