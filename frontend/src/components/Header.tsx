import React from 'react';
import { Cpu, FileText, ShieldCheck } from 'lucide-react';

interface HeaderProps {
  activeView?: 'extractor' | 'originality';
  onNavigate?: (view: 'extractor' | 'originality') => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeView = 'extractor',
  onNavigate,
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
              <h1 className="text-xl sm:text-2xl font-bold bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                Text Extractor Tool
              </h1>
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
                  onClick={() => onNavigate('originality')}
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

            {/* Engine Status pill */}
            <div className="hidden sm:flex items-center space-x-2 text-xs font-medium bg-slate-800/80 border border-slate-700/60 rounded-full px-3 py-1.5 text-slate-300">
              <Cpu className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
              <span>PaddleOCR & PP-Structure</span>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
