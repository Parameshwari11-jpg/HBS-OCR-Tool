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
        
    def set_language(self, lang: str):
        if self.lang != lang:
            self.lang = lang
            self._initialized = False
            self._ocr = None
            logger.info(f"PaddleOCR language set to {lang}. Engine will be re-initialized.")

    def _init_ocr(self):
        if self._initialized:
            return
        try:
            # Fix for common Windows OpenMP DLL conflict that causes silent crashes
            os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
            os.environ["FLAGS_allocator_strategy"] = "naive_best_fit"
            
            from paddleocr import PaddleOCR
            
            self._ocr = PaddleOCR(
                use_angle_cls=self.use_angle_cls,
                lang=self.lang,
                show_log=False,
                use_gpu=self.use_gpu
            )
            self._initialized = True
            logger.info("PaddleOCR engine initialized successfully.")
        except Exception as e:
            logger.error(f"PaddleOCR failed to initialize. Root cause: {e}", exc_info=True)
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

            # Step 1: Pre-process OCR lines to detect and merge superscript TM / ™ / M
            raw_candidates = []
            for idx, line in enumerate(ocr_res[0]):
                if not line or len(line) < 2:
                    continue
                bbox_points, (text, confidence) = line[0], line[1]
                xs = [pt[0] for pt in bbox_points]
                ys = [pt[1] for pt in bbox_points]
                bbox = [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))]
                conf_val = float(confidence) if confidence is not None else None
                raw_candidates.append({
                    "orig_idx": idx + 1,
                    "text": text,
                    "bbox": bbox,
                    "confidence": conf_val
                })

            # Check for isolated superscript trademark glyphs (e.g. 'M', 'TM', '™') near top-right of main words
            merged_candidates = []
            used_indices = set()
            n_cand = len(raw_candidates)

            for i in range(n_cand):
                if i in used_indices:
                    continue
                cand_i = raw_candidates[i]
                bbox_i = cand_i["bbox"]
                text_i = cand_i["text"] or ""
                conf_i = cand_i["confidence"] or 0.9

                matched_tm_idx = None
                for j in range(n_cand):
                    if i == j or j in used_indices:
                        continue
                    cand_j = raw_candidates[j]
                    clean_j = (cand_j["text"] or "").strip().upper()
                    if clean_j in ("TM", "™", "M"):
                        bbox_j = cand_j["bbox"]
                        dx = bbox_j[0] - bbox_i[2]
                        h_i = bbox_i[3] - bbox_i[1]
                        h_j = bbox_j[3] - bbox_j[1]
                        # Top-right corner of item i: small superscript
                        if -25.0 <= dx <= 70.0 and bbox_j[1] <= bbox_i[1] + (h_i * 0.45) and h_j <= (h_i * 0.55):
                            matched_tm_idx = j
                            break

                if matched_tm_idx is not None:
                    cand_j = raw_candidates[matched_tm_idx]
                    used_indices.add(matched_tm_idx)
                    used_indices.add(i)
                    bbox_j = cand_j["bbox"]
                    conf_j = cand_j["confidence"] or 0.9

                    # Clean trailing dot if present before TM
                    base_t = text_i.strip()
                    if base_t.endswith("."):
                        base_t = base_t[:-1].strip()
                    combined_text = f"{base_t} TM"
                    combined_bbox = [
                        min(bbox_i[0], bbox_j[0]),
                        min(bbox_i[1], bbox_j[1]),
                        max(bbox_i[2], bbox_j[2]),
                        max(bbox_i[3], bbox_j[3])
                    ]
                    merged_candidates.append({
                        "orig_idx": cand_i["orig_idx"],
                        "text": combined_text,
                        "bbox": combined_bbox,
                        "confidence": (conf_i + conf_j) / 2.0
                    })
                else:
                    used_indices.add(i)
                    merged_candidates.append(cand_i)

            # Step 2: Detect bordered text-boxes (callout boxes / warning frames) and enrich any missed lines
            try:
                import cv2
                from difflib import SequenceMatcher

                # Normalize image array for OpenCV line detection
                if isinstance(img_np, str):
                    cv_img = cv2.imread(img_np)
                elif isinstance(img_np, np.ndarray):
                    cv_img = img_np
                else:
                    cv_img = None

                if cv_img is not None and len(cv_img.shape) >= 2:
                    if len(cv_img.shape) == 3:
                        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
                    else:
                        gray = cv_img

                    bw = cv2.threshold(gray, 230, 255, cv2.THRESH_BINARY_INV)[1]
                    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (80, 1))
                    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 30))
                    h_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, h_kernel)
                    v_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, v_kernel)

                    table_grid = cv2.add(h_lines, v_lines)
                    contours, _ = cv2.findContours(table_grid, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                    detected_boxes = []
                    for c in contours:
                        bx, by, bw_b, bh_b = cv2.boundingRect(c)
                        ar = bw_b / max(1.0, float(bh_b))
                        # Only target genuine wide callout notice/warning boxes (w >= 300, ar >= 3.2)
                        # Prevents non-boxed headings or portrait frames from being falsely cropped
                        if bw_b >= 300 and bh_b >= 28 and ar >= 3.2:
                            detected_boxes.append((bx, by, bw_b, bh_b))

                    filtered_boxes = []
                    for b in detected_boxes:
                        bx, by, bw_b, bh_b = b
                        if not any(abs(bx - fx) < 8 and abs(by - fy) < 8 for fx, fy, fw, fh in filtered_boxes):
                            filtered_boxes.append(b)

                    box_margin = 4
                    box_recovered_items = []
                    for bx, by, bw_b, bh_b in filtered_boxes:
                        crop = cv_img[by + box_margin : by + bh_b - box_margin, bx + box_margin : bx + bw_b - box_margin]
                        if crop.shape[0] < 15 or crop.shape[1] < 30:
                            continue
                        c_ocr = self._ocr.ocr(crop, cls=False)
                        if not c_ocr or not c_ocr[0]:
                            continue
                        for c_line in c_ocr[0]:
                            if not c_line or len(c_line) < 2:
                                continue
                            c_pts, (c_txt, c_conf) = c_line[0], c_line[1]
                            c_xs = [p[0] + bx + box_margin for p in c_pts]
                            c_ys = [p[1] + by + box_margin for p in c_pts]
                            c_bbox = [float(min(c_xs)), float(min(c_ys)), float(max(c_xs)), float(max(c_ys))]
                            box_recovered_items.append((c_bbox, c_txt, float(c_conf)))

                    # Merge recovered box lines into candidates
                    for b_bbox, b_text, b_conf in box_recovered_items:
                        b_clean = b_text.strip()
                        if not b_clean:
                            continue

                        # Look for matching line or fragments that are substrings / parts of b_clean
                        matched_indices = []
                        for idx_m, item_m in enumerate(merged_candidates):
                            p_text = (item_m.get("text") or "").strip()
                            if not p_text:
                                continue
                            sim = SequenceMatcher(None, b_clean.lower(), p_text.lower()).ratio()
                            is_substr = (p_text.lower() in b_clean.lower()) and len(p_text) >= 8
                            if sim >= 0.55 or is_substr:
                                # Also check that vertical position is near the box
                                p_bbox = item_m.get("bbox", [0, 0, 0, 0])
                                if abs(p_bbox[1] - b_bbox[1]) < 40.0:
                                    matched_indices.append(idx_m)

                        if matched_indices:
                            # Replace the first match with the full clean line, and clear the other fragments
                            first_idx = matched_indices[0]
                            merged_candidates[first_idx]["text"] = b_clean
                            merged_candidates[first_idx]["bbox"] = b_bbox
                            merged_candidates[first_idx]["confidence"] = max(merged_candidates[first_idx].get("confidence") or 0.9, b_conf)
                            for redundant_idx in matched_indices[1:]:
                                merged_candidates[redundant_idx]["text"] = ""
                        else:
                            # New un-extracted line inside box (e.g. Harcourt Publishing Company...)
                            merged_candidates.append({
                                "orig_idx": 1000 + len(merged_candidates),
                                "text": b_clean,
                                "bbox": b_bbox,
                                "confidence": b_conf
                            })
            except Exception as e_box:
                logger.debug(f"Box text enrichment note: {e_box}")

            # Filter out any candidates whose text was cleared during deduplication
            merged_candidates = [m for m in merged_candidates if m.get("text") and m["text"].strip()]

            # Sort all items vertically from top to bottom
            merged_candidates.sort(key=lambda x: (x["bbox"][1], x["bbox"][0]))

            for item in merged_candidates:
                text = item["text"]
                bbox = item["bbox"]
                conf_val = item["confidence"]

                # Filter out UI dropdown buttons, caption buttons (_ x), checkboxes, and noise artifacts
                if is_ui_artifact(text, bbox, confidence=conf_val):
                    continue

                cleaned_text = clean_ocr_text(text)
                if not cleaned_text:
                    continue

                if is_ui_artifact(cleaned_text, bbox, confidence=conf_val):
                    continue

                results.append({
                    "id": f"ocr_p{page_num}_{item['orig_idx']}",
                    "page": page_num,
                    "type": "image_text",
                    "source": "ocr",
                    "text": cleaned_text,
                    "confidence": round(float(conf_val or 0.9) * 100, 2),
                    "bbox": bbox
                })
        except Exception as e:
            logger.error(f"Error executing PaddleOCR on page {page_num}: {e}")

        return results
