import io
import csv
import json
import pymupdf  # PyMuPDF
from typing import Dict, Any
from app.originality.models import OriginalityReport, StatusType, SeverityLevel


class ReportGenerator:
    """
    Exports originality verification results to PDF, JSON, and CSV reports.
    """

    @classmethod
    def generate_json(cls, report: OriginalityReport) -> str:
        """
        Generates machine-readable JSON matching specifications.
        """
        return json.dumps(report.model_dump(), indent=2, ensure_ascii=False)

    @classmethod
    def generate_csv(cls, report: OriginalityReport) -> str:
        """
        Generates structured CSV containing summary, page breakdown, and detailed mismatches.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # 1. Header & Summary Info
        writer.writerow(["ORIGINALITY & EXTRACTION ACCURACY VERIFICATION REPORT"])
        writer.writerow(["Report ID", report.report_id])
        writer.writerow(["Original File", report.original_filename])
        writer.writerow(["Extracted File", report.extracted_filename])
        writer.writerow(["File Type", report.file_type.upper()])
        writer.writerow(["Verification Date", report.timestamp])
        writer.writerow(["Overall Accuracy", f"{report.overall_accuracy}%"])
        writer.writerow(["Verification Status", report.verification_status])
        writer.writerow([])

        # 2. KPI Metrics
        writer.writerow(["SUMMARY METRICS"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Pages", report.total_pages])
        writer.writerow(["Passed Pages", report.passed_pages])
        writer.writerow(["Warning Pages", report.warning_pages])
        writer.writerow(["Error Pages", report.error_pages])
        writer.writerow(["Total Original Words", report.total_orig_words])
        writer.writerow(["Total Extracted Words", report.total_extracted_words])
        writer.writerow(["Missing Words", report.missing_words])
        writer.writerow(["Extra Words", report.extra_words])
        writer.writerow(["Changed Words", report.changed_words])
        writer.writerow(["Character Errors", report.character_errors])
        writer.writerow(["Number Mismatches", report.number_mismatches])
        writer.writerow(["Punctuation Mismatches", report.punctuation_mismatches])
        writer.writerow([])

        # 3. Page-wise breakdown
        writer.writerow(["PAGE-WISE RESULTS"])
        writer.writerow(["Page", "Original Words", "Extracted Words", "Accuracy (%)", "Status", "Verification Type", "Mismatches Count"])
        for p in report.pages:
            writer.writerow([
                p.page,
                p.orig_word_count,
                p.extracted_word_count,
                f"{p.accuracy}%",
                p.status,
                p.verification_type,
                len(p.mismatches)
            ])
        writer.writerow([])

        # 4. Detailed Mismatch Inventory
        writer.writerow(["DETAILED MISMATCHES"])
        writer.writerow(["Page", "Line/Location", "Type", "Severity", "Original Text", "Extracted Text", "Difference Details"])
        for p in report.pages:
            for m in p.mismatches:
                writer.writerow([
                    m.page,
                    m.location,
                    m.diff_type,
                    m.severity,
                    m.orig_text,
                    m.extracted_text,
                    m.difference
                ])

        return output.getvalue()

    @classmethod
    def generate_pdf(cls, report: OriginalityReport) -> bytes:
        """
        Generates a professional PDF report using PyMuPDF.
        """
        doc = pymupdf.open()
        
        # Color palette (RGB floats 0..1)
        NAVY = (0.08, 0.12, 0.22)
        SLATE = (0.28, 0.35, 0.45)
        LIGHT_BG = (0.96, 0.97, 0.98)
        DARK_TEXT = (0.12, 0.15, 0.2)
        WHITE = (1.0, 1.0, 1.0)
        
        # Status colors
        if report.verification_status == StatusType.PASS:
            STATUS_COLOR = (0.06, 0.65, 0.38) # Emerald
        elif report.verification_status == StatusType.WARNING:
            STATUS_COLOR = (0.85, 0.55, 0.05) # Amber
        else:
            STATUS_COLOR = (0.88, 0.22, 0.25) # Rose

        page = doc.new_page(width=595.3, height=841.9) # A4
        y = 40

        # Header banner
        page.draw_rect(pymupdf.Rect(40, y, 555.3, y + 65), color=None, fill=NAVY)
        page.insert_text(pymupdf.Point(55, y + 26), "Universal Document Text Extractor", fontsize=11, color=(0.7, 0.8, 1.0))
        page.insert_text(pymupdf.Point(55, y + 48), "Extraction Accuracy & Originality Verification Report", fontsize=16, color=WHITE)
        y += 80

        # Metadata grid
        page.draw_rect(pymupdf.Rect(40, y, 555.3, y + 75), color=(0.85, 0.88, 0.92), fill=LIGHT_BG)
        page.insert_text(pymupdf.Point(55, y + 20), f"Original Document: {report.original_filename}", fontsize=9, color=DARK_TEXT)
        page.insert_text(pymupdf.Point(55, y + 36), f"Extracted Text File: {report.extracted_filename}", fontsize=9, color=DARK_TEXT)
        page.insert_text(pymupdf.Point(55, y + 52), f"Verification Date: {report.timestamp}", fontsize=9, color=SLATE)
        page.insert_text(pymupdf.Point(55, y + 66), f"Report ID: {report.report_id[:18]}...", fontsize=8, color=SLATE)

        # Status Badge
        badge_rect = pymupdf.Rect(410, y + 15, 540, y + 60)
        page.draw_rect(badge_rect, color=None, fill=STATUS_COLOR)
        page.insert_text(pymupdf.Point(420, y + 34), f"{report.overall_accuracy}%", fontsize=16, color=WHITE)
        page.insert_text(pymupdf.Point(420, y + 50), f"STATUS: {report.verification_status}", fontsize=9, color=WHITE)
        y += 90

        # Summary KPIs Box
        page.insert_text(pymupdf.Point(40, y + 14), "VERIFICATION SUMMARY", fontsize=12, color=NAVY)
        y += 24

        kpis = [
            ("Total Pages", str(report.total_pages)),
            ("Passed", str(report.passed_pages)),
            ("Warnings", str(report.warning_pages)),
            ("Errors", str(report.error_pages)),
            ("Missing Words", str(report.missing_words)),
            ("Extra Words", str(report.extra_words)),
            ("Changed Words", str(report.changed_words)),
            ("Number Errors", str(report.number_mismatches)),
        ]

        card_w = 60
        card_h = 42
        for idx, (lbl, val) in enumerate(kpis):
            col = idx % 4
            row = idx // 4
            cx = 40 + col * (120 + 8)
            cy = y + row * (card_h + 8)
            page.draw_rect(pymupdf.Rect(cx, cy, cx + 120, cy + card_h), color=(0.85, 0.88, 0.92), fill=(0.98, 0.98, 0.99))
            page.insert_text(pymupdf.Point(cx + 8, cy + 16), lbl, fontsize=8, color=SLATE)
            page.insert_text(pymupdf.Point(cx + 8, cy + 34), val, fontsize=13, color=NAVY)

        y += (2 * (card_h + 8)) + 15

        # Page-wise Results Table
        page.insert_text(pymupdf.Point(40, y + 14), "PAGE-BY-PAGE BREAKDOWN", fontsize=12, color=NAVY)
        y += 24

        table_header = pymupdf.Rect(40, y, 555.3, y + 20)
        page.draw_rect(table_header, color=None, fill=NAVY)
        page.insert_text(pymupdf.Point(45, y + 14), "Page", fontsize=8, color=WHITE)
        page.insert_text(pymupdf.Point(90, y + 14), "Original Words", fontsize=8, color=WHITE)
        page.insert_text(pymupdf.Point(180, y + 14), "Extracted Words", fontsize=8, color=WHITE)
        page.insert_text(pymupdf.Point(280, y + 14), "Accuracy", fontsize=8, color=WHITE)
        page.insert_text(pymupdf.Point(360, y + 14), "Status", fontsize=8, color=WHITE)
        page.insert_text(pymupdf.Point(440, y + 14), "Mismatches", fontsize=8, color=WHITE)
        y += 20

        for p_res in report.pages[:15]:  # fit on first page or multi-page
            row_rect = pymupdf.Rect(40, y, 555.3, y + 18)
            row_fill = (0.97, 0.98, 1.0) if p_res.page % 2 == 0 else WHITE
            page.draw_rect(row_rect, color=(0.9, 0.92, 0.95), fill=row_fill)
            
            p_status_color = (0.06, 0.65, 0.38) if p_res.status == StatusType.PASS else ((0.85, 0.55, 0.05) if p_res.status == StatusType.WARNING else (0.88, 0.22, 0.25))

            page.insert_text(pymupdf.Point(45, y + 13), f"Page {p_res.page}", fontsize=8, color=DARK_TEXT)
            page.insert_text(pymupdf.Point(90, y + 13), str(p_res.orig_word_count), fontsize=8, color=DARK_TEXT)
            page.insert_text(pymupdf.Point(180, y + 13), str(p_res.extracted_word_count), fontsize=8, color=DARK_TEXT)
            page.insert_text(pymupdf.Point(280, y + 13), f"{p_res.accuracy}%", fontsize=8, color=DARK_TEXT)
            page.insert_text(pymupdf.Point(360, y + 13), p_res.status, fontsize=8, color=p_status_color)
            page.insert_text(pymupdf.Point(440, y + 13), str(len(p_res.mismatches)), fontsize=8, color=DARK_TEXT)
            y += 18

        # Detailed Mismatches Section (New Page if needed)
        all_mms = [m for p in report.pages for m in p.mismatches]
        if all_mms:
            page2 = doc.new_page(width=595.3, height=841.9)
            y2 = 40
            page2.insert_text(pymupdf.Point(40, y2 + 16), "DETAILED EXTRACTION MISMATCHES", fontsize=14, color=NAVY)
            y2 += 30

            for m in all_mms[:25]: # Top 25 critical mismatches
                card_rect = pymupdf.Rect(40, y2, 555.3, y2 + 45)
                sev_color = (0.88, 0.22, 0.25) if m.severity == SeverityLevel.HIGH else ((0.85, 0.55, 0.05) if m.severity == SeverityLevel.MEDIUM else SLATE)
                
                page2.draw_rect(card_rect, color=(0.88, 0.90, 0.93), fill=(0.99, 0.99, 1.0))
                # Severity badge
                page2.draw_rect(pymupdf.Rect(45, y2 + 6, 95, y2 + 20), color=None, fill=sev_color)
                page2.insert_text(pymupdf.Point(50, y2 + 16), m.severity, fontsize=7, color=WHITE)
                
                page2.insert_text(pymupdf.Point(105, y2 + 16), f"{m.location} • Type: {m.diff_type}", fontsize=8, color=SLATE)
                
                orig_snippet = (m.orig_text[:65] + '...') if len(m.orig_text) > 65 else (m.orig_text or "(none)")
                ext_snippet = (m.extracted_text[:65] + '...') if len(m.extracted_text) > 65 else (m.extracted_text or "(none)")
                
                page2.insert_text(pymupdf.Point(45, y2 + 32), f"Original:  {orig_snippet}", fontsize=8, color=(0.1, 0.4, 0.2))
                page2.insert_text(pymupdf.Point(45, y2 + 42), f"Extracted: {ext_snippet}", fontsize=8, color=(0.6, 0.1, 0.1))
                y2 += 52

                if y2 > 780:
                    page2 = doc.new_page(width=595.3, height=841.9)
                    y2 = 40

        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes
