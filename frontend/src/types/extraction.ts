export interface FontInfo {
  name?: string;
  size?: number;
  color?: string;
  bold?: boolean;
  italic?: boolean;
  underline?: boolean;
}

export interface ExtractedElement {
  id: string;
  type: 'text' | 'image' | 'image_text' | 'table' | 'formula' | 'caption' | 'header' | 'footer' | 'footnote' | 'textbox' | 'shape' | 'drawing' | 'paragraph';
  source: 'native' | 'ocr' | 'pp_structure' | 'docx' | 'docx_xml';
  text?: string;
  page: number;
  bbox?: [number, number, number, number]; // [x0, y0, x1, y1]
  confidence?: number;
  font?: FontInfo;
  block_num?: number;
  line_num?: number;
  span_num?: number;
  reading_order?: number;
  possible_duplicate?: boolean;
  related_native_text_id?: string;
  overlap_relationship?: string;
  overlapping_element_ids?: string[];
  rows?: string[][];
  headers?: string[];
  image_id?: string;
  image_path?: string;
  width?: number;
  height?: number;
}

export interface PageData {
  page: number;
  width: number;
  height: number;
  elements: ExtractedElement[];
  rendered_image_url?: string;
}

export interface ExtractionStatistics {
  total_pages: number;
  native_text_blocks: number;
  ocr_text_blocks: number;
  pp_structure_regions: number;
  images_count: number;
  tables_count: number;
  formulas_count: number;
  textboxes_count: number;
  headers_count: number;
  footers_count: number;
  footnotes_count: number;
  possible_duplicates_count: number;
}

export interface ExtractionJobStatus {
  job_id: string;
  filename: string;
  file_type: 'pdf' | 'docx';
  status: 'uploading' | 'processing' | 'completed' | 'failed';
  stage: string;
  progress: number;
  current_page?: number;
  total_pages?: number;
  stage_message?: string;
  error?: string;
}

export interface ExtractionResult {
  job_id: string;
  filename: string;
  file_type: 'pdf' | 'docx';
  pages: PageData[];
  statistics: ExtractionStatistics;
  reconstructed_text: string;
}
