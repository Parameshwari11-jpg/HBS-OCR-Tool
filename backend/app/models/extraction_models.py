from typing import List, Optional, Any, Dict, Union
from pydantic import BaseModel, Field

class FontInfo(BaseModel):
    name: Optional[str] = None
    size: Optional[float] = None
    color: Optional[str] = None
    bold: Optional[bool] = False
    italic: Optional[bool] = False
    underline: Optional[bool] = False

class BBox(BaseModel):
    # [x0, y0, x1, y1]
    coords: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])

class ExtractedElement(BaseModel):
    id: str
    type: str # text, image, image_text, table, formula, caption, header, footer, footnote, textbox, shape, drawing, paragraph
    source: str # native, ocr, pp_structure, docx, docx_xml
    text: Optional[str] = None
    page: int = 1
    bbox: Optional[List[float]] = None # [x0, y0, x1, y1]
    confidence: Optional[float] = None
    font: Optional[FontInfo] = None
    block_num: Optional[int] = None
    line_num: Optional[int] = None
    span_num: Optional[int] = None
    reading_order: Optional[int] = None
    
    # Overlap / Duplicate detection
    possible_duplicate: bool = False
    related_native_text_id: Optional[str] = None
    overlap_relationship: Optional[str] = None # overlaps, contains, contained_by, near, etc.
    overlapping_element_ids: List[str] = Field(default_factory=list)
    
    # Table structure
    rows: Optional[List[List[str]]] = None
    headers: Optional[List[str]] = None
    
    # Image metadata
    image_id: Optional[str] = None
    image_path: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

class PageData(BaseModel):
    page: int
    width: float = 612.0
    height: float = 792.0
    elements: List[ExtractedElement] = Field(default_factory=list)
    rendered_image_url: Optional[str] = None

class ExtractionStatistics(BaseModel):
    total_pages: int = 0
    native_text_blocks: int = 0
    ocr_text_blocks: int = 0
    pp_structure_regions: int = 0
    images_count: int = 0
    tables_count: int = 0
    formulas_count: int = 0
    textboxes_count: int = 0
    headers_count: int = 0
    footers_count: int = 0
    footnotes_count: int = 0
    possible_duplicates_count: int = 0

class ExtractionJobStatus(BaseModel):
    job_id: str
    filename: str
    file_type: str # pdf or docx
    status: str # uploaded, processing, completed, failed
    stage: str # uploading, converting, parsing, native_extraction, page_processing, ocr, structure_analysis, layout_analysis, duplicate_detection, finalizing, completed, failed
    progress: int = 0 # 0 - 100
    current_page: Optional[int] = None
    total_pages: Optional[int] = None
    stage_message: Optional[str] = None
    error: Optional[str] = None

class ExtractionResult(BaseModel):
    job_id: str
    filename: str
    file_type: str
    pages: List[PageData] = Field(default_factory=list)
    statistics: ExtractionStatistics = Field(default_factory=ExtractionStatistics)
    reconstructed_text: str = ""
