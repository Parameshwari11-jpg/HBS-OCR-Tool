import os
import logging
from typing import Optional
from pathlib import Path

from app.models.extraction_models import ExtractionResult, PageData, ExtractionStatistics
from app.services.job_service import job_service
from app.extractors.pdf_extractor import PDFExtractor
from app.extractors.docx_extractor import DOCXExtractor
from app.ocr.paddle_ocr_engine import PaddleOCREngine
from app.ocr.pp_structure_engine import PPStructureEngine
from app.utils.file_utils import get_job_temp_dir
from app.utils.normalization import is_ui_artifact, clean_ocr_text

logger = logging.getLogger("extraction_service")

class ExtractionService:
    def __init__(self):
        # Instantiate engines once
        self.paddle_ocr = PaddleOCREngine()
        self.pp_structure = PPStructureEngine()
        self.pdf_extractor = PDFExtractor(ocr_engine=self.paddle_ocr, structure_engine=self.pp_structure)
        self.docx_extractor = DOCXExtractor(ocr_engine=self.paddle_ocr, structure_engine=self.pp_structure)

    def process_document(self, job_id: str, file_path: str, filename: str, file_type: str):
        try:
            def on_progress(
                stage: str,
                progress: int,
                current_page: Optional[int] = None,
                total_pages: Optional[int] = None,
                message: Optional[str] = None
            ):
                job_service.update_job_status(
                    job_id=job_id,
                    status="processing",
                    stage=stage,
                    progress=progress,
                    current_page=current_page,
                    total_pages=total_pages,
                    stage_message=message
                )

            on_progress("parsing", 10, None, None, f"Parsing and initializing {filename}...")
            temp_dir = str(get_job_temp_dir(job_id))

            if file_type == "pdf":
                res = self.pdf_extractor.extract_pdf(file_path, temp_dir, progress_callback=on_progress)
            elif file_type == "docx":
                res = self.docx_extractor.extract_docx(file_path, temp_dir, progress_callback=on_progress)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            pages: list[PageData] = res["pages"]
            total_pages_count = len(pages)
            on_progress("finalizing", 94, total_pages_count, total_pages_count, "Structuring reading order and assembling text content...")

            statistics: ExtractionStatistics = res["statistics"]

            # Reconstruct full text in reading order with page boundaries
            reconstructed_lines = []
            for p in pages:
                reconstructed_lines.append(f"--- Page {p.page} ---")
                valid_elems = [e for e in p.elements if not e.possible_duplicate and e.type not in ("image", "figure")]
                sorted_elems = sorted(valid_elems, key=lambda e: (
                    e.reading_order if e.reading_order is not None and e.reading_order > 0 else 99999,
                    e.bbox[1] if e.bbox else 99999,
                    e.bbox[0] if e.bbox else 99999
                ))
                for elem in sorted_elems:
                    if elem.text and elem.text.strip():
                        if is_ui_artifact(elem.text, elem.bbox, confidence=elem.confidence):
                            continue
                        cleaned_txt = clean_ocr_text(elem.text) if elem.source == "ocr" else elem.text.strip()
                        if cleaned_txt and not is_ui_artifact(cleaned_txt, elem.bbox, confidence=elem.confidence):
                            reconstructed_lines.append(cleaned_txt)
                reconstructed_lines.append("") # Blank line after page

            reconstructed_text = "\n".join(reconstructed_lines)

            result = ExtractionResult(
                job_id=job_id,
                filename=filename,
                file_type=file_type,
                is_tagged_document=res.get("is_tagged_document", False),
                tagging_summary=res.get("tagging_summary"),
                pages=pages,
                statistics=statistics,
                reconstructed_text=reconstructed_text
            )

            job_service.save_result(job_id, result)
            job_service.update_job_status(
                job_id,
                status="completed",
                stage="completed",
                progress=100,
                current_page=total_pages_count,
                total_pages=total_pages_count,
                stage_message=f"Successfully extracted {total_pages_count} pages!"
            )
            logger.info(f"Extraction for job {job_id} completed successfully.")

        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}", exc_info=True)
            job_service.update_job_status(
                job_id,
                status="failed",
                stage="failed",
                progress=100,
                stage_message="Extraction failed.",
                error=str(e)
            )

extraction_service = ExtractionService()
