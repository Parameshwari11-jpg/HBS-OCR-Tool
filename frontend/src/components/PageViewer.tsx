import React, { useState, useRef, useEffect } from 'react';
import { PageData, ExtractedElement } from '../types/extraction';
import { ZoomIn, ZoomOut, RotateCcw, Link2, FileText, ChevronLeft, ChevronRight } from 'lucide-react';

interface PageViewerProps {
  pages: PageData[];
  selectedElementId: string | null;
  onSelectElement: (element: ExtractedElement | null) => void;
  currentPageIndex?: number;
  onPageChange?: (index: number) => void;
  onActivePageChange?: (index: number) => void;
  isSyncScroll?: boolean;
  onToggleSyncScroll?: () => void;
  onScrollContainerScroll?: () => void;
  containerRefExternal?: React.RefObject<HTMLDivElement | null>;
  pageRefsExternal?: React.MutableRefObject<(HTMLDivElement | null)[]>;
}

export const PageViewer: React.FC<PageViewerProps> = ({
  pages,
  selectedElementId,
  onSelectElement,
  currentPageIndex,
  onPageChange,
  onActivePageChange,
  isSyncScroll = true,
  onToggleSyncScroll,
  onScrollContainerScroll,
  containerRefExternal,
  pageRefsExternal,
}) => {
  const [internalPageIndex, setInternalPageIndex] = useState(0);
  const activePageIndex = currentPageIndex !== undefined ? currentPageIndex : internalPageIndex;

  const [zoom, setZoom] = useState(1.0);
  const [showNativeTextBbox, setShowNativeTextBbox] = useState(true);
  const [showOcrBbox, setShowOcrBbox] = useState(true);
  const [showImageBbox, setShowImageBbox] = useState(true);
  const [showTableBbox, setShowTableBbox] = useState(true);
  const [showFormulaBbox, setShowFormulaBbox] = useState(true);

  const localContainerRef = useRef<HTMLDivElement>(null);
  const containerRef = containerRefExternal || localContainerRef;

  const localPageRefs = useRef<(HTMLDivElement | null)[]>([]);
  const pageRefs = pageRefsExternal || localPageRefs;
  const isProgrammaticScroll = useRef(false);
  const lastSelectedElementIdRef = useRef<string | null>(null);

  if (!pages || pages.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center text-slate-400">
        No page preview available.
      </div>
    );
  }

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.2, 2.5));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.2, 0.5));
  const handleResetZoom = () => setZoom(1.0);

  // Jump to page when selected via dropdown or prev/next buttons
  const handlePageNavigation = (newIndex: number) => {
    if (newIndex < 0 || newIndex >= pages.length) return;
    if (onPageChange) {
      onPageChange(newIndex);
    } else {
      setInternalPageIndex(newIndex);
    }
    const targetEl = pageRefs.current[newIndex];
    if (targetEl && containerRef.current) {
      isProgrammaticScroll.current = true;
      targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setTimeout(() => {
        isProgrammaticScroll.current = false;
      }, 700);
    }
  };

  // Update current page dropdown dynamically as the user scrolls
  const handleScroll = () => {
    if (isProgrammaticScroll.current || !containerRef.current) return;

    const container = containerRef.current;
    const containerTop = container.scrollTop;
    const containerMid = containerTop + container.clientHeight * 0.35;

    let activeIndex = 0;
    for (let i = 0; i < pages.length; i++) {
      const el = pageRefs.current[i];
      if (el) {
        const elTop = el.getBoundingClientRect().top - container.getBoundingClientRect().top + container.scrollTop;
        const elBottom = elTop + el.offsetHeight;
        if (containerMid >= elTop && containerMid <= elBottom) {
          activeIndex = i;
          break;
        } else if (elTop > containerMid) {
          break;
        }
        activeIndex = i;
      }
    }

    if (activeIndex !== activePageIndex && activeIndex >= 0 && activeIndex < pages.length) {
      if (onActivePageChange) {
        onActivePageChange(activeIndex);
      } else if (!onPageChange) {
        setInternalPageIndex(activeIndex);
      }
    }
  };

  // Navigate to and center element's exact location on its page when selected
  useEffect(() => {
    if (!selectedElementId) {
      lastSelectedElementIdRef.current = null;
      return;
    }
    // Only scroll if the selected element actually changed
    if (selectedElementId === lastSelectedElementIdRef.current) return;
    lastSelectedElementIdRef.current = selectedElementId;

    for (let i = 0; i < pages.length; i++) {
      const elem = pages[i].elements.find((e) => e.id === selectedElementId);
      if (elem) {
        if (i !== activePageIndex) {
          if (onPageChange) {
            onPageChange(i);
          } else {
            setInternalPageIndex(i);
          }
        }

        const pageEl = pageRefs.current[i];
        const container = containerRef.current;
        if (pageEl && container) {
          isProgrammaticScroll.current = true;
          const containerRect = container.getBoundingClientRect();
          const pageRect = pageEl.getBoundingClientRect();
          const pageTopInContainer = pageRect.top - containerRect.top + container.scrollTop;

          let targetScrollTop = pageTopInContainer;
          if (elem.bbox && elem.bbox.length >= 4) {
            const scaleY = pageEl.offsetHeight / Math.max(1, pages[i].height);
            const elemTop = elem.bbox[1] * scaleY;
            const elemHeight = (elem.bbox[3] - elem.bbox[1]) * scaleY;
            // Center element vertically in container
            targetScrollTop = pageTopInContainer + elemTop - (container.clientHeight / 2) + (elemHeight / 2);
          }

          container.scrollTo({ top: Math.max(0, targetScrollTop), behavior: 'smooth' });
          setTimeout(() => {
            isProgrammaticScroll.current = false;
          }, 700);
        }
        break;
      }
    }
  }, [selectedElementId, pages, activePageIndex, onPageChange]);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col h-[700px]">
      {/* Viewer Header / Toolbar */}
      <div className="bg-slate-950 border-b border-slate-800 p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        {/* Heading Badge & Page Switcher */}
        <div className="flex items-center space-x-2.5">
          <div className="flex items-center space-x-1.5 font-bold text-xs bg-blue-500/20 text-blue-300 border border-blue-500/40 px-2.5 py-1 rounded-lg">
            <FileText className="w-3.5 h-3.5" />
            <span>Uploaded File</span>
          </div>

          {/* Page Navigation with Previous / Next Buttons */}
          <div className="flex items-center space-x-1 bg-slate-900 border border-slate-700/80 rounded-lg p-0.5">
            <button
              onClick={() => handlePageNavigation(activePageIndex - 1)}
              disabled={activePageIndex <= 0}
              className="p-1 rounded text-slate-300 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition cursor-pointer"
              title="Previous Page"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <select
              value={activePageIndex}
              onChange={(e) => handlePageNavigation(Number(e.target.value))}
              className="bg-transparent text-slate-100 px-2 py-0.5 text-xs focus:outline-none font-medium cursor-pointer"
            >
              {pages.map((p, idx) => (
                <option key={idx} value={idx} className="bg-slate-900 text-slate-100">
                  Page {p.page} of {pages.length}
                </option>
              ))}
            </select>
            <button
              onClick={() => handlePageNavigation(activePageIndex + 1)}
              disabled={activePageIndex >= pages.length - 1}
              className="p-1 rounded text-slate-300 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition cursor-pointer"
              title="Next Page"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center space-x-1 bg-slate-900 border border-slate-800 rounded-lg p-1">
          <button
            onClick={handleZoomOut}
            className="p-1.5 hover:bg-slate-800 rounded text-slate-300 hover:text-white transition cursor-pointer"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="px-2 font-mono font-semibold text-indigo-400">{Math.round(zoom * 100)}%</span>
          <button
            onClick={handleZoomIn}
            className="p-1.5 hover:bg-slate-800 rounded text-slate-300 hover:text-white transition cursor-pointer"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleResetZoom}
            className="p-1.5 hover:bg-slate-800 rounded text-slate-300 hover:text-white transition ml-1 border-l border-slate-800 cursor-pointer"
            title="Reset Zoom"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Sync Scroll & Bounding Box Toggle Filters */}
        <div className="flex items-center space-x-2">
          {onToggleSyncScroll && (
            <button
              onClick={onToggleSyncScroll}
              className={`px-2 py-1 rounded-lg flex items-center space-x-1 border text-[11px] transition cursor-pointer font-medium ${
                isSyncScroll
                  ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300 shadow-sm'
                  : 'bg-slate-900 border-slate-700 text-slate-500 hover:text-slate-400'
              }`}
              title="Toggle synchronized scrolling between document preview and extracted text"
            >
              <Link2 className={`w-3.5 h-3.5 ${isSyncScroll ? 'text-indigo-400' : 'text-slate-500'}`} />
              <span>Sync {isSyncScroll ? 'ON' : 'OFF'}</span>
            </button>
          )}

          <button
            onClick={() => setShowNativeTextBbox(!showNativeTextBbox)}
            className={`px-2 py-1 rounded flex items-center space-x-1 border text-[11px] transition cursor-pointer ${
              showNativeTextBbox
                ? 'bg-blue-500/20 border-blue-500/50 text-blue-300'
                : 'bg-slate-900 border-slate-800 text-slate-500'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-blue-400 inline-block"></span>
            <span>Native</span>
          </button>

          <button
            onClick={() => setShowOcrBbox(!showOcrBbox)}
            className={`px-2 py-1 rounded flex items-center space-x-1 border text-[11px] transition cursor-pointer ${
              showOcrBbox
                ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300'
                : 'bg-slate-900 border-slate-800 text-slate-500'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block"></span>
            <span>OCR</span>
          </button>

          <button
            onClick={() => setShowImageBbox(!showImageBbox)}
            className={`px-2 py-1 rounded flex items-center space-x-1 border text-[11px] transition cursor-pointer ${
              showImageBbox
                ? 'bg-purple-500/20 border-purple-500/50 text-purple-300'
                : 'bg-slate-900 border-slate-800 text-slate-500'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-purple-400 inline-block"></span>
            <span>Images</span>
          </button>

          <button
            onClick={() => setShowTableBbox(!showTableBbox)}
            className={`px-2 py-1 rounded flex items-center space-x-1 border text-[11px] transition cursor-pointer ${
              showTableBbox
                ? 'bg-amber-500/20 border-amber-500/50 text-amber-300'
                : 'bg-slate-900 border-slate-800 text-slate-500'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-amber-400 inline-block"></span>
            <span>Tables</span>
          </button>

          <button
            onClick={() => setShowFormulaBbox(!showFormulaBbox)}
            className={`px-2 py-1 rounded flex items-center space-x-1 border text-[11px] transition cursor-pointer ${
              showFormulaBbox
                ? 'bg-rose-500/20 border-rose-500/50 text-rose-300'
                : 'bg-slate-900 border-slate-800 text-slate-500'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-rose-400 inline-block"></span>
            <span>Formulas / Math</span>
          </button>
        </div>
      </div>

      {/* Interactive Continuous Scroll Viewport */}
      <div
        ref={containerRef}
        onScroll={(e) => {
          handleScroll();
          onScrollContainerScroll?.();
        }}
        className="flex-1 overflow-auto bg-slate-950 p-4 select-none flex flex-col items-center gap-6"
      >
        {pages.map((page, pageIdx) => {
          const pageWidth = page.width * zoom;
          const pageHeight = page.height * zoom;

          return (
            <div
              key={page.page}
              ref={(el) => {
                pageRefs.current[pageIdx] = el;
              }}
              data-page-index={pageIdx}
              className="relative shadow-2xl rounded border border-slate-800 bg-white flex-shrink-0"
              style={{
                width: `${pageWidth}px`,
                height: `${pageHeight}px`,
              }}
            >
              {page.rendered_image_url ? (
                <img
                  src={page.rendered_image_url}
                  alt={`Page ${page.page}`}
                  loading="lazy"
                  className="w-full h-full object-contain block select-none"
                />
              ) : (
                <div className="w-full h-full bg-white flex flex-col items-center justify-center p-6 text-slate-700 overflow-auto">
                  <div className="text-xs font-semibold text-slate-400 mb-3">Document Page {page.page}</div>
                  {page.elements.filter((e) => e.type === 'image' && e.image_path).map((imgElem) => (
                    <div key={imgElem.id} className="max-w-full my-2 border border-slate-200 rounded p-2 bg-slate-50 shadow-sm">
                      <img
                        src={imgElem.image_path}
                        alt={imgElem.image_id || 'Document Image'}
                        className="max-h-[500px] object-contain mx-auto"
                      />
                    </div>
                  ))}
                </div>
              )}

              {/* SVG Bounding Box Overlays */}
              <svg
                className="absolute top-0 left-0 w-full h-full pointer-events-auto"
                viewBox={`0 0 ${page.width} ${page.height}`}
              >
                {page.elements.map((elem) => {
                  if (!elem.bbox || elem.bbox.length < 4) return null;

                  const [x0, y0, x1, y1] = elem.bbox;
                  const width = Math.max(x1 - x0, 2);
                  const height = Math.max(y1 - y0, 2);

                  const isSelected = selectedElementId === elem.id;

                  const isVisual = elem.type === 'image' || elem.type === 'figure' || elem.type === 'drawing' || elem.source === 'visual_detector';

                  // Filter checks
                  if (elem.source === 'native' && !isVisual && !showNativeTextBbox && !isSelected) return null;
                  if (elem.source === 'ocr' && !showOcrBbox && !isSelected) return null;
                  if (isVisual && !showImageBbox && !isSelected) return null;
                  if (elem.type === 'table' && !showTableBbox && !isSelected) return null;
                  if (elem.type === 'formula' && !showFormulaBbox && !isSelected) return null;

                  // Color styles
                  let strokeColor = '#3b82f6'; // blue
                  let fillColor = 'rgba(59, 130, 246, 0.08)';

                  if (elem.source === 'ocr') {
                    strokeColor = '#10b981'; // emerald
                    fillColor = 'rgba(16, 185, 129, 0.1)';
                  } else if (isVisual) {
                    strokeColor = '#ec4899'; // vivid pink/magenta for distinct visual elements
                    fillColor = 'rgba(236, 72, 153, 0.12)';
                  } else if (elem.type === 'table') {
                    strokeColor = '#f59e0b'; // amber
                    fillColor = 'rgba(245, 158, 11, 0.12)';
                  } else if (elem.type === 'formula') {
                    strokeColor = '#f43f5e'; // rose
                    fillColor = 'rgba(244, 63, 94, 0.12)';
                  }

                  if (isSelected) {
                    strokeColor = '#f43f5e'; // rose highlight
                    fillColor = 'rgba(244, 63, 94, 0.3)';
                  }

                  return (
                    <rect
                      key={elem.id}
                      x={x0}
                      y={y0}
                      width={width}
                      height={height}
                      fill={fillColor}
                      stroke={strokeColor}
                      strokeWidth={isSelected ? 2.5 : (isVisual ? 1.5 : 1)}
                      strokeDasharray={elem.possible_duplicate ? '3 3' : 'none'}
                      className="cursor-pointer transition-all hover:opacity-80"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectElement(elem);
                      }}
                    >
                      <title>{`${elem.type} [${elem.parameters?.subtype || elem.tag || ''}] (${elem.source}): ${elem.text || elem.id}`}</title>
                    </rect>
                  );
                })}
              </svg>

              {/* Discreet page badge at the bottom right */}
              <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-slate-900/70 backdrop-blur text-slate-300 text-[10px] font-mono pointer-events-none select-none">
                Page {page.page} / {pages.length}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
