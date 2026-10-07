import React from 'react';
import { Cpu, FileText, ShieldCheck, RefreshCw } from 'lucide-react';

interface HeaderProps {
  activeView?: 'extractor' | 'originality';
  onNavigate?: (view: 'extractor' | 'originality') => void;
  onCheckOriginalityClick?: () => void;
  onHardReload?: () => void;
  isReloading?: boolean;
  onNewExtraction?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeView = 'extractor',
  onNavigate,
  onCheckOriginalityClick,
  onHardReload,
  isReloading = false,
  onNewExtraction,
}) => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          {/* Logo & Title */}
          <div className="flex items-center space-x-3">
            <div className="h-11 w-11 rounded-xl overflow-hidden shadow-lg shadow-blue-500/20 border border-slate-700/60 bg-white flex items-center justify-center p-0.5">
              <img
                src="/logo.png"
                alt="Text Extractor Tool Logo"
                className="h-full w-full object-contain rounded-lg"
              />
            </div>
            <div>
              <div className="flex items-center space-x-2.5">
                <h1 className="text-xl sm:text-2xl font-bold bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                  Text Extractor Tool
                </h1>
                {onHardReload && (
                  <button
                    type="button"
                    onClick={onHardReload}
                    disabled={isReloading}
                    className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-amber-300 border border-slate-700/60 transition shadow-sm hover:border-amber-500/40 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed group relative"
                    title="Hard Reload / Re-Extract: Apply code changes and refresh extraction immediately without re-uploading"
                  >
                    <RefreshCw className={`w-4 h-4 transition-transform ${isReloading ? 'animate-spin text-amber-400' : 'group-hover:rotate-180 duration-500'}`} />
                  </button>
                )}
              </div>
              <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
                Universal Document Text Extraction & Accuracy Verification
              </p>
            </div>
          </div>

          {/* Navigation Controls: Extractor vs Check Originality */}
          <div className="flex items-center space-x-3">
            {onNavigate && (
              <div className="flex items-center p-1 bg-slate-950 border border-slate-800 rounded-xl text-xs font-semibold">
                <button
                  type="button"
                  onClick={() => onNavigate('extractor')}
                  className={`px-3 py-1.5 rounded-lg flex items-center space-x-1.5 transition cursor-pointer ${
                    activeView === 'extractor'
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Extract Document</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    if (onCheckOriginalityClick) {
                      onCheckOriginalityClick();
                    } else {
                      onNavigate('originality');
                    }
                  }}
                  className={`px-3 py-1.5 rounded-lg flex items-center space-x-1.5 transition cursor-pointer ${
                    activeView === 'originality'
                      ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-300" />
                  <span>Check Originality</span>
                </button>
              </div>
            )}

            {/* Top Right: New Extraction Button */}
            {onNewExtraction && (
              <button
                type="button"
                onClick={onNewExtraction}
                className="px-3.5 py-1.5 rounded-xl bg-slate-800/90 hover:bg-slate-700 text-slate-200 hover:text-white text-xs font-semibold flex items-center space-x-1.5 transition border border-slate-700 hover:border-slate-600 shadow-sm cursor-pointer transform hover:-translate-y-0.5 active:translate-y-0"
                title="Start a new document extraction"
              >
                <RefreshCw className="w-3.5 h-3.5 text-indigo-400" />
                <span>New Extraction</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
