import React from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  Info,
  CheckCircle2,
  ArrowRight,
  Hash,
  Type,
  FileMinus,
  FilePlus,
  Repeat,
  Binary,
} from 'lucide-react';
import { MismatchItem, SeverityLevel, DifferenceType } from '../../types/originality';

interface MismatchDetailsProps {
  mismatches: MismatchItem[];
  pageNumber: number;
}

export const MismatchDetails: React.FC<MismatchDetailsProps> = ({ mismatches, pageNumber }) => {
  const getSeverityBadge = (sev: SeverityLevel) => {
    switch (sev) {
      case 'HIGH':
        return {
          bg: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
          label: 'HIGH SEVERITY',
        };
      case 'MEDIUM':
        return {
          bg: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
          label: 'MEDIUM SEVERITY',
        };
      case 'LOW':
        return {
          bg: 'bg-blue-500/20 text-blue-300 border-blue-500/40',
          label: 'LOW SEVERITY',
        };
    }
  };

  const getTypeIcon = (type: DifferenceType) => {
    switch (type) {
      case 'NUMBER_MISMATCH':
        return <Binary className="w-3.5 h-3.5 text-rose-400" />;
      case 'MISSING_TEXT':
        return <FileMinus className="w-3.5 h-3.5 text-rose-400" />;
      case 'EXTRA_TEXT':
        return <FilePlus className="w-3.5 h-3.5 text-emerald-400" />;
      case 'CHARACTER_MISMATCH':
        return <Type className="w-3.5 h-3.5 text-amber-400" />;
      case 'READING_ORDER':
        return <Repeat className="w-3.5 h-3.5 text-indigo-400" />;
      default:
        return <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />;
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col h-[650px]">
      {/* Header */}
      <div className="bg-slate-950 border-b border-slate-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider">
            Detected Mismatches ({mismatches.length})
          </h4>
          <span className="text-[11px] text-slate-400 font-mono">
            Page {pageNumber}
          </span>
        </div>
        <span className="text-[10px] text-slate-400">
          Ranked by Severity
        </span>
      </div>

      {/* Mismatches List */}
      <div className="flex-1 overflow-auto p-4 space-y-3 bg-slate-900/60">
        {mismatches.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-400 opacity-60" />
            <p className="text-sm font-medium text-slate-300">
              No mismatches detected on this page.
            </p>
            <p className="text-xs text-slate-500">
              All words, numbers, and characters match the original document.
            </p>
          </div>
        ) : (
          mismatches.map((m, idx) => {
            const sevInfo = getSeverityBadge(m.severity);
            const TypeIcon = getTypeIcon(m.diff_type);

            return (
              <div
                key={m.id || idx}
                className={`p-3.5 rounded-xl border transition-all ${
                  m.severity === 'HIGH'
                    ? 'bg-rose-950/20 border-rose-500/40 shadow-sm'
                    : m.severity === 'MEDIUM'
                    ? 'bg-amber-950/20 border-amber-500/40'
                    : 'bg-slate-950 border-slate-800'
                }`}
              >
                {/* Header row: Location, Type, Severity */}
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2 pb-2 border-b border-slate-800/80">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-mono font-bold text-slate-200">
                      {m.location}
                    </span>
                    <span className="flex items-center space-x-1 text-[11px] text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded-md font-medium">
                      {TypeIcon}
                      <span className="capitalize">{m.diff_type.replace('_', ' ').toLowerCase()}</span>
                    </span>
                  </div>

                  <div className="flex items-center space-x-2">
                    <span
                      className={`text-[9px] px-2 py-0.5 rounded-full font-bold border ${sevInfo.bg}`}
                    >
                      {sevInfo.label}
                    </span>
                  </div>
                </div>

                {/* Diff Callout */}
                <div className="flex items-center space-x-2 text-xs font-mono mb-2.5 bg-slate-950 p-2 rounded-lg border border-slate-800">
                  <span className="text-slate-400 font-sans text-[11px]">Difference:</span>
                  <span className="text-amber-300 font-bold tracking-wide">
                    {m.difference}
                  </span>
                </div>

                {/* Side-by-side snippet preview */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <div className="bg-rose-950/30 border border-rose-900/40 rounded-lg p-2">
                    <span className="text-[10px] uppercase font-bold text-rose-400 tracking-wider block mb-1">
                      Original
                    </span>
                    <p className="text-slate-200 font-sans leading-relaxed select-text">
                      {m.orig_text || <span className="text-slate-500 italic">(none)</span>}
                    </p>
                  </div>

                  <div className="bg-amber-950/30 border border-amber-900/40 rounded-lg p-2">
                    <span className="text-[10px] uppercase font-bold text-amber-400 tracking-wider block mb-1">
                      Extracted
                    </span>
                    <p className="text-slate-200 font-sans leading-relaxed select-text">
                      {m.extracted_text || <span className="text-slate-500 italic">(none)</span>}
                    </p>
                  </div>
                </div>

                {/* Character-Level Breakdown if available */}
                {m.char_diffs && m.char_diffs.length > 0 && (
                  <div className="mt-2.5 pt-2 border-t border-slate-800/80">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">
                      Character-Level OCR Analysis:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {m.char_diffs.map((cd, cdIdx) => (
                        <span
                          key={cdIdx}
                          className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/30 text-indigo-300"
                        >
                          {cd.diff_type === 'missing_char' && `Missing '${cd.char}' at pos ${cd.position}`}
                          {cd.diff_type === 'extra_char' && `Extra '${cd.char}' at pos ${cd.position}`}
                          {cd.diff_type === 'changed_char' && `Changed '${cd.char}' at pos ${cd.position}`}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
