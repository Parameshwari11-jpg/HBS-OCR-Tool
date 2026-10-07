import React, { useState } from 'react';
import { Download, FileCode, FileText, Sparkles, Loader2, Check } from 'lucide-react';
import { getExportTxtUrl, getExportJsonUrl, injectPdfDirect } from '../api/extractionApi';

interface ExportButtonsProps {
  jobId: string;
  filename?: string;
}

export const ExportButtons: React.FC<ExportButtonsProps> = ({ jobId, filename }) => {
  const [isInjecting, setIsInjecting] = useState<boolean>(false);
  const [injectSuccess, setInjectSuccess] = useState<boolean>(false);

  const handleExportTxt = () => {
    window.location.href = getExportTxtUrl(jobId);
  };

  const handleExportJson = () => {
    window.location.href = getExportJsonUrl(jobId);
  };

  const handleInjectPdf = async () => {
    setIsInjecting(true);
    setInjectSuccess(false);
    try {
      const blob = await injectPdfDirect(jobId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const baseName = (filename || 'document').replace(/\.[^/.]+$/, '');
      a.download = `${baseName}_with_invisible_text.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      setInjectSuccess(true);
      setTimeout(() => setInjectSuccess(false), 4000);
    } catch (err: any) {
      alert(err.message || 'Failed to inject invisible layer');
    } finally {
      setIsInjecting(false);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2.5">
      {/* INJECT INVISIBLE TEXT LAYER BUTTON */}
      <button
        type="button"
        onClick={handleInjectPdf}
        disabled={isInjecting}
        className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center space-x-2 transition shadow-lg cursor-pointer border active:scale-95 ${
          injectSuccess
            ? 'bg-emerald-600 text-white border-emerald-500 shadow-emerald-950/40'
            : 'bg-gradient-to-r from-purple-600 via-indigo-600 to-violet-600 hover:from-purple-500 hover:to-violet-500 text-white border-purple-400/40 shadow-purple-950/40 hover:-translate-y-0.5'
        } disabled:opacity-50 disabled:cursor-not-allowed`}
        title="Inject extracted text as an invisible search/copy text layer behind all images in the PDF"
      >
        {isInjecting ? (
          <>
            <Loader2 className="w-4 h-4 text-white animate-spin" />
            <span>INJECTING...</span>
          </>
        ) : injectSuccess ? (
          <>
            <Check className="w-4 h-4 text-white" />
            <span>INJECTED &amp; DOWNLOADED!</span>
          </>
        ) : (
          <>
            <Sparkles className="w-4 h-4 text-amber-300" />
            <span>INJECT INVISIBLE LAYER</span>
          </>
        )}
      </button>

      <button
        type="button"
        onClick={handleExportTxt}
        className="px-4 py-2 rounded-xl bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-100 text-xs font-semibold flex items-center space-x-2 transition shadow-md cursor-pointer active:scale-95"
      >
        <FileText className="w-4 h-4 text-indigo-400" />
        <span>Export TXT</span>
      </button>

      <button
        type="button"
        onClick={handleExportJson}
        className="px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 text-white text-xs font-semibold flex items-center space-x-2 transition shadow-md shadow-indigo-500/20 cursor-pointer active:scale-95"
      >
        <FileCode className="w-4 h-4" />
        <span>Export JSON</span>
      </button>
    </div>
  );
};

