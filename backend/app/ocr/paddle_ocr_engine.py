import os
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from PIL import Image

from app.utils.normalization import is_ui_artifact, clean_ocr_text

logger = logging.getLogger("paddle_ocr_engine")

class PaddleOCREngine:
    def __init__(self, lang: str = "en", use_angle_cls: bool = False, use_gpu: bool = False):
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self.use_gpu = use_gpu
        self._ocr = None
        self._initialized = False
        
    def _init_ocr(self):
        if self._initialized:
            return
        try:
            from paddleocr import PaddleOCR
            # Suppress verbose paddle logging
            os.environ["FLAGS_allocator_strategy"] = "naive_best_fit"
            self._ocr = PaddleOCR(
                use_angle_cls=self.use_angle_cls,
                lang=self.lang,
                show_log=False,
                use_gpu=self.use_gpu
            )
            self._initialized = True
            logger.info("PaddleOCR engine initialized successfully.")
        except Exception as e:
            logger.warning(f"PaddleOCR failed to initialize: {e}. Will use fallback or retry.")
            self._ocr = None
            self._initialized = True

    def run_ocr(self, image_input: Any, page_num: int = 1) -> List[Dict[str, Any]]:
        """
        Runs PaddleOCR on an image (filepath, PIL Image, or numpy array).
        Returns list of detected items with text, confidence, and bbox [x0, y0, x1, y1].
        """
        self._init_ocr()
        
        results = []
        if self._ocr is None:
            logger.warning("PaddleOCR is not available.")
            return results

        try:
            if isinstance(image_input, Image.Image):
                img_np = np.array(image_input)
            elif isinstance(image_input, str):
                img_np = image_input
            else:
                img_np = image_input

            ocr_res = self._ocr.ocr(img_np, cls=self.use_angle_cls)
            
            if not ocr_res or len(ocr_res) == 0 or ocr_res[0] is None:
                return results

            for idx, line in enumerate(ocr_res[0]):
                if not line or len(line) < 2:
                    continue
                bbox_points, (text, confidence) = line[0], line[1]
                
                # Convert 4 points [[x0,y0], [x1,y0], [x1,y1], [x0,y1]] to bbox [x0, y0, x1, y1]
                xs = [pt[0] for pt in bbox_points]
                ys = [pt[1] for pt in bbox_points]
                bbox = [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))]
                
                # Filter out UI dropdown buttons, caption buttons (_ x), checkboxes, and noise artifacts
                conf_val = float(confidence) if confidence is not None else None
                if is_ui_artifact(text, bbox, confidence=conf_val):
                    continue

                cleaned_text = clean_ocr_text(text)
                if not cleaned_text:
                    continue

                if is_ui_artifact(cleaned_text, bbox, confidence=conf_val):
                    continue

                results.append({
                    "id": f"ocr_p{page_num}_{idx+1}",
                    "page": page_num,
                    "type": "image_text",
                    "source": "ocr",
                    "text": cleaned_text,
                    "confidence": round(float(confidence) * 100, 2),
                    "bbox": bbox
                })
        except Exception as e:
            logger.error(f"Error executing PaddleOCR on page {page_num}: {e}")

        return results
