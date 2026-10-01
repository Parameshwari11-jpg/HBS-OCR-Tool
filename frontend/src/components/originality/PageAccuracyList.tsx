import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, CheckCircle2, AlertTriangle, XCircle, Filter } from 'lucide-react';
import { PageOriginalityResult, StatusType } from '../../types/originality';

interface PageAccuracyListProps {
  pages: PageOriginalityResult[];
  selectedPageIndex: number;
  onSelectPage: (index: number) => void;
}

export const PageAccuracyList: React.FC<PageAccuracyListProps> = ({
  pages,
  selectedPageIndex,
  onSelectPage,
}) => {
  const [filter, setFilter] = useState<'all' | 'errors' | 'warnings' | 'passed'>('all');

  const filteredPages = pages.map((p, originalIdx) => ({ p, originalIdx })).filter(({ p }) => {
    if (filter === 'errors') return p.status === 'ERROR';
    if (filter === 'warnings') return p.status === 'WARNING';
    if (filter === 'passed') return p.status === 'PASS';
    return true;
  });

  const getStatusIcon = (status: StatusType) => {
    switch (status) {
      case 'PASS':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
      case 'WARNING':
        return <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />;
      case 'ERROR':
        return <XCircle className="w-3.5 h-3.5 text-rose-400" />;
    }
  };

  const getStatusBadgeClass = (status: StatusType, isSelected: boolean) => {
    if (isSelected) {
      return 'bg-indigo-600 border-indigo-400 text-white shadow-md shadow-indigo-600/30';
    }
    switch (status) {
      case 'PASS':
        return 'bg-slate-900 border-slate-800 text-slate-300 hover:border-emerald-500/50 hover:bg-emerald-950/20';
      case 'WARNING':
        return 'bg-slate-900 border-amber-500/40 text-amber-300 hover:bg-amber-950/30';
      case 'ERROR':
        return 'bg-slate-900 border-rose-500/50 text-rose-300 hover:bg-rose-950/30 ring-1 ring-rose-500/20';
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-xl space-y-3">
      {/* Top Header: Navigation Controls & Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider">
            Page-Wise Verification
          </h4>
          <span className="text-[11px] text-slate-400 font-mono">
            ({pages.length} total)
          </span>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-1 bg-slate-950 border border-slate-800 p-0.5 rounded-lg text-xs">
          <button
            type="button"
            onClick={() => setFilter('all')}
            className={`px-2 py-0.5 rounded transition cursor-pointer font-medium ${
              filter === 'all' ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All ({pages.length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('errors')}
            className={`px-2 py-0.5 rounded transition cursor-pointer font-medium ${
              filter === 'errors' ? 'bg-rose-900/60 text-rose-300 border border-rose-500/30' : 'text-rose-400/80 hover:text-rose-300'
            }`}
          >
            Errors ({pages.filter((p) => p.status === 'ERROR').length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('warnings')}
            className={`px-2 py-0.5 rounded transition cursor-pointer font-medium ${
              filter === 'warnings' ? 'bg-amber-900/60 text-amber-300 border border-amber-500/30' : 'text-amber-400/80 hover:text-amber-300'
            }`}
          >
            Warnings ({pages.filter((p) => p.status === 'WARNING').length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('passed')}
            className={`px-2 py-0.5 rounded transition cursor-pointer font-medium ${
              filter === 'passed' ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-500/30' : 'text-emerald-400/80 hover:text-emerald-300'
            }`}
          >
            Passed ({pages.filter((p) => p.status === 'PASS').length})
          </button>
        </div>

        {/* Stepper Navigation */}
        <div className="flex items-center space-x-1.5 bg-slate-950 border border-slate-800 rounded-lg p-0.5 text-xs">
          <button
            type="button"
            onClick={() => onSelectPage(Math.max(0, selectedPageIndex - 1))}
            disabled={selectedPageIndex <= 0}
            className="p-1 rounded text-slate-300 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition"
            title="Previous Page"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <span className="px-2 font-mono text-[11px] text-slate-300">
            Page {pages[selectedPageIndex]?.page || 1} of {pages.length}
          </span>
          <button
            type="button"
            onClick={() => onSelectPage(Math.min(pages.length - 1, selectedPageIndex + 1))}
            disabled={selectedPageIndex >= pages.length - 1}
            className="p-1 rounded text-slate-300 hover:text-white hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition"
            title="Next Page"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Horizontal Page Pills Scroll */}
      <div className="flex items-center space-x-2 overflow-x-auto no-scrollbar py-1">
        {filteredPages.map(({ p, originalIdx }) => {
          const isSelected = selectedPageIndex === originalIdx;
          const badgeClass = getStatusBadgeClass(p.status, isSelected);

          return (
            <button
              key={p.page}
              type="button"
              onClick={() => onSelectPage(originalIdx)}
              className={`px-3 py-1.5 rounded-xl border text-xs font-semibold flex items-center space-x-2 transition-all cursor-pointer whitespace-nowrap ${badgeClass}`}
            >
              {getStatusIcon(p.status)}
              <span>Page {p.page}</span>
              <span className="font-mono text-[10px] opacity-80">
                {p.accuracy}%
              </span>
              {p.mismatches.length > 0 && (
                <span
                  className={`text-[9px] px-1.5 py-0.2 rounded-full ${
                    isSelected
                      ? 'bg-white/20 text-white'
                      : p.status === 'ERROR'
                      ? 'bg-rose-500/20 text-rose-300'
                      : 'bg-amber-500/20 text-amber-300'
                  }`}
                >
                  {p.mismatches.length} {p.mismatches.length === 1 ? 'diff' : 'diffs'}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
