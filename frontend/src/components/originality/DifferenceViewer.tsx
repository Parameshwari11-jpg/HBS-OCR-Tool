import React, { useState } from 'react';
import {
  Columns,
  AlignJustify,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Sparkles,
  Image as ImageIcon,
  Copy,
  Check,
  FileText,
  ChevronDown,
  ChevronUp,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { PageOriginalityResult, LineDiffItem } from '../../types/originality';
import { OriginalDocumentViewer } from './OriginalDocumentViewer';

export interface DifferenceViewerProps {
  pageResult: PageOriginalityResult;
  pages?: PageOriginalityResult[];
  selectedPageIndex?: number;
  onSelectPage?: (index: number) => void;
  originalFilename?: string;
  jobId?: string;
  reportId?: string;
  initialMode?: 'visual' | 'split' | 'unified';
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
}) => {
  const [viewLayout, setViewLayout] = useState<'visual' | 'split' | 'unified'>(initialMode);
  const [copied, setCopied] = useState<boolean>(false);
  const [expandedDiffs, setExpandedDiffs] = useState<Record<number, boolean>>({});
  const [allExpanded, setAllExpanded] = useState<boolean>(false);

  const allPagesList = pages && pages.length > 0 ? pages : [pageResult];

  const handleCopyExtracted = () => {
    const text = pageResult.extracted_lines.join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const toggleLineDiff = (idx: number) => {
    setExpandedDiffs((prev) => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  };

  const handleToggleExpandAll = () => {
    const nextState = !allExpanded;
    setAllExpanded(nextState);
    const newExpanded: Record<number, boolean> = {};
    pageResult.line_diffs.forEach((_, idx) => {
      newExpanded[idx] = nextState;
    });
    setExpandedDiffs(newExpanded);
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
              />
            </div>

            {/* Right: Extracted Text Content (Clean, Sequential, Accurate Display) */}
            <div className="h-full bg-slate-900 border border-slate-800 rounded-xl flex flex-col overflow-hidden shadow-inner">
              {/* Header with Word Count, Copy, and Expand All Diffs */}
              <div className="bg-slate-950/90 border-b border-slate-800 px-3 py-2 flex items-center justify-between shrink-0">
                <div className="flex items-center space-x-2">
                  <span className="p-1 rounded bg-indigo-500/10 text-indigo-400">
                    <FileText className="w-3.5 h-3.5" />
                  </span>
                  <span className="text-xs font-bold text-white">Extracted Text Content</span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    ({pageResult.extracted_word_count} words &bull; {pageResult.extracted_lines.length} lines)
                  </span>
                </div>

                <div className="flex items-center space-x-1.5">
                  <button
                    type="button"
                    onClick={handleToggleExpandAll}
                    className="px-2 py-1 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-[10px] font-medium flex items-center space-x-1 transition cursor-pointer"
                    title={allExpanded ? 'Collapse all diffs' : 'Expand all diffs'}
                  >
                    {allExpanded ? (
                      <>
                        <Minimize2 className="w-3 h-3 text-slate-400" />
                        <span>Collapse Diffs</span>
                      </>
                    ) : (
                      <>
                        <Maximize2 className="w-3 h-3 text-slate-400" />
                        <span>Expand Diffs</span>
                      </>
                    )}
                  </button>

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

              {/* Clean Extracted Text Lines Stream */}
              <div className="flex-1 overflow-auto p-3 space-y-1.5 bg-slate-950/70 font-mono text-xs select-text">
                {pageResult.line_diffs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-2">
                    <CheckCircle2 className="w-8 h-8 text-emerald-400 opacity-60" />
                    <p className="text-sm font-sans font-medium text-slate-300">
                      No differences detected.
                    </p>
                    <p className="text-xs font-sans text-slate-500">
                      Extracted text exactly mirrors the original document.
                    </p>
                  </div>
                ) : (
                  pageResult.line_diffs.map((ld, idx) => {
                    const isExpanded = expandedDiffs[idx] || allExpanded;

                    // 1. EXACT MATCH LINE
                    if (ld.tag === 'equal') {
                      return (
                        <div
                          key={idx}
                          className="flex items-start space-x-2.5 px-2.5 py-1.5 rounded-lg bg-slate-900/50 border border-slate-800/80 hover:border-slate-700/80 transition group"
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
                          key={idx}
                          className="rounded-lg border border-amber-500/30 bg-amber-950/15 overflow-hidden transition-all shadow-sm"
                        >
                          {/* Main Clean Extracted Line */}
                          <div
                            onClick={() => toggleLineDiff(idx)}
                            className="flex items-start space-x-2.5 px-2.5 py-1.5 hover:bg-amber-500/10 transition cursor-pointer select-text"
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

                            {/* Badge with click-to-expand chevron */}
                            <div className="flex items-center space-x-1 shrink-0 select-none pt-0.5">
                              <span className="text-[9px] font-sans font-semibold text-amber-300 bg-amber-500/20 border border-amber-500/30 px-1.5 py-0.2 rounded">
                                Diff
                              </span>
                              <button
                                type="button"
                                className="p-0.5 text-amber-400 hover:text-white rounded"
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

                          {/* Accordion Comparison with Original Ground Truth */}
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
                          key={idx}
                          className="flex items-start space-x-2.5 px-2.5 py-1.5 rounded-lg bg-emerald-950/20 border border-emerald-500/30 text-emerald-200"
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
                          key={idx}
                          className="flex items-start space-x-2.5 px-2.5 py-1 rounded bg-rose-950/20 border border-rose-500/30 text-rose-300 opacity-90"
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
                  })
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
