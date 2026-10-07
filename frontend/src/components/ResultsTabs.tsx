import React, { useState, useRef, useEffect, useMemo } from 'react';
import { ExtractionResult, ExtractedElement, PageData } from '../types/extraction';
import {
  FileText,
  ScanText,
  Image,
  Table,
  GitFork,
  AlignLeft,
  Copy,
  Check,
  Info,
  Link2,
  FileCode,
  ChevronLeft,
  ChevronRight,
  Layers,
} from 'lucide-react';

interface ResultsTabsProps {
  result: ExtractionResult;
  selectedElementId: string | null;
  onSelectElement: (element: ExtractedElement | null) => void;
  currentPageIndex?: number;
  onPageChange?: (index: number) => void;
  isSyncScroll?: boolean;
  onToggleSyncScroll?: () => void;
  onScrollContainerScroll?: () => void;
  containerRefExternal?: React.RefObject<HTMLDivElement | null>;
  pageRefsExternal?: React.MutableRefObject<(HTMLDivElement | null)[]>;
}

interface PageSection {
  pageNumber: number;
  text: string;
}

export const ResultsTabs: React.FC<ResultsTabsProps> = ({
  result,
  selectedElementId,
  onSelectElement,
  currentPageIndex = 0,
  onPageChange,
  isSyncScroll = true,
  onToggleSyncScroll,
  onScrollContainerScroll,
  containerRefExternal,
  pageRefsExternal,
}) => {
  const [activeTab, setActiveTab] = useState<'all' | 'native' | 'ocr' | 'images' | 'tables' | 'structure'>('all');
  const [allTextViewMode, setAllTextViewMode] = useState<'cards' | 'plain'>('plain');
  const [copiedAll, setCopiedAll] = useState(false);
  const [copiedPage, setCopiedPage] = useState<number | null>(null);

  // Automatically default to Plain Text whenever a new extraction result is loaded
  useEffect(() => {
    setAllTextViewMode('plain');
  }, [result.job_id]);

  const localContainerRef = useRef<HTMLDivElement>(null);
  const containerRef = containerRefExternal || localContainerRef;

  const localPageRefs = useRef<(HTMLDivElement | null)[]>([]);
  const pageRefs = pageRefsExternal || localPageRefs;

  // Flatten elements across all pages
  const allElements: ExtractedElement[] = result.pages.flatMap((p) => p.elements);

  const nativeElements = allElements.filter((e) => e.source === 'native' || e.source === 'docx');
  const ocrElements = allElements.filter((e) => e.source === 'ocr' || e.source === 'pp_structure');
  const imageElements = allElements.filter((e) => e.type === 'image' || (e.type === 'formula' && Boolean(e.image_path)));
  const tableElements = allElements.filter((e) => e.type === 'table');

  // Parse reconstructed_text into per-page sections matching result.pages
  const pageSections = useMemo((): PageSection[] => {
    const getFallbackText = (p: PageData) => {
      return p.elements
        .filter((e) => !e.possible_duplicate && e.type !== 'image' && e.text && e.text.trim())
        .map((e) => e.text!.trim())
        .join('\n\n');
    };

    if (!result.reconstructed_text) {
      return result.pages.map((p) => ({
        pageNumber: p.page,
        text: getFallbackText(p),
      }));
    }

    const regex = /--- Page (\d+) ---([\s\S]*?)(?=(?:--- Page \d+ ---|$))/g;
    const sectionsMap = new Map<number, string>();
    let match;
    while ((match = regex.exec(result.reconstructed_text)) !== null) {
      const pNum = parseInt(match[1], 10);
      sectionsMap.set(pNum, match[2].trim());
    }

    if (sectionsMap.size > 0) {
      return result.pages.map((p) => ({
        pageNumber: p.page,
        text: sectionsMap.get(p.page) || getFallbackText(p),
      }));
    }

    // Fallback if no page delimiters present
    return result.pages.map((p, idx) => ({
      pageNumber: p.page,
      text: idx === 0 ? result.reconstructed_text.trim() : getFallbackText(p),
    }));
  }, [result.reconstructed_text, result.pages]);

  // Sorted reading-order elements for each page (used for interactive text navigation)
  const pageReadingOrderElements = useMemo(() => {
    return result.pages.map((p) => {
      let valid = p.elements.filter(
        (e) => !e.possible_duplicate && e.type !== 'image' && e.text && e.text.trim()
      );
      if (valid.length === 0) {
        valid = p.elements.filter(
          (e) => e.type !== 'image' && e.text && e.text.trim()
        );
      }
      return valid.sort((a, b) => {
        const roA = a.reading_order && a.reading_order > 0 ? a.reading_order : 99999;
        const roB = b.reading_order && b.reading_order > 0 ? b.reading_order : 99999;
        if (roA !== roB) return roA - roB;
        const yA = a.bbox ? a.bbox[1] : 99999;
        const yB = b.bbox ? b.bbox[1] : 99999;
        if (yA !== yB) return yA - yB;
        const xA = a.bbox ? a.bbox[0] : 99999;
        const xB = b.bbox ? b.bbox[0] : 99999;
        return xA - xB;
      });
    });
  }, [result.pages]);

  // When active tab changes, auto-align to current page
  useEffect(() => {
    if (currentPageIndex !== undefined && pageRefs.current[currentPageIndex]) {
      pageRefs.current[currentPageIndex]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [activeTab]);

  // Scroll element card into view in Tab 1 when selected from document viewer
  useEffect(() => {
    if (selectedElementId && activeTab === 'all' && allTextViewMode === 'cards') {
      const cardEl = document.getElementById(`elem-card-${selectedElementId}`);
      if (cardEl) {
        cardEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }, [selectedElementId, activeTab, allTextViewMode]);

  const handleCopyAll = () => {
    navigator.clipboard.writeText(result.reconstructed_text);
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 2000);
  };

  const handleCopyPage = (text: string, pageNum: number) => {
    navigator.clipboard.writeText(text);
    setCopiedPage(pageNum);
    setTimeout(() => setCopiedPage(null), 2000);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col h-[700px]">
      {/* Top Header: Navigation Tabs + Toolbar Controls */}
      <div className="bg-slate-950 border-b border-slate-800 px-4 pt-3 flex flex-wrap items-center justify-between gap-2">
        {/* Navigation Tabs */}
        <div className="flex items-center space-x-1 overflow-x-auto no-scrollbar">
          {[
            { id: 'all', label: 'All Text', icon: AlignLeft, count: null },
            { id: 'native', label: 'Native Text', icon: FileText, count: nativeElements.length },
            { id: 'ocr', label: 'OCR Text', icon: ScanText, count: ocrElements.length },
            { id: 'images', label: 'Images', icon: Image, count: imageElements.length },
            { id: 'tables', label: 'Tables', icon: Table, count: tableElements.length },
            { id: 'structure', label: 'Structure', icon: GitFork, count: null },
          ].map((tab) => {
            const IconComp = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-3 py-2 font-semibold text-xs rounded-t-xl flex items-center space-x-1.5 border-t border-x transition-all duration-150 whitespace-nowrap cursor-pointer ${
                  isActive
                    ? 'bg-slate-900 border-slate-800 text-indigo-400 border-b-transparent'
                    : 'bg-transparent border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <IconComp className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
                {tab.count !== null && (
                  <span
                    className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                      isActive ? 'bg-indigo-500/20 text-indigo-300' : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Sync Scroll Button and Page Selector */}
        <div className="flex items-center space-x-2 pb-2">
          <div className="flex items-center space-x-1.5 font-bold text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 px-2.5 py-1 rounded-lg">
            <FileCode className="w-3.5 h-3.5" />
            <span>Converted Text</span>
          </div>
          {/* Page Switcher */}
          {result.pages.length > 1 && (
            <div className="flex items-center space-x-1 text-xs bg-slate-900 border border-slate-800 rounded-lg p-0.5">
              <button
                type="button"
                onClick={() => onPageChange?.(Math.max(0, currentPageIndex - 1))}
                disabled={currentPageIndex <= 0}
                title="Previous Page"
                className="p-1 rounded text-slate-300 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <select
                value={currentPageIndex}
                onChange={(e) => onPageChange?.(Number(e.target.value))}
                className="bg-transparent text-slate-200 text-xs px-1.5 py-0.5 focus:outline-none cursor-pointer font-medium"
              >
                {result.pages.map((p, idx) => (
                  <option key={idx} value={idx} className="bg-slate-900 text-slate-200">
                    Page {p.page} of {result.pages.length}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => onPageChange?.(Math.min(result.pages.length - 1, currentPageIndex + 1))}
                disabled={currentPageIndex >= result.pages.length - 1}
                title="Next Page"
                className="p-1 rounded text-slate-300 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Sync Scroll Toggle */}
          {onToggleSyncScroll && (
            <button
              onClick={onToggleSyncScroll}
              title={isSyncScroll ? 'Synchronized scrolling enabled' : 'Synchronized scrolling disabled'}
              className={`px-2.5 py-1 rounded-lg border flex items-center space-x-1.5 font-semibold text-[11px] transition cursor-pointer ${
                isSyncScroll
                  ? 'bg-indigo-600/30 border-indigo-500/60 text-indigo-300 shadow-sm'
                  : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-slate-400'
              }`}
            >
              <Link2 className="w-3.5 h-3.5" />
              <span>Sync {isSyncScroll ? 'ON' : 'OFF'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Tab Contents - Continuous Scroll Container */}
      <div
        ref={containerRef}
        onScroll={onScrollContainerScroll}
        className="flex-1 overflow-auto p-4 bg-slate-900"
      >
        {/* Tab 1: All Text (Page-by-page aligned) */}
        {activeTab === 'all' && (
          <div className="space-y-4">
            <div className="flex flex-wrap justify-between items-center bg-slate-950 p-3 rounded-xl border border-slate-800 sticky top-0 z-10 shadow-md gap-2">
              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-200 font-bold">Reconstructed Text</span>
                <span className="text-[10px] text-slate-500 font-mono">
                  ({result.pages.length} {result.pages.length === 1 ? 'page' : 'pages'})
                </span>
                <span className="hidden sm:inline-block text-[11px] text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                  {allTextViewMode === 'plain'
                    ? 'Plain Text View — Click Interactive to inspect element tags'
                    : 'Interactive View — Click any paragraph to jump to original document'}
                </span>
              </div>
              <div className="flex items-center space-x-2">
                {/* View Mode Toggle: Plain Text vs Interactive Cards */}
                <div className="flex items-center space-x-1 bg-slate-900 border border-slate-800 p-0.5 rounded-lg text-xs">
                  <button
                    type="button"
                    onClick={() => setAllTextViewMode('plain')}
                    className={`px-2.5 py-1 rounded font-medium transition cursor-pointer flex items-center space-x-1.5 ${
                      allTextViewMode === 'plain'
                        ? 'bg-indigo-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                    title="Plain text view: continuous text for easy reading and copying"
                  >
                    <AlignLeft className="w-3.5 h-3.5" />
                    <span>Plain Text</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setAllTextViewMode('cards')}
                    className={`px-2.5 py-1 rounded font-medium transition cursor-pointer flex items-center space-x-1.5 ${
                      allTextViewMode === 'cards'
                        ? 'bg-indigo-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                    title="Interactive view: Click any paragraph to locate in the original document"
                  >
                    <Layers className="w-3.5 h-3.5" />
                    <span>Interactive</span>
                  </button>
                </div>

                <button
                  type="button"
                  onClick={handleCopyAll}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded-lg font-medium flex items-center space-x-1.5 transition cursor-pointer"
                >
                  {copiedAll ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedAll ? 'Copied All!' : 'Copy All Text'}</span>
                </button>
              </div>
            </div>

            {pageSections.map((sec, idx) => {
              const pageElems = pageReadingOrderElements[idx] || [];
              const hasElements = pageElems.length > 0;
              const isCurrentPage = currentPageIndex === idx;

              return (
                <div
                  key={sec.pageNumber}
                  ref={(el) => {
                    if (pageRefs.current) {
                      pageRefs.current[idx] = el;
                    }
                  }}
                  className={`bg-slate-950 rounded-xl border transition-all duration-200 overflow-hidden ${
                    isCurrentPage ? 'border-indigo-500/50 shadow-md shadow-indigo-500/10' : 'border-slate-800/80'
                  }`}
                >
                  <div className="bg-slate-900/90 border-b border-slate-800/80 px-4 py-2.5 flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className={`w-2.5 h-2.5 rounded-full ${isCurrentPage ? 'bg-indigo-400 animate-pulse' : 'bg-slate-500'}`}></span>
                      <span className="text-xs font-bold text-slate-200">Page {sec.pageNumber}</span>
                      {hasElements && (
                        <span className="text-[10px] text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded-full">
                          {pageElems.length} {pageElems.length === 1 ? 'block' : 'blocks'}
                        </span>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleCopyPage(sec.text, sec.pageNumber)}
                      className="text-[11px] text-slate-400 hover:text-slate-200 flex items-center space-x-1 transition cursor-pointer px-2 py-0.5 rounded bg-slate-800/60 hover:bg-slate-800"
                    >
                      {copiedPage === sec.pageNumber ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedPage === sec.pageNumber ? 'Copied' : 'Copy Page'}</span>
                    </button>
                  </div>

                  {allTextViewMode === 'cards' && hasElements ? (
                    <div className="p-3 space-y-2">
                      {pageElems.map((elem, elemIdx) => {
                        const isSelected = selectedElementId === elem.id;
                        return (
                          <div
                            key={elem.id || `${idx}-${elemIdx}`}
                            id={`elem-card-${elem.id}`}
                            onClick={() => {
                              if (onPageChange && currentPageIndex !== idx) {
                                onPageChange(idx);
                              }
                              onSelectElement(elem);
                            }}
                            className={`p-3 rounded-xl border transition-all cursor-pointer group text-left ${
                              isSelected
                                ? 'bg-rose-500/15 border-rose-500/80 text-rose-50 shadow-md ring-1 ring-rose-500/50'
                                : 'bg-slate-900/60 border-slate-800/80 hover:border-indigo-500/60 hover:bg-slate-900/90 text-slate-200'
                            }`}
                          >
                            <div className="flex items-center justify-between text-[11px] mb-1.5 opacity-75 group-hover:opacity-100">
                              <div className="flex items-center space-x-2">
                                <span
                                  className={`font-mono text-[10px] px-1.5 py-0.5 rounded font-medium ${
                                    isSelected ? 'bg-rose-500/30 text-rose-300' : 'bg-slate-800 text-slate-400'
                                  }`}
                                >
                                  #{elem.reading_order ?? elemIdx + 1}
                                </span>
                                {elem.tag && (
                                  <span className="font-mono text-[10px] px-1.5 py-0.5 rounded font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                                    &lt;{elem.tag}&gt;
                                  </span>
                                )}
                                <span className="text-[11px] text-slate-400 capitalize">
                                  {elem.content_type || elem.type || 'text'} • {elem.source === 'ocr' ? 'OCR' : elem.source === 'pp_structure' ? 'Structure' : 'Native'}
                                </span>
                                <span className={`text-[9px] px-1 rounded ${elem.is_tagged ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-800 text-slate-500'}`}>
                                  {elem.is_tagged ? 'Tagged' : 'Inferred'}
                                </span>
                              </div>
                              <span
                                className={`text-[10px] flex items-center space-x-0.5 ${
                                  isSelected ? 'text-rose-400 font-semibold' : 'text-indigo-400 group-hover:underline'
                                }`}
                              >
                                <span>{isSelected ? 'Viewing in document' : `Locate on page ${sec.pageNumber}`}</span>
                                <ChevronRight className="w-2.5 h-2.5" />
                              </span>
                            </div>
                            <p className="text-xs font-sans leading-relaxed whitespace-pre-wrap select-text">
                              {elem.text}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="p-4 bg-slate-950">
                      <div className="text-slate-100 font-sans text-xs sm:text-sm whitespace-pre-wrap leading-relaxed select-text font-normal selection:bg-indigo-500/30">
                        {sec.text ? sec.text : <span className="text-slate-500 italic">No text extracted on this page.</span>}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Tab 2: Native Text (Grouped by Page) */}
        {activeTab === 'native' && (
          <div className="space-y-4">
            {result.pages.map((p, pageIdx) => {
              const pageElems = nativeElements.filter((e) => e.page === p.page);
              return (
                <div
                  key={p.page}
                  ref={(el) => {
                    if (pageRefs.current) pageRefs.current[pageIdx] = el;
                  }}
                  className="space-y-2"
                >
                  <div className="text-xs font-semibold text-blue-400 bg-slate-950/80 px-3 py-1.5 rounded-lg border border-slate-800 flex items-center justify-between">
                    <span>Page {p.page}</span>
                    <span className="text-[10px] text-slate-500">{pageElems.length} blocks</span>
                  </div>
                  {pageElems.length === 0 ? (
                    <div className="p-3 text-xs text-slate-500 italic bg-slate-950/40 rounded-xl border border-slate-800/40">
                      No native text blocks on Page {p.page}.
                    </div>
                  ) : (
                    pageElems.map((elem) => {
                      const isSelected = selectedElementId === elem.id;
                      return (
                        <div
                          key={elem.id}
                          onClick={() => onSelectElement(elem)}
                          className={`p-3 rounded-xl border transition cursor-pointer ${
                            isSelected
                              ? 'bg-blue-500/15 border-blue-500/60 text-blue-100 shadow-md'
                              : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700 text-slate-300'
                          }`}
                        >
                          <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                            <span className="font-semibold text-blue-400">Page {elem.page} • Block {elem.block_num ?? elem.id}</span>
                            {elem.bbox && (
                              <span className="font-mono text-[10px] text-slate-500">
                                BBox: [{elem.bbox.map((n) => Math.round(n)).join(', ')}]
                              </span>
                            )}
                          </div>
                          <p className="text-xs font-sans leading-relaxed">{elem.text}</p>
                        </div>
                      );
                    })
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Tab 3: OCR Text (Grouped by Page) */}
        {activeTab === 'ocr' && (
          <div className="space-y-4">
            {result.pages.map((p, pageIdx) => {
              const pageElems = ocrElements.filter((e) => e.page === p.page);
              return (
                <div
                  key={p.page}
                  ref={(el) => {
                    if (pageRefs.current) pageRefs.current[pageIdx] = el;
                  }}
                  className="space-y-2"
                >
                  <div className="text-xs font-semibold text-emerald-400 bg-slate-950/80 px-3 py-1.5 rounded-lg border border-slate-800 flex items-center justify-between">
                    <span>Page {p.page}</span>
                    <span className="text-[10px] text-slate-500">{pageElems.length} elements</span>
                  </div>
                  {pageElems.length === 0 ? (
                    <div className="p-3 text-xs text-slate-500 italic bg-slate-950/40 rounded-xl border border-slate-800/40">
                      No OCR text blocks on Page {p.page}.
                    </div>
                  ) : (
                    pageElems.map((elem) => {
                      const isSelected = selectedElementId === elem.id;
                      return (
                        <div
                          key={elem.id}
                          onClick={() => onSelectElement(elem)}
                          className={`p-3 rounded-xl border transition cursor-pointer ${
                            isSelected
                              ? 'bg-emerald-500/15 border-emerald-500/60 text-emerald-100 shadow-md'
                              : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700 text-slate-300'
                          }`}
                        >
                          <div className="flex items-center justify-between text-[11px] mb-1">
                            <div className="flex items-center space-x-2">
                              <span className="font-semibold text-emerald-400">Page {elem.page} • PaddleOCR</span>
                            </div>
                            {elem.possible_duplicate && (
                              <span className="px-2 py-0.5 rounded bg-orange-500/20 text-orange-300 text-[10px] font-semibold flex items-center space-x-1">
                                <Info className="w-3 h-3" />
                                <span>Possible Duplicate</span>
                              </span>
                            )}
                          </div>
                          <p className="text-xs font-sans leading-relaxed">{elem.text}</p>
                        </div>
                      );
                    })
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Tab 4: Images & Equations (Grouped by Page) */}
        {activeTab === 'images' && (
          <div className="space-y-4">
            {result.pages.map((p, pageIdx) => {
              const pageElems = imageElements.filter((e) => e.page === p.page);
              return (
                <div
                  key={p.page}
                  ref={(el) => {
                    if (pageRefs.current) pageRefs.current[pageIdx] = el;
                  }}
                  className="space-y-3"
                >
                  <div className="text-xs font-semibold text-purple-400 bg-slate-950/80 px-3 py-1.5 rounded-lg border border-slate-800 flex items-center justify-between">
                    <span>Page {p.page}</span>
                    <span className="text-[10px] text-slate-500">{pageElems.length} items</span>
                  </div>
                  {pageElems.length === 0 ? (
                    <div className="p-3 text-xs text-slate-500 italic bg-slate-950/40 rounded-xl border border-slate-800/40">
                      No images or formulas on Page {p.page}.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {pageElems.map((imgElem) => {
                        const isSelected = selectedElementId === imgElem.id;
                        const relatedOcr = ocrElements.filter(
                          (o) => o.image_id === imgElem.image_id || (o.bbox && imgElem.bbox && o.page === imgElem.page)
                        );
                        return (
                          <div
                            key={imgElem.id}
                            onClick={() => onSelectElement(imgElem)}
                            className={`p-4 rounded-xl border transition cursor-pointer space-y-2 ${
                              isSelected
                                ? 'bg-purple-500/15 border-purple-500/60 text-purple-100 shadow-md'
                                : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700 text-slate-300'
                            }`}
                          >
                            <div className="flex items-center justify-between text-xs font-semibold text-purple-400">
                              <div className="flex items-center space-x-1.5">
                                <span>Page {imgElem.page} •</span>
                                {imgElem.type === 'formula' ? (
                                  <span className="px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 text-[10px] font-bold">
                                    MathType Equation
                                  </span>
                                ) : (
                                  <span>Image {imgElem.image_id || imgElem.id}</span>
                                )}
                              </div>
                            </div>
                            {imgElem.image_path && (
                              <div className="w-full h-44 bg-slate-900 rounded-lg overflow-hidden border border-slate-800 flex items-center justify-center p-1">
                                <img
                                  src={imgElem.image_path}
                                  alt={imgElem.image_id || 'Extracted Image'}
                                  loading="lazy"
                                  className="max-h-full max-w-full object-contain rounded"
                                />
                              </div>
                            )}
                            {imgElem.bbox && (
                              <p className="text-[10px] font-mono text-slate-400">
                                BBox: [{imgElem.bbox.map((n) => Math.round(n)).join(', ')}]
                              </p>
                            )}
                            {relatedOcr.length > 0 && (
                              <div className="p-2 bg-slate-900 rounded-lg text-xs space-y-1 border border-slate-800">
                                <span className="text-[10px] font-bold text-emerald-400">OCR Text Inside Image:</span>
                                {relatedOcr.map((ocr) => (
                                  <p key={ocr.id} className="text-slate-300 italic text-[11px]">
                                    {ocr.text}
                                  </p>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Tab 5: Tables (Grouped by Page) */}
        {activeTab === 'tables' && (
          <div className="space-y-4">
            {result.pages.map((p, pageIdx) => {
              const pageElems = tableElements.filter((e) => e.page === p.page);
              return (
                <div
                  key={p.page}
                  ref={(el) => {
                    if (pageRefs.current) pageRefs.current[pageIdx] = el;
                  }}
                  className="space-y-3"
                >
                  <div className="text-xs font-semibold text-amber-400 bg-slate-950/80 px-3 py-1.5 rounded-lg border border-slate-800 flex items-center justify-between">
                    <span>Page {p.page}</span>
                    <span className="text-[10px] text-slate-500">{pageElems.length} tables</span>
                  </div>
                  {pageElems.length === 0 ? (
                    <div className="p-3 text-xs text-slate-500 italic bg-slate-950/40 rounded-xl border border-slate-800/40">
                      No tables on Page {p.page}.
                    </div>
                  ) : (
                    pageElems.map((tbl) => (
                      <div key={tbl.id} className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                        <div className="text-xs font-semibold text-amber-400">
                          Page {tbl.page} • Table ({tbl.rows?.length || 0} rows)
                        </div>
                        {tbl.rows && tbl.rows.length > 0 && (
                          <div className="overflow-x-auto rounded-lg border border-slate-800">
                            <table className="w-full text-left text-xs border-collapse">
                              <tbody>
                                {tbl.rows.map((row, rIdx) => (
                                  <tr
                                    key={rIdx}
                                    className={
                                      rIdx === 0
                                        ? 'bg-slate-800/80 font-semibold text-amber-300'
                                        : 'border-t border-slate-800 text-slate-300 hover:bg-slate-900'
                                    }
                                  >
                                    {row.map((cell, cIdx) => (
                                      <td key={cIdx} className="p-2 border-r border-slate-800/60">
                                        {cell}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Tab 6: Document Structure Tree (Grouped by Page) */}
        {activeTab === 'structure' && (
          <div className="space-y-4 font-mono text-xs">
            {result.tagging_summary && (
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl flex flex-wrap items-center justify-between text-xs gap-2 font-sans">
                <div className="flex items-center space-x-2">
                  <span className="text-slate-400 font-medium">Document Tag Status:</span>
                  <span
                    className={`px-2 py-0.5 rounded-full font-bold uppercase text-[10px] ${
                      result.tagging_summary.document_tag_status === 'tagged'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : result.tagging_summary.document_tag_status === 'partially_tagged'
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        : 'bg-slate-800 text-slate-300 border border-slate-700'
                    }`}
                  >
                    {result.tagging_summary.document_tag_status}
                  </span>
                </div>
                <div className="flex items-center space-x-3 text-[11px] text-slate-400">
                  <span>Tagged: <strong className="text-emerald-400">{result.tagging_summary.tagged_elements_count}</strong></span>
                  <span>Inferred: <strong className="text-indigo-400">{result.tagging_summary.inferred_elements_count}</strong></span>
                  <span>Total Elements: <strong className="text-slate-200">{result.tagging_summary.total_elements}</strong></span>
                </div>
              </div>
            )}

            {result.pages.map((p, pageIdx) => (
              <div
                key={p.page}
                ref={(el) => {
                  if (pageRefs.current) pageRefs.current[pageIdx] = el;
                }}
                className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2"
              >
                <div className="font-bold text-indigo-400 flex items-center justify-between">
                  <span>Page {p.page}</span>
                  <span className="text-[10px] text-slate-500 font-sans">{p.elements.length} elements</span>
                </div>
                <div className="pl-4 border-l border-slate-800 space-y-1">
                  {p.elements.map((elem) => (
                    <div
                      key={elem.id}
                      onClick={() => onSelectElement(elem)}
                      className={`p-1.5 rounded cursor-pointer transition flex items-center justify-between text-[11px] ${
                        selectedElementId === elem.id ? 'bg-indigo-500/20 text-indigo-200' : 'hover:bg-slate-900 text-slate-300'
                      }`}
                    >
                      <div className="flex items-center space-x-2 truncate">
                        <span className="font-bold text-indigo-400 font-mono">[{elem.tag || elem.content_type || elem.type}]</span>
                        <span className="text-slate-500">({elem.content_type || elem.type})</span>
                        <span className={`text-[9px] px-1 rounded ${elem.is_tagged ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-800 text-slate-400'}`}>
                          {elem.is_tagged ? 'TAGGED' : 'INFERRED'}
                        </span>
                        <span className="truncate font-sans">{elem.text ? `"${elem.text.slice(0, 40)}..."` : ''}</span>
                      </div>
                      <span className="text-[10px] text-slate-600">Order: {elem.reading_order}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
