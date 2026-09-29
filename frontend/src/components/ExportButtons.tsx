import React from 'react';
import { Download, FileCode, FileText } from 'lucide-react';
import { getExportTxtUrl, getExportJsonUrl } from '../api/extractionApi';

interface ExportButtonsProps {
  jobId: string;
}

export const ExportButtons: React.FC<ExportButtonsProps> = ({ jobId }) => {
  const handleExportTxt = () => {
    window.location.href = getExportTxtUrl(jobId);
  };

  const handleExportJson = () => {
    window.location.href = getExportJsonUrl(jobId);
  };

  return (
    <div className="flex items-center space-x-3">
      <button
        onClick={handleExportTxt}
        className="px-4 py-2 rounded-xl bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-100 text-xs font-semibold flex items-center space-x-2 transition shadow-md cursor-pointer active:scale-95"
      >
        <FileText className="w-4 h-4 text-indigo-400" />
        <span>Export TXT</span>
      </button>

      <button
        onClick={handleExportJson}
        className="px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 text-white text-xs font-semibold flex items-center space-x-2 transition shadow-md shadow-indigo-500/20 cursor-pointer active:scale-95"
      >
        <FileCode className="w-4 h-4" />
        <span>Export JSON</span>
      </button>
    </div>
  );
};
