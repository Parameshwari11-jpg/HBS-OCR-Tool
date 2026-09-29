import React, { useState, useRef, useEffect, useMemo } from 'react';
import { ExtractionResult, ExtractedElement, PageData } from '../types/extraction';
import { FileText, ScanText, Image, Table, GitFork, AlignLeft, Copy, Check, Info, Link2, FileCode } from 'lucide-react';

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
  const [copiedAll, setCopiedAll] = useState(false);
  const [copiedPage, setCopiedPage] = useState<number | null>(null);

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
    if (!result.reconstructed_text) {
      return result.pages.map((p) => ({ pageNumber: p.page, text: '' }));
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
        text: sectionsMap.get(p.page) ?? '',
      }));
    }

    // Fallback if no page delimiters present
    return result.pages.map((p, idx) => ({
      pageNumber: p.page,
      text: idx === 0 ? result.reconstructed_text.trim() : '',
    }));
  }, [result.reconstructed_text, result.pages]);

  // When active tab changes, auto-align to current page
  useEffect(() => {
    if (currentPageIndex !== undefined && pageRefs.current[currentPageIndex]) {
      pageRefs.current[currentPageIndex]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [activeTab]);

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
            <div className="flex items-center space-x-1.5 text-xs">
              <span className="text-slate-400 text-[11px] font-medium">Page:</span>
              <select
                value={currentPageIndex}
                onChange={(e) => onPageChange?.(Number(e.target.value))}
                className="bg-slate-900 border border-slate-700 text-slate-200 rounded-lg px-2 py-1 text-xs focus:outline-none focus:border-indigo-500 cursor-pointer"
              >
                {result.pages.map((p, idx) => (
                  <option key={idx} value={idx}>
                    {p.page} / {result.pages.length}
                  </option>
                ))}
              </select>
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
            <div className="flex justify-between items-center bg-slate-950 p-3 rounded-xl border border-slate-800 sticky top-0 z-10 shadow-md">
              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-300 font-semibold">Reconstructed Text in Reading Order</span>
                <span className="text-[10px] text-slate-500 font-mono">({result.pages.length} {result.pages.length === 1 ? 'page' : 'pages'})</span>
              </div>
              <button
                onClick={handleCopyAll}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded-lg font-medium flex items-center space-x-1.5 transition cursor-pointer"
              >
                {copiedAll ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedAll ? 'Copied All!' : 'Copy All Text'}</span>
              </button>
            </div>

            {pageSections.map((sec, idx) => (
              <div
                key={sec.pageNumber}
                ref={(el) => {
                  if (pageRefs.current) {
                    pageRefs.current[idx] = el;
                  }
                }}
                className={`bg-slate-950 rounded-xl border transition-all duration-200 overflow-hidden ${
                  currentPageIndex === idx ? 'border-indigo-500/50 shadow-md shadow-indigo-500/10' : 'border-slate-800/80'
                }`}
              >
                <div className="bg-slate-900/90 border-b border-slate-800/80 px-4 py-2.5 flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className={`w-2.5 h-2.5 rounded-full ${currentPageIndex === idx ? 'bg-indigo-400 animate-pulse' : 'bg-slate-500'}`}></span>
                    <span className="text-xs font-bold text-slate-200">Page {sec.pageNumber}</span>
                  </div>
                  <button
                    onClick={() => handleCopyPage(sec.text, sec.pageNumber)}
                    className="text-[11px] text-slate-400 hover:text-slate-200 flex items-center space-x-1 transition cursor-pointer px-2 py-0.5 rounded bg-slate-800/60 hover:bg-slate-800"
                  >
                    {copiedPage === sec.pageNumber ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedPage === sec.pageNumber ? 'Copied' : 'Copy Page'}</span>
                  </button>
                </div>
                <pre className="p-4 text-slate-200 font-mono text-xs whitespace-pre-wrap leading-relaxed overflow-x-auto selection:bg-indigo-500/30">
                  {sec.text ? sec.text : <span className="text-slate-500 italic">No text extracted on this page.</span>}
                </pre>
              </div>
            ))}
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
                              {elem.confidence !== undefined && (
                                <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-bold">
                                  {elem.confidence}% conf
                                </span>
                              )}
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
                        <span className="font-semibold text-slate-400">[{elem.type}]</span>
                        <span className="text-slate-500">({elem.source})</span>
                        <span className="truncate">{elem.text ? `"${elem.text.slice(0, 40)}..."` : ''}</span>
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
