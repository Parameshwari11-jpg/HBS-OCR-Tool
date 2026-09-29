import React from 'react';
import { Cpu } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
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
                Extract text from PDF and Word documents, including text inside images and layered content.
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2 text-xs font-medium bg-slate-800/80 border border-slate-700/60 rounded-full px-3 py-1.5 text-slate-300">
            <Cpu className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
            <span>PaddleOCR & PP-StructureV3</span>
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          </div>
        </div>
      </div>
    </header>
  );
};
