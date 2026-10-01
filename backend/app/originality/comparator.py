import os
import uuid
import shutil
import datetime
import logging
from typing import Dict, Any, Optional, Callable, List
import pymupdf

from app.utils.file_utils import get_job_temp_dir
from app.originality.models import (
    OriginalityReport,
    PageOriginalityResult,
    StatusType,
    DifferenceType,
    SeverityLevel,
    MismatchItem,
)
from app.originality.pdf_checker import PDFOriginalityChecker
from app.originality.docx_checker import DOCXOriginalityChecker
from app.originality.accuracy import AccuracyCalculator

logger = logging.getLogger("comparator")


class OriginalityComparator:
    """
    Central orchestration service for originality verification and accuracy analysis.
    """

    def __init__(self, ocr_processor: Optional[Any] = None):
        self.ocr_processor = ocr_processor
        self.pdf_checker = PDFOriginalityChecker(ocr_processor=ocr_processor)
        self.docx_checker = DOCXOriginalityChecker()
        # In-memory store for generated reports
        self.reports_cache: Dict[str, OriginalityReport] = {}

    def compare(
        self,
        original_file_path: str,
        extracted_text: str,
        original_filename: Optional[str] = None,
        extracted_filename: Optional[str] = None,
        job_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> OriginalityReport:
        """
        Runs comprehensive originality check comparing original PDF/DOCX document
        against extracted text content.
        """
        orig_fn = original_filename or os.path.basename(original_file_path)
        ext_fn = extracted_filename or "extracted_text.txt"
        file_ext = os.path.splitext(original_file_path)[1].lower()

        logger.info(f"Starting originality check for {orig_fn} against {ext_fn}")

        if file_ext == ".pdf":
            file_type = "pdf"
            pages = self.pdf_checker.check_pdf(
                pdf_path=original_file_path,
                extracted_text=extracted_text,
                progress_callback=progress_callback
            )
        elif file_ext in (".docx", ".doc"):
            file_type = "docx"
            # 1. Prefer existing converted PDF from extraction job (preserves exact full visual pages & layout)
            converted_pdf_path = None
            if job_id:
                candidate = get_job_temp_dir(job_id) / "original_converted.pdf"
                if candidate.exists():
                    converted_pdf_path = str(candidate)

            if converted_pdf_path:
                pages = self.pdf_checker.check_pdf(
                    pdf_path=converted_pdf_path,
                    extracted_text=extracted_text,
                    progress_callback=progress_callback,
                    docx_source_path=original_file_path
                )
            else:
                # 2. Try direct PyMuPDF page-by-page verification for Word documents
                try:
                    mupdf_doc = pymupdf.open(original_file_path)
                    has_pages = len(mupdf_doc) > 0
                    mupdf_doc.close()
                    if has_pages:
                        pages = self.pdf_checker.check_pdf(
                            pdf_path=original_file_path,
                            extracted_text=extracted_text,
                            progress_callback=progress_callback,
                            docx_source_path=original_file_path
                        )
                    else:
                        pages = self.docx_checker.check_docx(
                            docx_path=original_file_path,
                            extracted_text=extracted_text,
                            progress_callback=progress_callback
                        )
                except Exception as ex_mupdf:
                    logger.warning(f"PyMuPDF direct docx check failed, using docx_checker: {ex_mupdf}")
                    pages = self.docx_checker.check_docx(
                        docx_path=original_file_path,
                        extracted_text=extracted_text,
                        progress_callback=progress_callback
                    )
        else:
            raise ValueError(f"Unsupported file type: {file_ext}. Only PDF and Word (.docx) are supported.")

        # Aggregate document statistics
        all_mismatches: List[MismatchItem] = [mm for p in pages for mm in p.mismatches]

        passed_pages = sum(1 for p in pages if p.status == StatusType.PASS)
        warning_pages = sum(1 for p in pages if p.status == StatusType.WARNING)
        error_pages = sum(1 for p in pages if p.status == StatusType.ERROR)

        total_orig_words = sum(p.orig_word_count for p in pages)
        total_extracted_words = sum(p.extracted_word_count for p in pages)

        missing_words = sum(1 for m in all_mismatches if m.diff_type == DifferenceType.MISSING_TEXT)
        extra_words = sum(1 for m in all_mismatches if m.diff_type == DifferenceType.EXTRA_TEXT)
        changed_words = sum(1 for m in all_mismatches if m.diff_type == DifferenceType.WORD_MISMATCH)
        char_errors = sum(len(m.char_diffs) for m in all_mismatches if m.diff_type == DifferenceType.CHARACTER_MISMATCH)
        num_mismatches = sum(1 for m in all_mismatches if m.diff_type == DifferenceType.NUMBER_MISMATCH)
        punct_mismatches = sum(1 for m in all_mismatches if m.diff_type == DifferenceType.PUNCTUATION_MISMATCH)
        ro_issues = sum(1 for m in all_mismatches if m.diff_type == DifferenceType.READING_ORDER)

        overall_accuracy, verification_status = AccuracyCalculator.calculate_overall_accuracy(pages, all_mismatches)

        # Summary notes
        summary_notes: List[str] = []
        if verification_status == StatusType.PASS:
            summary_notes.append("The extracted text is an exceptionally accurate representation of the original document.")
        elif verification_status == StatusType.WARNING:
            summary_notes.append(f"Minor extraction discrepancies detected across {warning_pages} page(s). Review recommended.")
        else:
            summary_notes.append(f"Critical mismatches detected across {error_pages} page(s). Important content or numbers differ.")

        if num_mismatches > 0:
            summary_notes.append(f"Caution: {num_mismatches} numeric mismatch(es) detected. Review numbers carefully.")
        if ro_issues > 0:
            summary_notes.append(f"Note: {ro_issues} reading order transposition(s) identified.")

        report_id = str(uuid.uuid4())

        # Populate preview image URLs and generate rendered preview images
        try:
            report_temp = get_job_temp_dir(report_id)
            if job_id:
                job_temp = get_job_temp_dir(job_id)
                for p in pages:
                    src_img = job_temp / f"page_{p.page}.png"
                    dst_img = report_temp / f"page_{p.page}.png"
                    if src_img.exists() and not dst_img.exists():
                        shutil.copyfile(str(src_img), str(dst_img))

            # Fallback: render directly with PyMuPDF for any missing page images
            try:
                render_source = original_file_path
                if job_id:
                    cand = get_job_temp_dir(job_id) / "original_converted.pdf"
                    if cand.exists():
                        render_source = str(cand)

                mupdf_doc = pymupdf.open(render_source)
                for p in pages:
                    dst_img = report_temp / f"page_{p.page}.png"
                    if not dst_img.exists() and (p.page - 1) < len(mupdf_doc):
                        pix = mupdf_doc[p.page - 1].get_pixmap(dpi=150)
                        pix.save(str(dst_img))
                mupdf_doc.close()
            except Exception as e_pdf:
                logger.warning(f"Could not render PDF preview images: {e_pdf}")

            for p in pages:
                p.preview_image_url = f"/api/originality/preview/{report_id}/{p.page}"
        except Exception as ex:
            logger.warning(f"Error preparing preview images: {ex}")

        report = OriginalityReport(
            report_id=report_id,
            job_id=job_id,
            preview_available=True,
            original_filename=orig_fn,
            extracted_filename=ext_fn,
            file_type=file_type,
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            overall_accuracy=overall_accuracy,
            verification_status=verification_status,
            total_pages=len(pages),
            passed_pages=passed_pages,
            warning_pages=warning_pages,
            error_pages=error_pages,
            total_orig_words=total_orig_words,
            total_extracted_words=total_extracted_words,
            missing_words=missing_words,
            extra_words=extra_words,
            changed_words=changed_words,
            character_errors=char_errors,
            number_mismatches=num_mismatches,
            punctuation_mismatches=punct_mismatches,
            reading_order_issues=ro_issues,
            pages=pages,
            summary_notes=summary_notes
        )

        self.reports_cache[report_id] = report
        return report

    def get_report(self, report_id: str) -> Optional[OriginalityReport]:
        return self.reports_cache.get(report_id)


# Global singleton instance
originality_comparator = OriginalityComparator()
