import React, { useState } from 'react';
import {
  Columns,
  AlignJustify,
  CheckCircle2,
  AlertTriangle,
  Image as ImageIcon,
  Copy,
  Check,
  FileText,
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  Layers,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Sparkles,
  Download,
  Loader2,
} from 'lucide-react';
import { PageOriginalityResult, LineDiffItem } from '../../types/originality';
import { PageData } from '../../types/extraction';
import { OriginalDocumentViewer } from './OriginalDocumentViewer';
import { injectInvisibleText } from '../../api/originalityApi';

export interface DifferenceViewerProps {
  pageResult: PageOriginalityResult;
  pages?: PageOriginalityResult[];
  selectedPageIndex?: number;
  onSelectPage?: (index: number) => void;
  originalFilename?: string;
  jobId?: string;
  reportId?: string;
  initialMode?: 'visual' | 'split' | 'unified';
  extractionPages?: PageData[];
}

export const DifferenceViewer: React.FC<DifferenceViewerProps> = ({
  pageResult,
  pages,
  selectedPageIndex = 0,
  onSelectPage,
  originalFilename,
  jobId,
  reportId,
  initialMode = 'visual',
  extractionPages,
}) => {
  const [viewLayout, setViewLayout] = useState<'visual' | 'split' | 'unified'>(initialMode);
  const [copied, setCopied] = useState<boolean>(false);
  const [expandedDiffs, setExpandedDiffs] = useState<Record<string, boolean>>({});

  // Extracted Text View Controls (Page Mode + Zoom + Interactive Navigation)
  const [textDisplayMode, setTextDisplayMode] = useState<'single' | 'all'>('single');
  const [textZoom, setTextZoom] = useState<number>(1.0);
  const [selectedLineId, setSelectedLineId] = useState<string | null>(null);
  const [selectedLineIndex, setSelectedLineIndex] = useState<number | null>(null);
  const [isInjecting, setIsInjecting] = useState<boolean>(false);
  const [injectSuccess, setInjectSuccess] = useState<boolean>(false);
  const [injectError, setInjectError] = useState<string | null>(null);

  const handleInjectInvisibleText = async () => {
    if (!reportId) return;
    setIsInjecting(true);
    setInjectError(null);
    setInjectSuccess(false);
    try {
      const blob = await injectInvisibleText(reportId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const baseName = (originalFilename || 'document').replace(/\.[^/.]+$/, '');
      a.download = `${baseName}_with_invisible_text.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      setInjectSuccess(true);
      setTimeout(() => setInjectSuccess(false), 4000);
    } catch (err: any) {
      console.error('Failed to inject invisible text:', err);
      setInjectError(err.message || 'Failed to inject invisible text layer.');
      setTimeout(() => setInjectError(null), 5000);
    } finally {
      setIsInjecting(false);
    }
  };

  const allPagesList = pages && pages.length > 0 ? pages : [pageResult];

  const handleTextZoomIn = () => setTextZoom((z) => Math.min(z + 0.25, 3.0));
  const handleTextZoomOut = () => setTextZoom((z) => Math.max(z - 0.25, 0.5));
  const handleTextResetZoom = () => setTextZoom(1.0);

  const handleCopyExtracted = () => {
    let text = '';
    if (textDisplayMode === 'all') {
      text = allPagesList
        .map((p) => `--- Page ${p.page} ---\n` + p.extracted_lines.join('\n'))
        .join('\n\n');
    } else {
      text = pageResult.extracted_lines.join('\n');
    }
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const toggleLineDiff = (key: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setExpandedDiffs((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleLineClick = (pageNumber: number, lineIndex: number, lineKey: string) => {
    setSelectedLineId(lineKey);
    setSelectedLineIndex(lineIndex);
    const targetIdx = allPagesList.findIndex((p) => p.page === pageNumber);
    if (targetIdx !== -1 && onSelectPage) {
      onSelectPage(targetIdx);
    }
  };

  const renderLineDiffs = (lineDiffs: LineDiffItem[], pageNumber: number, pageKeyPrefix: string = '') => {
    if (lineDiffs.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-8 text-slate-500 space-y-2">
          <CheckCircle2 className="w-8 h-8 text-emerald-400 opacity-60" />
          <p className="text-sm font-sans font-medium text-slate-300">
            No differences detected.
          </p>
          <p className="text-xs font-sans text-slate-500">
            Extracted text exactly mirrors the original document.
          </p>
        </div>
      );
    }

    return lineDiffs.map((ld, idx) => {
      const key = `${pageKeyPrefix}_${idx}`;
      const isExpanded = expandedDiffs[key] ?? false;
      const isSelected = selectedLineId === key;

      // 1. EXACT MATCH LINE
      if (ld.tag === 'equal') {
        return (
          <div
            key={key}
            onClick={() => handleLineClick(pageNumber, idx, key)}
            className={`flex items-start space-x-2.5 px-2.5 py-1.5 rounded-lg border transition-all cursor-pointer group ${
              isSelected
                ? 'bg-indigo-950/60 border-indigo-500 text-white shadow-md ring-1 ring-indigo-500/50'
                : 'bg-slate-900/50 border-slate-800/80 hover:border-indigo-500/40 hover:bg-slate-900/80'
            }`}
          >
            <span className="text-[10px] text-slate-500 font-mono w-6 text-right select-none pt-0.5 shrink-0">
              {ld.ext_line_num}
            </span>
            <span className="text-emerald-400/80 pt-0.5 shrink-0">
              <CheckCircle2 className="w-3.5 h-3.5" />
            </span>
            <div className="flex-1 overflow-hidden">
              <p className="font-sans text-xs text-slate-200 whitespace-pre-wrap leading-relaxed break-words">
                {ld.extracted_line}
              </p>
            </div>
            <span className="text-[9px] font-sans font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.2 rounded shrink-0 select-none">
              Match
            </span>
          </div>
        );
      }

      // 2. DISCREPANCY / MODIFIED LINE (CLEAN INLINE DISPLAY + ACCORDION)
      if (ld.tag === 'replace') {
        return (
          <div
            key={key}
            onClick={() => handleLineClick(pageNumber, idx, key)}
            className={`rounded-lg border overflow-hidden transition-all shadow-sm cursor-pointer ${
              isSelected
                ? 'bg-amber-950/30 border-amber-400 ring-1 ring-amber-400/50 shadow-md'
                : 'border-amber-500/30 bg-amber-950/15 hover:border-amber-500/60'
            }`}
          >
            <div
              onClick={(e) => toggleLineDiff(key, e)}
              className="flex items-start space-x-2.5 px-2.5 py-1.5 hover:bg-amber-500/10 transition select-text"
            >
              <span className="text-[10px] text-amber-500/80 font-mono w-6 text-right select-none pt-0.5 shrink-0 font-bold">
                {ld.ext_line_num}
              </span>
              <span className="text-amber-400 pt-0.5 shrink-0">
                <AlertTriangle className="w-3.5 h-3.5" />
              </span>
              <div className="flex-1 overflow-hidden">
                <p className="font-sans text-xs text-amber-100 whitespace-pre-wrap leading-relaxed break-words font-medium">
                  {ld.extracted_line}
                </p>
              </div>

              <div className="flex items-center space-x-1 shrink-0 select-none pt-0.5">
                <span className="text-[9px] font-sans font-semibold text-amber-300 bg-amber-500/20 border border-amber-500/30 px-1.5 py-0.2 rounded">
                  Diff
                </span>
                <button
                  type="button"
                  onClick={(e) => toggleLineDiff(key, e)}
                  className="p-0.5 text-amber-400 hover:text-white rounded cursor-pointer"
                  title={isExpanded ? 'Hide comparison' : 'Show original comparison'}
                >
                  {isExpanded ? (
                    <ChevronUp className="w-3 h-3" />
                  ) : (
                    <ChevronDown className="w-3 h-3" />
                  )}
                </button>
              </div>
            </div>

            {isExpanded && (
              <div className="px-3 py-2 bg-slate-950/90 border-t border-amber-500/20 space-y-1.5 text-[11px] animate-fadeIn">
                <div className="flex items-start space-x-2 font-mono">
                  <span className="text-[10px] text-blue-400 font-bold uppercase shrink-0 pt-0.5">
                    Original:
                  </span>
                  <span className="text-slate-300 break-words flex-1 bg-slate-900 px-2 py-1 rounded border border-slate-800">
                    {ld.orig_line}
                  </span>
                </div>
                <div className="flex items-start space-x-2 font-mono">
                  <span className="text-[10px] text-amber-400 font-bold uppercase shrink-0 pt-0.5">
                    Extracted:
                  </span>
                  <span className="text-amber-200 break-words flex-1 bg-amber-950/40 px-2 py-1 rounded border border-amber-900/40">
                    {ld.extracted_line}
                  </span>
                </div>
              </div>
            )}
          </div>
        );
      }

      // 3. EXTRA EXTRACTED TEXT LINE
      if (ld.tag === 'insert') {
        return (
          <div
            key={key}
            onClick={() => handleLineClick(pageNumber, idx, key)}
            className={`flex items-start space-x-2.5 px-2.5 py-1.5 rounded-lg border transition-all cursor-pointer ${
              isSelected
                ? 'bg-emerald-950/50 border-emerald-400 ring-1 ring-emerald-400/50 text-emerald-100 shadow-md'
                : 'bg-emerald-950/20 border-emerald-500/30 text-emerald-200 hover:border-emerald-500/60'
            }`}
          >
            <span className="text-[10px] text-emerald-500 font-mono w-6 text-right select-none pt-0.5 shrink-0">
              {ld.ext_line_num}
            </span>
            <span className="text-emerald-400 font-bold font-mono text-xs shrink-0 select-none pt-0.5">
              +
            </span>
            <div className="flex-1 overflow-hidden">
              <p className="font-sans text-xs whitespace-pre-wrap leading-relaxed break-words">
                {ld.extracted_line}
              </p>
            </div>
            <span className="text-[9px] font-sans font-medium text-emerald-400 bg-emerald-500/20 border border-emerald-500/30 px-1.5 py-0.2 rounded shrink-0 select-none">
              Extra Text
            </span>
          </div>
        );
      }

      // 4. OMITTED LINE IN ORIGINAL DOCUMENT
      if (ld.tag === 'delete') {
        return (
          <div
            key={key}
            onClick={() => handleLineClick(pageNumber, idx, key)}
            className={`flex items-start space-x-2.5 px-2.5 py-1 rounded border transition-all cursor-pointer opacity-90 ${
              isSelected
                ? 'bg-rose-950/50 border-rose-400 ring-1 ring-rose-400/50 text-rose-100'
                : 'bg-rose-950/20 border-rose-500/30 text-rose-300 hover:border-rose-500/60'
            }`}
          >
            <span className="text-[10px] text-rose-500 font-mono w-6 text-right select-none pt-0.5 shrink-0">
              -
            </span>
            <div className="flex-1 overflow-hidden">
              <p className="font-sans text-[11px] whitespace-pre-wrap leading-relaxed line-through opacity-80 break-words">
                {ld.orig_line}
              </p>
            </div>
            <span className="text-[9px] font-sans font-medium text-rose-400 bg-rose-500/20 border border-rose-500/30 px-1.5 py-0.2 rounded shrink-0 select-none">
              Omitted from Original
            </span>
          </div>
        );
      }

      return null;
    });
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col h-[750px]">
      {/* Top Header: Verification Status & Layout Controls */}
      <div className="bg-slate-950 border-b border-slate-800 px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold text-white">
              Page {pageResult.page} Verification
            </span>
            <span
              className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded border ${
                pageResult.accuracy >= 99
                  ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                  : pageResult.accuracy >= 95
                  ? 'text-amber-400 bg-amber-500/10 border-amber-500/20'
                  : 'text-rose-400 bg-rose-500/10 border-rose-500/20'
              }`}
            >
              {pageResult.accuracy}% Match
            </span>
          </div>

          <span className="hidden sm:inline-block text-[10px] text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full font-medium">
            {pageResult.verification_type === 'OCR_BASED' ? 'Visual / Scanned Document' : 'Native Document'}
          </span>
        </div>

        {/* Top Right Controls: Inject Button & View Layout Switcher */}
        <div className="flex items-center space-x-2.5">
          {reportId && (
            <button
              type="button"
              onClick={handleInjectInvisibleText}
              disabled={isInjecting}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center space-x-1.5 transition cursor-pointer shadow-md border ${
                injectSuccess
                  ? 'bg-emerald-600 text-white border-emerald-500 shadow-emerald-950/40'
                  : 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white border-purple-400/40 shadow-purple-950/40 hover:-translate-y-0.5 active:translate-y-0'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
              title="Inject extracted text as an invisible search/copy text layer behind all images in the PDF"
            >
              {isInjecting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 text-white animate-spin" />
                  <span>Injecting...</span>
                </>
              ) : injectSuccess ? (
                <>
                  <Check className="w-3.5 h-3.5 text-white" />
                  <span>Injected &amp; Downloaded!</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                  <span>Inject Invisible Layer</span>
                </>
              )}
            </button>
          )}

          {/* View Layout Switcher */}
          <div className="flex items-center space-x-1 bg-slate-900 border border-slate-800 p-0.5 rounded-lg text-xs">
            <button
              type="button"
              onClick={() => setViewLayout('visual')}
              className={`px-3 py-1.5 rounded font-medium transition cursor-pointer flex items-center space-x-1.5 ${
                viewLayout === 'visual'
                  ? 'bg-indigo-600 text-white shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Inspect full original document side-by-side with clean extracted text"
            >
              <ImageIcon className="w-3.5 h-3.5 text-blue-400" />
              <span>Document &amp; Text</span>
            </button>
            <button
              type="button"
              onClick={() => setViewLayout('split')}
              className={`px-3 py-1.5 rounded font-medium transition cursor-pointer flex items-center space-x-1.5 ${
                viewLayout === 'split'
                  ? 'bg-indigo-600 text-white shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Side-by-side original ground truth text vs extracted text"
            >
              <Columns className="w-3.5 h-3.5" />
              <span>Text Side-by-Side</span>
            </button>
            <button
              type="button"
              onClick={() => setViewLayout('unified')}
              className={`px-3 py-1.5 rounded font-medium transition cursor-pointer flex items-center space-x-1.5 ${
                viewLayout === 'unified'
                  ? 'bg-indigo-600 text-white shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Unified line-by-line diff view"
            >
              <AlignJustify className="w-3.5 h-3.5" />
              <span>Unified Diff</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Diff Content Container */}
      <div className="flex-1 overflow-hidden p-4 bg-slate-950 font-sans text-xs">
        {/* VIEW 1: ORIGINAL DOCUMENT FULL PAGES (LEFT) + CLEAN EXTRACTED TEXT (RIGHT) */}
        {viewLayout === 'visual' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-full">
            {/* Left: Original Document Viewer with Full Pages & Navigation */}
            <div className="h-full overflow-hidden flex flex-col">
              <OriginalDocumentViewer
                pages={allPagesList}
                selectedPageIndex={selectedPageIndex}
                onSelectPage={onSelectPage || (() => {})}
                originalFilename={originalFilename}
                jobId={jobId}
                selectedLineIndex={selectedLineIndex}
                extractionPages={extractionPages}
              />
            </div>

            {/* Right: Extracted Text Content (Clean, Sequential, Accurate Display) */}
            <div className="h-full bg-slate-900 border border-slate-800 rounded-xl flex flex-col overflow-hidden shadow-inner">
              {/* Header with Title, Page Selector, Zoom, and Copy */}
              <div className="bg-slate-950/90 border-b border-slate-800 px-3 py-2 flex flex-wrap items-center justify-between gap-2 shrink-0">
                <div className="flex items-center space-x-2">
                  <span className="p-1 rounded bg-indigo-500/10 text-indigo-400">
                    <FileText className="w-3.5 h-3.5" />
                  </span>
                  <span className="text-xs font-bold text-white">Extracted Text Content</span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    ({textDisplayMode === 'all'
                      ? `${allPagesList.reduce((a, p) => a + p.extracted_word_count, 0)} words • ${allPagesList.reduce((a, p) => a + p.extracted_lines.length, 0)} lines`
                      : `${pageResult.extracted_word_count} words • ${pageResult.extracted_lines.length} lines`
                    })
                  </span>

                  {/* Page Selector & Prev/Next Buttons (< Page X of N >) */}
                  <div className="flex items-center space-x-1 bg-slate-950 border border-slate-800 rounded-lg p-0.5 ml-1">
                    <button
                      type="button"
                      onClick={() => onSelectPage && selectedPageIndex > 0 && onSelectPage(selectedPageIndex - 1)}
                      disabled={selectedPageIndex <= 0}
                      className="p-1 text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:hover:bg-transparent rounded transition cursor-pointer"
                      title="Previous Page"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" />
                    </button>

                    <select
                      value={selectedPageIndex}
                      onChange={(e) => onSelectPage && onSelectPage(Number(e.target.value))}
                      className="bg-transparent text-xs font-bold text-indigo-400 px-1 py-0.5 outline-none cursor-pointer"
                      title="Select Page"
                    >
                      {allPagesList.map((p, idx) => (
                        <option key={p.page} value={idx} className="bg-slate-900 text-white">
                          Page {p.page} of {allPagesList.length}
                        </option>
                      ))}
                    </select>

                    <button
                      type="button"
                      onClick={() => onSelectPage && selectedPageIndex < allPagesList.length - 1 && onSelectPage(selectedPageIndex + 1)}
                      disabled={selectedPageIndex >= allPagesList.length - 1}
                      className="p-1 text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:hover:bg-transparent rounded transition cursor-pointer"
                      title="Next Page"
                    >
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                <div className="flex items-center space-x-1.5 flex-wrap gap-y-1">

                  {/* View Mode Toggle: Page X vs All Pages */}
                  <div className="flex items-center space-x-0.5 bg-slate-950 border border-slate-800 rounded-lg p-0.5 text-xs">
                    <button
                      type="button"
                      onClick={() => setTextDisplayMode('single')}
                      className={`px-2 py-1 rounded font-medium transition cursor-pointer flex items-center space-x-1 text-[11px] ${
                        textDisplayMode === 'single'
                          ? 'bg-indigo-600 text-white shadow-sm'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                      title="Show text for selected page"
                    >
                      <FileText className="w-3 h-3" />
                      <span>Page {pageResult.page}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setTextDisplayMode('all')}
                      className={`px-2 py-1 rounded font-medium transition cursor-pointer flex items-center space-x-1 text-[11px] ${
                        textDisplayMode === 'all'
                          ? 'bg-indigo-600 text-white shadow-sm'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                      title={`Show text for all ${allPagesList.length} pages`}
                    >
                      <Layers className="w-3 h-3" />
                      <span>All Pages ({allPagesList.length})</span>
                    </button>
                  </div>

                  {/* Zoom Controls */}
                  <div className="flex items-center space-x-1 bg-slate-950 border border-slate-800 rounded-lg p-0.5">
                    <button
                      type="button"
                      onClick={handleTextZoomOut}
                      className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition cursor-pointer"
                      title="Zoom Out"
                    >
                      <ZoomOut className="w-3.5 h-3.5" />
                    </button>
                    <span className="text-[11px] font-mono font-bold text-indigo-300 w-10 text-center select-none">
                      {Math.round(textZoom * 100)}%
                    </span>
                    <button
                      type="button"
                      onClick={handleTextZoomIn}
                      className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition cursor-pointer"
                      title="Zoom In"
                    >
                      <ZoomIn className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={handleTextResetZoom}
                      className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition cursor-pointer border-l border-slate-800"
                      title="Reset Zoom"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Copy Button */}
                  <button
                    type="button"
                    onClick={handleCopyExtracted}
                    className="px-2 py-1 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-[10px] font-medium flex items-center space-x-1 transition cursor-pointer"
                    title="Copy extracted text to clipboard"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-400" />
                        <span className="text-emerald-400 font-semibold">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Clean Extracted Text Stream with Zoom & Page Mode */}
              <div
                className="flex-1 overflow-auto p-3 space-y-1.5 bg-slate-950/70 font-mono text-xs select-text"
                style={{ fontSize: `${0.75 * textZoom}rem` }}
              >
                {textDisplayMode === 'all' ? (
                  allPagesList.map((p) => (
                    <div key={p.page} className="space-y-1.5 mb-4">
                      <div className="sticky top-0 z-10 text-[11px] font-bold text-indigo-300 bg-slate-900/95 border border-indigo-500/30 px-3 py-1.5 rounded-lg my-2 font-mono flex items-center justify-between shadow-md backdrop-blur select-none">
                        <div className="flex items-center space-x-2">
                          <span className="w-2 h-2 rounded-full bg-indigo-400" />
                          <span>Page {p.page} Extracted Text</span>
                        </div>
                        <span className="text-[10px] text-slate-400 font-normal">
                          {p.extracted_word_count} words &bull; {p.accuracy}% match
                        </span>
                      </div>
                      {renderLineDiffs(p.line_diffs, p.page, `p${p.page}`)}
                    </div>
                  ))
                ) : (
                  renderLineDiffs(pageResult.line_diffs, pageResult.page, `p${pageResult.page}`)
                )}
              </div>
            </div>
          </div>
        )}

        {/* VIEW 2: TEXT SIDE-BY-SIDE */}
        {viewLayout === 'split' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-full">
            {/* Left: Original Ground Truth Text */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-3 overflow-auto flex flex-col">
              <div className="pb-2 mb-2 border-b border-slate-800 flex items-center justify-between text-xs font-bold text-blue-400 shrink-0">
                <span className="flex items-center space-x-1.5">
                  <FileText className="w-3.5 h-3.5" />
                  <span>Original Document Ground Truth (Page {pageResult.page})</span>
                </span>
                <span className="text-[10px] text-slate-500 font-normal font-mono">
                  {pageResult.orig_word_count} words &bull; {pageResult.orig_lines.length} lines
                </span>
              </div>
              <div className="space-y-1.5 flex-1 overflow-auto font-mono text-xs">
                {pageResult.line_diffs.map((ld, idx) => {
                  if (ld.tag === 'insert') {
                    return (
                      <div
                        key={idx}
                        className="py-1 px-2 text-slate-700 italic select-none text-[11px]"
                      >
                        (no corresponding line)
                      </div>
                    );
                  }
                  const isDiff = ld.tag !== 'equal';
                  return (
                    <div
                      key={idx}
                      className={`flex items-start space-x-2 py-1 px-2 rounded font-sans text-xs leading-relaxed ${
                        isDiff
                          ? 'bg-rose-950/40 text-rose-200 border border-rose-900/60'
                          : 'text-slate-300 hover:bg-slate-800/40'
                      }`}
                    >
                      <span className="text-[10px] text-slate-500 font-mono select-none w-5 text-right">
                        {ld.orig_line_num}
                      </span>
                      <span className="flex-1 whitespace-pre-wrap break-words">{ld.orig_line}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right: Extracted Text */}
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-3 overflow-auto flex flex-col">
              <div className="pb-2 mb-2 border-b border-slate-800 flex items-center justify-between text-xs font-bold text-indigo-400 shrink-0">
                <span className="flex items-center space-x-1.5">
                  <FileText className="w-3.5 h-3.5" />
                  <span>Extracted Text</span>
                </span>
                <span className="text-[10px] text-slate-500 font-normal font-mono">
                  {pageResult.extracted_word_count} words &bull; {pageResult.extracted_lines.length} lines
                </span>
              </div>
              <div className="space-y-1.5 flex-1 overflow-auto font-mono text-xs">
                {pageResult.line_diffs.map((ld, idx) => {
                  if (ld.tag === 'delete') {
                    return (
                      <div
                        key={idx}
                        className="py-1 px-2 text-slate-700 italic select-none text-[11px]"
                      >
                        (line omitted in extraction)
                      </div>
                    );
                  }
                  const isDiff = ld.tag !== 'equal';
                  return (
                    <div
                      key={idx}
                      className={`flex items-start space-x-2 py-1 px-2 rounded font-sans text-xs leading-relaxed ${
                        isDiff
                          ? 'bg-amber-950/40 text-amber-200 border border-amber-900/60'
                          : 'text-slate-300 hover:bg-slate-800/40'
                      }`}
                    >
                      <span className="text-[10px] text-slate-500 font-mono select-none w-5 text-right">
                        {ld.ext_line_num}
                      </span>
                      <span className="flex-1 whitespace-pre-wrap break-words">{ld.extracted_line}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* VIEW 3: UNIFIED DIFF */}
        {viewLayout === 'unified' && (
          <div className="h-full overflow-auto space-y-1 font-mono text-xs select-text">
            {pageResult.line_diffs.map((ld, idx) => {
              if (ld.tag === 'equal') {
                return (
                  <div
                    key={idx}
                    className="flex items-start space-x-3 px-3 py-1.5 rounded hover:bg-slate-900/60 text-slate-300 transition"
                  >
                    <span className="w-8 text-right text-[10px] text-slate-600 select-none">
                      {ld.orig_line_num}
                    </span>
                    <span className="w-4 text-center text-slate-600 select-none"> </span>
                    <span className="flex-1 font-sans text-xs whitespace-pre-wrap leading-relaxed break-words">
                      {ld.orig_line}
                    </span>
                  </div>
                );
              }

              if (ld.tag === 'delete') {
                return (
                  <div
                    key={idx}
                    className="flex items-start space-x-3 px-3 py-1.5 rounded bg-rose-950/40 border border-rose-900/50 text-rose-200 transition"
                  >
                    <span className="w-8 text-right text-[10px] text-rose-500/70 select-none">
                      {ld.orig_line_num}
                    </span>
                    <span className="w-4 text-center font-bold text-rose-400 select-none">-</span>
                    <div className="flex-1">
                      <span className="font-sans text-xs whitespace-pre-wrap leading-relaxed break-words">
                        {ld.orig_line}
                      </span>
                      <span className="ml-2 text-[10px] font-sans text-rose-400 bg-rose-500/20 px-1.5 py-0.2 rounded border border-rose-500/30">
                        Missing in extraction
                      </span>
                    </div>
                  </div>
                );
              }

              if (ld.tag === 'insert') {
                return (
                  <div
                    key={idx}
                    className="flex items-start space-x-3 px-3 py-1.5 rounded bg-emerald-950/40 border border-emerald-900/50 text-emerald-200 transition"
                  >
                    <span className="w-8 text-right text-[10px] text-emerald-500/70 select-none">
                      {ld.ext_line_num}
                    </span>
                    <span className="w-4 text-center font-bold text-emerald-400 select-none">+</span>
                    <div className="flex-1">
                      <span className="font-sans text-xs whitespace-pre-wrap leading-relaxed break-words">
                        {ld.extracted_line}
                      </span>
                      <span className="ml-2 text-[10px] font-sans text-emerald-400 bg-emerald-500/20 px-1.5 py-0.2 rounded border border-emerald-500/30">
                        Extra extracted text
                      </span>
                    </div>
                  </div>
                );
              }

              // Replace / Changed Line
              return (
                <div
                  key={idx}
                  className="space-y-1 p-2 rounded-xl bg-slate-900/90 border border-amber-500/30 shadow-inner"
                >
                  <div className="flex items-start space-x-3 px-2 py-1 rounded bg-rose-950/30 text-rose-200">
                    <span className="w-8 text-right text-[10px] text-rose-400/60 select-none">
                      {ld.orig_line_num}
                    </span>
                    <span className="w-4 text-center font-bold text-rose-400 select-none">-</span>
                    <div className="flex-1">
                      <span className="font-sans text-xs whitespace-pre-wrap leading-relaxed break-words">
                        {ld.orig_line}
                      </span>
                      <span className="ml-2 text-[9px] font-sans text-rose-300 bg-rose-900/60 px-1.5 py-0.5 rounded">
                        Original
                      </span>
                    </div>
                  </div>

                  <div className="flex items-start space-x-3 px-2 py-1 rounded bg-amber-950/30 text-amber-200">
                    <span className="w-8 text-right text-[10px] text-amber-400/60 select-none">
                      {ld.ext_line_num}
                    </span>
                    <span className="w-4 text-center font-bold text-amber-400 select-none">~</span>
                    <div className="flex-1">
                      <span className="font-sans text-xs whitespace-pre-wrap leading-relaxed break-words">
                        {ld.extracted_line}
                      </span>
                      <span className="ml-2 text-[9px] font-sans text-amber-300 bg-amber-900/60 px-1.5 py-0.5 rounded">
                        Extracted
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
