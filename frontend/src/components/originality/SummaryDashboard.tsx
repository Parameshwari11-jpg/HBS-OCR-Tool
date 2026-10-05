import React, { useState } from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  XCircle,
  FileDown,
  FileCode,
  FileSpreadsheet,
  FileText,
  Layers,
  Hash,
  Type,
  AlertOctagon,
  RefreshCw,
  ArrowLeft,
} from 'lucide-react';
import { OriginalityReport, StatusType } from '../../types/originality';
import { getReportPdfUrl, getReportJsonUrl, getReportCsvUrl } from '../../api/originalityApi';

interface SummaryDashboardProps {
  report: OriginalityReport;
  onReset: () => void;
  onOpenReportModal: () => void;
  onBackToExtractor?: () => void;
}

export const SummaryDashboard: React.FC<SummaryDashboardProps> = ({
  report,
  onReset,
  onOpenReportModal,
  onBackToExtractor,
}) => {
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);

  const getStatusBadge = (status: StatusType) => {
    switch (status) {
      case 'PASS':
        return {
          bg: 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300 ring-emerald-500/20',
          icon: ShieldCheck,
          label: 'PASS',
          subtext: 'High fidelity extraction',
        };
      case 'WARNING':
        return {
          bg: 'bg-amber-500/15 border-amber-500/40 text-amber-300 ring-amber-500/20',
          icon: AlertTriangle,
          label: 'WARNING',
          subtext: 'Minor discrepancies detected',
        };
      case 'ERROR':
        return {
          bg: 'bg-rose-500/15 border-rose-500/40 text-rose-300 ring-rose-500/20',
          icon: XCircle,
          label: 'ERROR',
          subtext: 'Significant differences or number errors',
        };
    }
  };

  const statusInfo = getStatusBadge(report.verification_status);
  const StatusIcon = statusInfo.icon;

  const handleDownload = (format: 'pdf' | 'json' | 'csv') => {
    setDownloadingFormat(format);
    let url = '';
    if (format === 'pdf') url = getReportPdfUrl(report.report_id);
    else if (format === 'json') url = getReportJsonUrl(report.report_id);
    else if (format === 'csv') url = getReportCsvUrl(report.report_id);

    window.open(url, '_blank');
    setTimeout(() => setDownloadingFormat(null), 1500);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-5">
      {/* Top Banner: Overall Accuracy Score & Status & Actions */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
        <div className="flex items-center space-x-4">
          {/* Circular/Gauge visual accuracy score */}
          <div className="relative flex items-center justify-center">
            <div className="w-20 h-20 rounded-2xl bg-slate-950 border border-slate-800 flex flex-col items-center justify-center shadow-inner">
              <span className="text-2xl font-black tracking-tight text-white">
                {report.overall_accuracy}%
              </span>
              <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">
                Accuracy
              </span>
            </div>
          </div>

          <div>
            <div className="flex items-center space-x-2.5">
              <h3 className="text-lg font-bold text-white tracking-wide">
                Originality Check Summary
              </h3>
              <div
                className={`px-3 py-1 rounded-full text-xs font-bold border flex items-center space-x-1.5 shadow-sm ring-1 ${statusInfo.bg}`}
              >
                <StatusIcon className="w-3.5 h-3.5" />
                <span>{statusInfo.label}</span>
              </div>
            </div>
            <p className="text-xs text-slate-400 mt-1 flex items-center space-x-2">
              <span>{statusInfo.subtext}</span>
              <span>•</span>
              <span className="font-mono text-slate-300">
                {report.original_filename} vs {report.extracted_filename}
              </span>
            </p>
          </div>
        </div>

        {/* Action Buttons: Generate Report & Reset */}
        <div className="flex items-center flex-wrap gap-2.5">
          <button
            type="button"
            onClick={onOpenReportModal}
            className="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold flex items-center space-x-2 transition shadow-lg shadow-indigo-600/30 cursor-pointer"
          >
            <FileDown className="w-4 h-4" />
            <span>Generate Report</span>
          </button>

          {/* Quick Direct Exports */}
          <div className="flex items-center space-x-1 bg-slate-950 border border-slate-800 rounded-xl p-1 text-xs">
            <button
              type="button"
              onClick={() => handleDownload('pdf')}
              title="Download PDF Report"
              className="p-1.5 hover:bg-slate-800 text-slate-300 hover:text-white rounded-lg transition cursor-pointer flex items-center space-x-1"
            >
              <FileText className="w-3.5 h-3.5 text-rose-400" />
              <span className="text-[11px] font-semibold">PDF</span>
            </button>
            <button
              type="button"
              onClick={() => handleDownload('json')}
              title="Download JSON Report"
              className="p-1.5 hover:bg-slate-800 text-slate-300 hover:text-white rounded-lg transition cursor-pointer flex items-center space-x-1"
            >
              <FileCode className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-[11px] font-semibold">JSON</span>
            </button>
            <button
              type="button"
              onClick={() => handleDownload('csv')}
              title="Download CSV Report"
              className="p-1.5 hover:bg-slate-800 text-slate-300 hover:text-white rounded-lg transition cursor-pointer flex items-center space-x-1"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-[11px] font-semibold">CSV</span>
            </button>
          </div>

          <button
            type="button"
            onClick={onReset}
            className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold flex items-center space-x-1.5 transition border border-slate-700 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>New Check</span>
          </button>

          {onBackToExtractor && (
            <button
              type="button"
              onClick={onBackToExtractor}
              className="px-3.5 py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 hover:text-white text-xs font-bold flex items-center space-x-1.5 transition border border-indigo-500/40 cursor-pointer shadow-sm group"
              title="Return to the Extracted Text of this document"
            >
              <ArrowLeft className="w-3.5 h-3.5 text-indigo-400 group-hover:-translate-x-0.5 transition-transform" />
              <span>Back to Extracted Text</span>
            </button>
          )}
        </div>
      </div>

      {/* KPI Tiles Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5">
        <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3 flex flex-col justify-between">
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
            Total Pages
          </span>
          <span className="text-xl font-black text-slate-100 mt-1">
            {report.total_pages}
          </span>
          <span className="text-[10px] text-slate-500 mt-0.5">Document units</span>
        </div>

        <div className="bg-emerald-950/20 border border-emerald-500/30 rounded-xl p-3 flex flex-col justify-between">
          <span className="text-[10px] uppercase font-bold text-emerald-400 tracking-wider">
            Passed
          </span>
          <span className="text-xl font-black text-emerald-300 mt-1">
            {report.passed_pages}
          </span>
          <span className="text-[10px] text-emerald-500/80 mt-0.5">&ge; 99% accuracy</span>
        </div>

        <div className="bg-amber-950/20 border border-amber-500/30 rounded-xl p-3 flex flex-col justify-between">
          <span className="text-[10px] uppercase font-bold text-amber-400 tracking-wider">
            Warnings
          </span>
          <span className="text-xl font-black text-amber-300 mt-1">
            {report.warning_pages}
          </span>
          <span className="text-[10px] text-amber-500/80 mt-0.5">95% - 98.9%</span>
        </div>

        <div className="bg-rose-950/20 border border-rose-500/30 rounded-xl p-3 flex flex-col justify-between">
          <span className="text-[10px] uppercase font-bold text-rose-400 tracking-wider">
            Errors
          </span>
          <span className="text-xl font-black text-rose-300 mt-1">
            {report.error_pages}
          </span>
          <span className="text-[10px] text-rose-500/80 mt-0.5">&lt; 95% / numbers</span>
        </div>

        <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3 flex flex-col justify-between">
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
            Missing Words
          </span>
          <span className="text-xl font-black text-rose-400 mt-1">
            {report.missing_words}
          </span>
          <span className="text-[10px] text-slate-500 mt-0.5">Omitted in text</span>
        </div>

        <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3 flex flex-col justify-between">
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
            Extra Words
          </span>
          <span className="text-xl font-black text-indigo-400 mt-1">
            {report.extra_words}
          </span>
          <span className="text-[10px] text-slate-500 mt-0.5">Unmatched added</span>
        </div>

        <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3 flex flex-col justify-between">
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
            Changed Words
          </span>
          <span className="text-xl font-black text-amber-400 mt-1">
            {report.changed_words}
          </span>
          <span className="text-[10px] text-slate-500 mt-0.5">Substituted terms</span>
        </div>

        <div className={`rounded-xl p-3 flex flex-col justify-between border ${
          report.number_mismatches > 0
            ? 'bg-rose-950/30 border-rose-500/50 shadow-sm shadow-rose-900/20'
            : 'bg-slate-950/80 border-slate-800/80'
        }`}>
          <div className="flex items-center space-x-1">
            <span className={`text-[10px] uppercase font-bold tracking-wider ${
              report.number_mismatches > 0 ? 'text-rose-400' : 'text-slate-400'
            }`}>
              Number Errors
            </span>
            {report.number_mismatches > 0 && <AlertOctagon className="w-3 h-3 text-rose-400 animate-pulse" />}
          </div>
          <span className={`text-xl font-black mt-1 ${
            report.number_mismatches > 0 ? 'text-rose-300' : 'text-slate-100'
          }`}>
            {report.number_mismatches}
          </span>
          <span className="text-[10px] text-slate-500 mt-0.5">High severity</span>
        </div>
      </div>

      {/* Summary Notes (if any notes or alerts) */}
      {report.summary_notes.length > 0 && (
        <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3 text-xs text-slate-300 flex flex-col space-y-1">
          {report.summary_notes.map((note, idx) => (
            <div key={idx} className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
              <span>{note}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
