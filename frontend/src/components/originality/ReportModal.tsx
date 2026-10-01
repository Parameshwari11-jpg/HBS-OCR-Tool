import React from 'react';
import {
  X,
  FileDown,
  FileText,
  FileCode,
  FileSpreadsheet,
  ShieldCheck,
  AlertTriangle,
  XCircle,
  Check,
} from 'lucide-react';
import { OriginalityReport } from '../../types/originality';
import { getReportPdfUrl, getReportJsonUrl, getReportCsvUrl } from '../../api/originalityApi';

interface ReportModalProps {
  report: OriginalityReport;
  isOpen: boolean;
  onClose: () => void;
}

export const ReportModal: React.FC<ReportModalProps> = ({ report, isOpen, onClose }) => {
  if (!isOpen) return null;

  const download = (url: string) => {
    window.open(url, '_blank');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-2xl w-full p-6 shadow-2xl space-y-6 relative max-h-[90vh] overflow-y-auto">
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400">
              <FileDown className="w-5 h-5" />
            </span>
            <h3 className="text-xl font-bold text-white tracking-wide">
              Extraction Accuracy Report
            </h3>
          </div>
          <p className="text-xs text-slate-400">
            Professional audit report comparing original document against extracted text.
          </p>
        </div>

        {/* Report Overview Box */}
        <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 space-y-3">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <span className="text-xs text-slate-400 block">Overall Extraction Accuracy</span>
              <span className="text-3xl font-black text-white">{report.overall_accuracy}%</span>
            </div>
            <div className={`px-4 py-1.5 rounded-full text-xs font-bold border ${
              report.verification_status === 'PASS'
                ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300'
                : report.verification_status === 'WARNING'
                ? 'bg-amber-500/15 border-amber-500/40 text-amber-300'
                : 'bg-rose-500/15 border-rose-500/40 text-rose-300'
            }`}>
              VERIFICATION STATUS: {report.verification_status}
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Original File</span>
              <span className="text-slate-200 font-medium truncate block">{report.original_filename}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Extracted File</span>
              <span className="text-slate-200 font-medium truncate block">{report.extracted_filename}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Pages Audited</span>
              <span className="text-slate-200 font-medium">{report.total_pages} pages</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-bold">Timestamp</span>
              <span className="text-slate-200 font-medium">{report.timestamp}</span>
            </div>
          </div>
        </div>

        {/* Metrics Summary Table */}
        <div className="space-y-2">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
            Verification Metrics Summary
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80">
              <span className="text-slate-400 text-[11px] block">Passed Pages</span>
              <span className="text-base font-bold text-emerald-400">{report.passed_pages}</span>
            </div>
            <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80">
              <span className="text-slate-400 text-[11px] block">Warning Pages</span>
              <span className="text-base font-bold text-amber-400">{report.warning_pages}</span>
            </div>
            <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80">
              <span className="text-slate-400 text-[11px] block">Error Pages</span>
              <span className="text-base font-bold text-rose-400">{report.error_pages}</span>
            </div>
            <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80">
              <span className="text-slate-400 text-[11px] block">Number Errors</span>
              <span className={`text-base font-bold ${report.number_mismatches > 0 ? 'text-rose-400' : 'text-slate-200'}`}>
                {report.number_mismatches}
              </span>
            </div>
          </div>
        </div>

        {/* Export Buttons */}
        <div className="space-y-3 pt-2">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
            Choose Export Format
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <button
              type="button"
              onClick={() => download(getReportPdfUrl(report.report_id))}
              className="p-4 rounded-2xl bg-gradient-to-br from-rose-950/40 to-slate-900 border border-rose-500/30 hover:border-rose-500/60 transition flex flex-col items-center justify-center space-y-2 group cursor-pointer shadow-lg"
            >
              <FileText className="w-6 h-6 text-rose-400 group-hover:scale-110 transition-transform" />
              <div className="text-center">
                <span className="text-xs font-bold text-white block">PDF Report</span>
                <span className="text-[10px] text-slate-400">Official styled document</span>
              </div>
            </button>

            <button
              type="button"
              onClick={() => download(getReportJsonUrl(report.report_id))}
              className="p-4 rounded-2xl bg-gradient-to-br from-amber-950/40 to-slate-900 border border-amber-500/30 hover:border-amber-500/60 transition flex flex-col items-center justify-center space-y-2 group cursor-pointer shadow-lg"
            >
              <FileCode className="w-6 h-6 text-amber-400 group-hover:scale-110 transition-transform" />
              <div className="text-center">
                <span className="text-xs font-bold text-white block">JSON Report</span>
                <span className="text-[10px] text-slate-400">Machine-readable data</span>
              </div>
            </button>

            <button
              type="button"
              onClick={() => download(getReportCsvUrl(report.report_id))}
              className="p-4 rounded-2xl bg-gradient-to-br from-emerald-950/40 to-slate-900 border border-emerald-500/30 hover:border-emerald-500/60 transition flex flex-col items-center justify-center space-y-2 group cursor-pointer shadow-lg"
            >
              <FileSpreadsheet className="w-6 h-6 text-emerald-400 group-hover:scale-110 transition-transform" />
              <div className="text-center">
                <span className="text-xs font-bold text-white block">CSV Spreadsheet</span>
                <span className="text-[10px] text-slate-400">Detailed error inventory</span>
              </div>
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="pt-2 border-t border-slate-800 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
