import React, { useState, useRef } from 'react';
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Image as ImageIcon,
  Loader2,
  ChevronLeft,
  ChevronRight,
  FileText,
  Layers,
  FileCheck,
} from 'lucide-react';
import { PageOriginalityResult } from '../../types/originality';

export interface OriginalDocumentViewerProps {
  pages: PageOriginalityResult[];
  selectedPageIndex: number;
  onSelectPage: (index: number) => void;
  originalFilename?: string;
  jobId?: string;
}

export const OriginalDocumentViewer: React.FC<OriginalDocumentViewerProps> = ({
  pages,
  selectedPageIndex,
  onSelectPage,
  originalFilename,
  jobId,
}) => {
  const [zoom, setZoom] = useState<number>(1.0);
  const [displayMode, setDisplayMode] = useState<'single' | 'all'>('single');
  const [loadedImages, setLoadedImages] = useState<Record<number, boolean>>({});

  const currentPage = pages[selectedPageIndex] || pages[0];
  const totalPages = pages.length;

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.25, 3.0));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.25, 0.5));
  const handleResetZoom = () => setZoom(1.0);

  const handlePrevPage = () => {
    if (selectedPageIndex > 0) {
      onSelectPage(selectedPageIndex - 1);
    }
  };

  const handleNextPage = () => {
    if (selectedPageIndex < totalPages - 1) {
      onSelectPage(selectedPageIndex + 1);
    }
  };

  const getPageImageUrl = (pageResult: PageOriginalityResult) => {
    return (
      pageResult.preview_image_url ||
      (jobId ? `/api/preview/${jobId}/${pageResult.page}` : null)
    );
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-inner">
      {/* Top Viewer Toolbar */}
      <div className="bg-slate-900/95 border-b border-slate-800 px-3 py-2 flex flex-wrap items-center justify-between gap-2 shrink-0">
        {/* Left: Document Info & Page Navigator */}
        <div className="flex items-center space-x-2">
          <span className="p-1 rounded bg-blue-500/10 text-blue-400">
            <ImageIcon className="w-3.5 h-3.5" />
          </span>
          <span
            className="text-xs font-bold text-white max-w-[140px] sm:max-w-[200px] truncate"
            title={originalFilename || 'Original Document'}
          >
            {originalFilename || 'Original Document'}
          </span>

          {/* Page Selector & Prev/Next Buttons */}
          <div className="flex items-center space-x-1 bg-slate-950 border border-slate-800 rounded-lg p-0.5 ml-1">
            <button
              type="button"
              onClick={handlePrevPage}
              disabled={selectedPageIndex <= 0}
              className="p-1 text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:hover:bg-transparent rounded transition cursor-pointer"
              title="Previous Page"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>

            <select
              value={selectedPageIndex}
              onChange={(e) => onSelectPage(Number(e.target.value))}
              className="bg-transparent text-xs font-bold text-blue-400 px-1 py-0.5 outline-none cursor-pointer"
              title="Select Page"
            >
              {pages.map((p, idx) => (
                <option key={p.page} value={idx} className="bg-slate-900 text-white">
                  Page {p.page} of {totalPages}
                </option>
              ))}
            </select>

            <button
              type="button"
              onClick={handleNextPage}
              disabled={selectedPageIndex >= totalPages - 1}
              className="p-1 text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:hover:bg-transparent rounded transition cursor-pointer"
              title="Next Page"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Right: Display Mode (Single vs All Pages) & Zoom Controls */}
        <div className="flex items-center space-x-2">
          {/* View Mode Toggle */}
          <div className="flex items-center space-x-0.5 bg-slate-950 border border-slate-800 rounded-lg p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setDisplayMode('single')}
              className={`px-2 py-1 rounded font-medium transition cursor-pointer flex items-center space-x-1 text-[11px] ${
                displayMode === 'single'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Show only selected page"
            >
              <FileText className="w-3 h-3" />
              <span>Page {currentPage?.page}</span>
            </button>
            <button
              type="button"
              onClick={() => setDisplayMode('all')}
              className={`px-2 py-1 rounded font-medium transition cursor-pointer flex items-center space-x-1 text-[11px] ${
                displayMode === 'all'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Scroll all pages of the original document"
            >
              <Layers className="w-3 h-3" />
              <span>All Pages ({totalPages})</span>
            </button>
          </div>

          {/* Zoom Controls */}
          <div className="flex items-center space-x-1 bg-slate-950 border border-slate-800 rounded-lg p-0.5">
            <button
              type="button"
              onClick={handleZoomOut}
              className="p-1 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition cursor-pointer"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="text-[10px] font-mono text-slate-300 px-1 min-w-[2.5rem] text-center select-none">
              {Math.round(zoom * 100)}%
            </span>
            <button
              type="button"
              onClick={handleZoomIn}
              className="p-1 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition cursor-pointer"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={handleResetZoom}
              className="p-1 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition cursor-pointer"
              title="Reset Zoom"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Document View Canvas */}
      <div className="flex-1 overflow-auto p-4 bg-slate-950 flex flex-col items-center">
        {displayMode === 'single' ? (
          /* SINGLE PAGE VIEW */
          <div
            className="transition-transform duration-150 origin-top flex flex-col items-center justify-center my-auto"
            style={{ transform: `scale(${zoom})`, transformOrigin: 'top center' }}
          >
            {currentPage && getPageImageUrl(currentPage) ? (
              <div className="relative shadow-2xl rounded border border-slate-700/60 bg-white">
                {!loadedImages[currentPage.page] && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/70 z-10 space-y-2 p-8">
                    <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
                    <span className="text-xs text-slate-300">Loading Page {currentPage.page}...</span>
                  </div>
                )}
                <img
                  src={getPageImageUrl(currentPage)!}
                  alt={`Original Document Page ${currentPage.page}`}
                  className={`max-w-full h-auto transition-opacity duration-300 ${
                    loadedImages[currentPage.page] ? 'opacity-100' : 'opacity-0'
                  }`}
                  onLoad={() => setLoadedImages((prev) => ({ ...prev, [currentPage.page]: true }))}
                />
              </div>
            ) : (
              <div className="p-8 text-center text-slate-500">
                <FileText className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                <p className="text-xs">No preview available for page {currentPage?.page}</p>
              </div>
            )}
          </div>
        ) : (
          /* CONTINUOUS ALL PAGES VIEW */
          <div
            className="transition-transform duration-150 origin-top flex flex-col items-center space-y-6 w-full"
            style={{ transform: `scale(${zoom})`, transformOrigin: 'top center' }}
          >
            {pages.map((p, idx) => {
              const url = getPageImageUrl(p);
              const isSelected = idx === selectedPageIndex;
              return (
                <div
                  key={p.page}
                  onClick={() => onSelectPage(idx)}
                  className={`flex flex-col items-center w-full max-w-2xl transition-all cursor-pointer ${
                    isSelected ? 'ring-2 ring-blue-500 rounded-lg p-1 bg-blue-500/5' : ''
                  }`}
                >
                  <div className="w-full flex items-center justify-between pb-1.5 px-2 text-[11px]">
                    <span className="font-bold text-slate-300 flex items-center space-x-1">
                      <span>Page {p.page} of {totalPages}</span>
                      {isSelected && (
                        <span className="text-[10px] text-blue-400 bg-blue-500/20 px-1.5 py-0.2 rounded font-mono">
                          Active
                        </span>
                      )}
                    </span>
                    <span className="text-slate-500 font-mono text-[10px]">
                      {p.orig_word_count} words &bull; {p.accuracy}% Match
                    </span>
                  </div>

                  {url ? (
                    <div className="relative shadow-2xl rounded border border-slate-700/60 bg-white w-full">
                      <img
                        src={url}
                        alt={`Original Document Page ${p.page}`}
                        className="w-full h-auto"
                        loading="lazy"
                      />
                    </div>
                  ) : (
                    <div className="p-8 text-center text-slate-500 bg-slate-900 rounded border border-slate-800 w-full">
                      <FileText className="w-6 h-6 mx-auto mb-1 text-slate-600" />
                      <p className="text-xs">Page {p.page} preview not generated</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Bottom Status Bar */}
      <div className="bg-slate-900/90 border-t border-slate-800 px-3 py-1.5 flex items-center justify-between text-[11px] text-slate-400 shrink-0">
        <div className="flex items-center space-x-2">
          <span>
            Viewing Page <strong className="text-white">{currentPage?.page}</strong> of{' '}
            <strong className="text-white">{totalPages}</strong>
          </span>
          <span className="text-slate-600">&bull;</span>
          <span>{currentPage?.orig_word_count || 0} ground truth words</span>
        </div>
        <span className="text-[10px] text-slate-500">
          Click any page or use Prev/Next to inspect
        </span>
      </div>
    </div>
  );
};
