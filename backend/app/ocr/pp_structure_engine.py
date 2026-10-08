import os
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from PIL import Image

logger = logging.getLogger("pp_structure_engine")

class PPStructureEngine:
    def __init__(self, lang: str = "en", use_gpu: bool = False):
        self.lang = lang
        self.use_gpu = use_gpu
        self._engine = None
        self._initialized = False

    def _init_engine(self):
        if self._initialized:
            return
        try:
            try:
                from paddleocr import PPStructure
            except ImportError:
                try:
                    from paddleocr.ppstructure.predict_system import PPStructure
                except ImportError:
                    PPStructure = None

            if PPStructure is None:
                logger.warning("PPStructure class not available in installed paddleocr version. Document layout will rely on Visual Layout Detector.")
                self._engine = None
                self._initialized = True
                return

            engine_instance = None
            configs = [
                {"lang": self.lang, "layout": True, "table": False},
                {"lang": self.lang},
                {"show_log": False, "image_orientation": False, "use_gpu": self.use_gpu, "lang": self.lang, "layout": True, "table": False},
                {}
            ]

            for cfg in configs:
                try:
                    engine_instance = PPStructure(**cfg)
                    break
                except Exception:
                    continue

            self._engine = engine_instance
            self._initialized = True
            if self._engine is not None:
                logger.info("PPStructure engine initialized successfully.")
            else:
                logger.warning("PPStructure could not be initialized with compatible arguments. Relying on Visual Layout Detector.")
        except Exception as e:
            logger.warning(f"PPStructure failed to initialize: {e}. Will handle gracefully.")
            self._engine = None
            self._initialized = True

    def analyze_structure(self, image_input: Any, page_num: int = 1) -> List[Dict[str, Any]]:
        """
        Analyzes document structure using PPStructure.
        Returns list of structured elements (regions, tables, formulas, titles, etc.).
        """
        self._init_engine()
        results = []
        
        if self._engine is None:
            return results

        try:
            scale_ratio = 1.0
            if isinstance(image_input, str):
                pil_img = Image.open(image_input).convert("RGB")
            elif isinstance(image_input, Image.Image):
                pil_img = image_input.convert("RGB")
            elif isinstance(image_input, np.ndarray):
                pil_img = Image.fromarray(image_input)
            else:
                pil_img = None

            if pil_img is not None:
                orig_w, orig_h = pil_img.size
                max_dim = max(orig_w, orig_h)
                if max_dim > 1024:
                    scale_ratio = 1024.0 / max_dim
                    new_w = int(orig_w * scale_ratio)
                    new_h = int(orig_h * scale_ratio)
                    pil_img = pil_img.resize((new_w, new_h), Image.Resampling.BILINEAR)
                img_np = np.array(pil_img)
            else:
                img_np = image_input

            res = self._engine(img_np)
            
            for idx, region in enumerate(res):
                region_type = region.get("type", "text").lower()
                raw_bbox = region.get("bbox", [0, 0, 0, 0])
                bbox = [float(b) / scale_ratio for b in raw_bbox]
                
                res_data = {
                    "id": f"pp_p{page_num}_{idx+1}",
                    "page": page_num,
                    "type": region_type,
                    "source": "pp_structure",
                    "bbox": bbox
                }
                
                # Check for table structure inside region
                if region_type == "table" and "res" in region:
                    table_info = region["res"]
                    if isinstance(table_info, dict) and "html" in table_info:
                        # Convert html table or cell list to row grid
                        cell_list = table_info.get("cell_bbox", [])
                        # html extraction if available
                        res_data["html"] = table_info.get("html", "")
                    res_data["type"] = "table"
                elif region_type == "equation" or region_type == "formula":
                    res_data["type"] = "formula"
                    res_data["text"] = region.get("res", {}).get("text", "") if isinstance(region.get("res"), dict) else None
                else:
                    # Regular text region
                    res_text = ""
                    if "res" in region and isinstance(region["res"], list):
                        line_texts = [line.get("text", "") for line in region["res"] if isinstance(line, dict) and "text" in line]
                        res_text = "\n".join(line_texts)
                    res_data["text"] = res_text if res_text else None
                    
                results.append(res_data)
        except Exception as e:
            logger.error(f"Error executing PPStructure on page {page_num}: {e}")

        return results
