# Universal Document Text Extractor

An advanced, production-ready web application for extracting native text, OCR text, document layout, images, tables, headers, footers, floating objects, and layered/overlapping content from **PDF** and **Microsoft Word (.docx)** files.

> **IMPORTANT**: This system completely replaces Tesseract / pytesseract with **PaddleOCR** and **PP-StructureV3** for superior OCR performance, document parsing, layout recognition, and table extraction.

---

## 🌟 Key Features

- 📄 **Multi-Format Parsing**: Extracts text, images, and structures from both PDF and DOCX files.
- 🤖 **PaddleOCR & PP-StructureV3 Integration**: High-accuracy text detection inside images, scanned pages, tables, math formulas, and complex page layouts.
- 📐 **Layered & Overlapping Content Detection**: Handles text inside images, text over images, text under images, and multi-layered PDF objects without deleting overlapping text.
- 🔍 **Dynamic Duplicate Detection**: Compares native text and OCR text using spatial IoU and normalized string metrics to flag duplicate text while preserving raw data provenance.
- 📑 **Logical Reading Order Engine**: Sorts multi-column and single-column text objects dynamically top-to-bottom and left-to-right.
- 📦 **DOCX Deep XML Inspection**: Parses underlying WordprocessingML XML (`w:txbxContent`, `w:drawing`, `v:shape`, `w:footnote`, `w:hdr`, `w:ftr`) to capture text inside floating text boxes, shapes, anchored objects, and footnotes.
- 👁️ **Interactive Page Viewer & Bounding Box Overlay**: Interactive canvas displaying high-DPI rendered page previews with color-coded, toggleable bounding boxes (Blue = Native Text, Emerald = OCR Text, Purple = Images, Amber = Tables, Rose = Formulas) and cross-highlighting.
- 📊 **6 Results Tabs**: All Text (reconstructed reading order), Native Text, OCR Text, Images, Tables, and Document Structure Tree.
- 🧮 **MathType & Mathematical Formula Support**: Extracts MathType equations (WMF/EMF/PNG), OMML equations (`<m:oMath>`), vector formulas, and mathematical notation from both Word documents and PDF files.
- 🎨 **100% Original Page Layout Preservation**: Renders exact original pages for both PDF and Word (`.docx`) files without losing fonts, margins, photos, diagrams, or equation layouts.
- 💾 **Instant TXT & JSON Export**: One-click downloads for reconstructed reading-order text and complete JSON extraction structure.

---

## 🏗️ System Architecture

```text
Universal Document Text Extractor
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI server entrypoint & CORS
│   │   ├── api/
│   │   │   ├── upload.py            # POST /api/upload
│   │   │   ├── extract.py           # POST /api/extract
│   │   │   ├── results.py           # GET /api/status, /api/results, /api/preview
│   │   │   └── export.py            # GET /api/export/{job_id}/txt & /json
│   │   ├── extractors/
│   │   │   ├── pdf_extractor.py     # PyMuPDF native text & image object parser
│   │   │   ├── docx_extractor.py    # python-docx paragraphs, runs, tables, images
│   │   │   ├── xml_extractor.py     # DOCX XML text boxes, shapes, footnotes
│   │   │   └── image_extractor.py   # OCR image processing helper
│   │   ├── ocr/
│   │   │   ├── paddle_ocr_engine.py # PaddleOCR wrapper with error handling
│   │   │   ├── pp_structure_engine.py # PP-StructureV3 table & region parser
│   │   │   └── preprocessing.py     # OpenCV image thresholding & denoise
│   │   ├── layout/
│   │   │   ├── overlap_detector.py  # Spatial bounding box IoU & relationship classifier
│   │   │   ├── duplicate_detector.py# Normalized string similarity & duplicate tagger
│   │   │   └── reading_order.py     # Dynamic top-to-bottom, left-to-right page sorter
│   │   ├── models/
│   │   │   └── extraction_models.py # Pydantic schemas for elements, pages, statistics
│   │   ├── services/
│   │   │   ├── extraction_service.py# Async pipeline orchestration & progress updates
│   │   │   └── job_service.py       # In-memory job state store
│   │   └── utils/
│   │       ├── bbox.py              # Bounding box IoU & containment math
│   │       ├── normalization.py     # Text normalization & string similarity
│   │       └── file_utils.py        # File validation & temp workspace management
│   └── requirements.txt
│
├── frontend/                        # React + TypeScript + Vite + Tailwind CSS
│   ├── src/
│   │   ├── api/
│   │   │   └── extractionApi.ts     # Client HTTP service layer
│   │   ├── components/
│   │   │   ├── Header.tsx           # Application header
│   │   │   ├── UploadArea.tsx       # Drag-and-drop file uploader
│   │   │   ├── ExtractionProgress.tsx # Real-time progress bar & stage status
│   │   │   ├── Statistics.tsx       # Extraction metrics dashboard
│   │   │   ├── PageViewer.tsx       # Interactive document viewer with SVG overlays
│   │   │   ├── ResultsTabs.tsx      # 6 results tabs with cross-highlighting
│   │   │   └── ExportButtons.tsx    # TXT & JSON export buttons
│   │   ├── types/
│   │   │   └── extraction.ts        # TypeScript data interfaces
│   │   ├── pages/
│   │   │   └── Home.tsx             # Main application container
│   │   ├── main.tsx
│   │   └── index.css                # Tailwind CSS v4 styling
│   ├── package.json
│   └── vite.config.ts               # Proxy configuration for /api
│
└── tests/                           # Unit test suite
```

---

## ⚡ Prerequisites

- **Python**: 3.11 or 3.12
- **Node.js**: v18+ and npm
- **C++ Build Tools / OpenCV Dependencies** (standard on Windows/Linux)

---

## 📦 Installation & Setup

### 1. Backend Setup

```bash
# Navigate to workspace
cd c:\Users\HBS\Desktop\OCR

# Activate existing venv or create a new one
.\venv\Scripts\activate

# Install Python requirements (including PaddlePaddle and PaddleOCR)
pip install -r backend/requirements.txt
```

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install npm dependencies
npm install
```

---

## 🚀 Running the Application

### ⚡ Option 1: Single Unified Command (Recommended)

You can launch both the **FastAPI Backend** and the **Vite Frontend** together using any of these single commands from the project root:

```bash
# Using batch file (or double-click run.bat in Windows Explorer):
run.bat

# OR using Python directly:
python run.py

# OR using npm:
npm start
```
This automatically starts:
- **Backend**: `http://127.0.0.1:8000`
- **Frontend**: `http://localhost:3000`
- Automatically opens `http://localhost:3000` in your default browser.
- Press **Ctrl+C** in the terminal to stop both servers cleanly.

---

### 🖥️ Option 2: Running Separately

If you prefer separate terminal windows:

1. **Start Backend**:
   ```bash
   run_backend.bat
   ```
2. **Start Frontend**:
   ```bash
   run_frontend.bat
   ```

---

## 📡 Backend API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/upload` | Upload `.pdf` or `.docx` document and receive a `job_id`. |
| `POST` | `/api/extract` | Initiate document extraction pipeline for a given `job_id`. |
| `GET` | `/api/status/{job_id}` | Retrieve real-time extraction progress (`progress %` and `stage`). |
| `GET` | `/api/results/{job_id}` | Fetch structured extraction result with pages, elements, and stats. |
| `GET` | `/api/preview/{job_id}/{page_num}` | Serve high-DPI rendered page PNG preview image. |
| `GET` | `/api/export/{job_id}/txt` | Download reconstructed reading-order text as a `.txt` file. |
| `GET` | `/api/export/{job_id}/json` | Download full document extraction tree as a `.json` file. |

---

## 🧪 Testing

Run unit tests for PDF extraction, DOCX parsing, overlap detection, and duplicate classification:

```bash
.\venv\Scripts\python -m unittest discover -s tests
```

---

## 📄 License

MIT License.
