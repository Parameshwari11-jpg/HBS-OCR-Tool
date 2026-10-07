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
  FileCheck2,
  Sparkles,
  CheckCircle2,
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
          badge: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
          dot: 'bg-emerald-400',
          icon: ShieldCheck,
          label: 'PASS',
          subtext: 'High-Fidelity Extraction',
        };
      case 'WARNING':
        return {
          badge: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
          dot: 'bg-amber-400',
          icon: AlertTriangle,
          label: 'WARNING',
          subtext: 'Minor Discrepancies Detected',
        };
      case 'ERROR':
        return {
          badge: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
          dot: 'bg-rose-400',
          icon: XCircle,
          label: 'ERROR',
          subtext: 'Significant Differences / Number Errors',
        };
    }
  };

  const statusInfo = getStatusBadge(report.verification_status);

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
    <div className="bg-slate-900/90 border border-slate-800/90 rounded-2xl p-5 shadow-2xl backdrop-blur-sm space-y-5">
      {/* Header Banner: Clean Enterprise Title, File Pair, Accuracy Badge & Actions */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
        <div className="flex items-center space-x-4 min-w-0 flex-1">
          {/* Accuracy Percentage Pill Badge */}
          <div className="flex flex-col items-center justify-center bg-slate-950/80 border border-slate-800 rounded-xl px-4 py-2.5 shadow-inner min-w-[95px] shrink-0">
            <div className="flex items-baseline space-x-0.5">
              <span className="text-2xl font-black text-slate-100 tracking-tight">
                {report.overall_accuracy}
              </span>
              <span className="text-xs font-bold text-slate-400">%</span>
            </div>
            <span className="text-[9px] uppercase tracking-wider font-semibold text-slate-500 mt-0.5">
              Accuracy
            </span>
          </div>

          <div className="space-y-1 min-w-0 flex-1">
            <div className="flex items-center space-x-2.5">
              <h3 className="text-base font-bold text-white tracking-wide shrink-0">
                Originality Check Summary
              </h3>
              <div
                className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border flex items-center space-x-1.5 shrink-0 ${statusInfo.badge}`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${statusInfo.dot}`} />
                <span>{statusInfo.label}</span>
              </div>
            </div>

            <div className="flex items-center text-xs text-slate-400 gap-x-2 gap-y-1 min-w-0">
              <span className="text-slate-300 font-medium shrink-0">{statusInfo.subtext}</span>
              <span className="text-slate-600 shrink-0">•</span>
              <div className="flex items-center space-x-1.5 font-mono text-[11px] text-slate-400 bg-slate-950/60 px-2 py-0.5 rounded border border-slate-800/60 min-w-0 max-w-full">
                <span className="text-slate-300 truncate max-w-[130px] sm:max-w-[170px] md:max-w-[210px]" title={report.original_filename}>
                  {report.original_filename}
                </span>
                <span className="text-slate-600 shrink-0">&rarr;</span>
                <span className="text-indigo-300 truncate max-w-[130px] sm:max-w-[170px] md:max-w-[210px]" title={report.extracted_filename}>
                  {report.extracted_filename}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Action Toolbar - Always strictly non-wrapping on single row */}
        <div className="flex items-center flex-nowrap gap-2 shrink-0 self-end lg:self-center">
          {onBackToExtractor && (
            <button
              type="button"
              onClick={onBackToExtractor}
              className="px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-slate-300 hover:text-white text-xs font-semibold flex items-center space-x-1.5 transition border border-slate-700/70 cursor-pointer shadow-sm group shrink-0"
              title="Return to Extracted Text view"
            >
              <ArrowLeft className="w-3.5 h-3.5 text-slate-400 group-hover:-translate-x-0.5 transition-transform" />
              <span>Back to Text</span>
            </button>
          )}

          <button
            type="button"
            onClick={onReset}
            className="px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-slate-300 hover:text-white text-xs font-semibold flex items-center space-x-1.5 transition border border-slate-700/70 cursor-pointer shrink-0"
            title="Start a new originality comparison"
          >
            <RefreshCw className="w-3.5 h-3.5 text-slate-400" />
            <span>New Check</span>
          </button>

          {/* Quick Export Formats Dropdown Group */}
          <div className="flex items-center bg-slate-950/90 border border-slate-800/90 rounded-lg p-0.5 text-xs shrink-0">
            <button
              type="button"
              onClick={() => handleDownload('pdf')}
              title="Download PDF Report"
              className="px-2 py-1 hover:bg-slate-800 text-slate-300 hover:text-white rounded transition cursor-pointer flex items-center space-x-1 text-[11px] font-medium"
            >
              <FileText className="w-3.5 h-3.5 text-rose-400" />
              <span>PDF</span>
            </button>
            <button
              type="button"
              onClick={() => handleDownload('json')}
              title="Download JSON Data"
              className="px-2 py-1 hover:bg-slate-800 text-slate-300 hover:text-white rounded transition cursor-pointer flex items-center space-x-1 text-[11px] font-medium border-l border-slate-800/80"
            >
              <FileCode className="w-3.5 h-3.5 text-amber-400" />
              <span>JSON</span>
            </button>
            <button
              type="button"
              onClick={() => handleDownload('csv')}
              title="Download CSV Table"
              className="px-2 py-1 hover:bg-slate-800 text-slate-300 hover:text-white rounded transition cursor-pointer flex items-center space-x-1 text-[11px] font-medium border-l border-slate-800/80"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
              <span>CSV</span>
            </button>
          </div>

          <button
            type="button"
            onClick={onOpenReportModal}
            className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center space-x-1.5 transition shadow-md shadow-indigo-600/20 cursor-pointer active:scale-95 shrink-0"
          >
            <FileDown className="w-3.5 h-3.5" />
            <span>Full Report</span>
          </button>
        </div>
      </div>

      {/* Modern Refined Metric Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
        <div className="bg-slate-950/70 border border-slate-800/70 rounded-xl p-2.5 flex flex-col justify-between transition hover:border-slate-700">
          <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
            Total Pages
          </span>
          <span className="text-xl font-bold text-slate-100 mt-1">
            {report.total_pages}
          </span>
          <span className="text-[10px] text-slate-400 mt-0.5">Pages verified</span>
        </div>

        <div className="bg-slate-950/70 border border-slate-800/70 rounded-xl p-2.5 flex flex-col justify-between transition hover:border-emerald-500/30">
          <span className="text-[10px] uppercase font-semibold text-emerald-400 tracking-wider">
            Passed
          </span>
          <span className="text-xl font-bold text-emerald-300 mt-1">
            {report.passed_pages}
          </span>
          <span className="text-[10px] text-slate-400 mt-0.5">&ge; 99% match</span>
        </div>

        <div className="bg-slate-950/70 border border-slate-800/70 rounded-xl p-2.5 flex flex-col justify-between transition hover:border-amber-500/30">
          <span className="text-[10px] uppercase font-semibold text-amber-400 tracking-wider">
            Warnings
          </span>
          <span className="text-xl font-bold text-amber-300 mt-1">
            {report.warning_pages}
          </span>
          <span className="text-[10px] text-slate-400 mt-0.5">95% &ndash; 98.9%</span>
        </div>

        <div className="bg-slate-950/70 border border-slate-800/70 rounded-xl p-2.5 flex flex-col justify-between transition hover:border-rose-500/30">
          <span className="text-[10px] uppercase font-semibold text-rose-400 tracking-wider">
            Errors
          </span>
          <span className="text-xl font-bold text-rose-300 mt-1">
            {report.error_pages}
          </span>
          <span className="text-[10px] text-slate-400 mt-0.5">&lt; 95% match</span>
        </div>

        <div className="bg-slate-950/70 border border-slate-800/70 rounded-xl p-2.5 flex flex-col justify-between transition hover:border-slate-700">
          <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
            Missing Words
          </span>
          <span className={`text-xl font-bold mt-1 ${report.missing_words > 0 ? 'text-rose-400' : 'text-slate-200'}`}>
            {report.missing_words}
          </span>
          <span className="text-[10px] text-slate-400 mt-0.5">Omitted in text</span>
        </div>

        <div className="bg-slate-950/70 border border-slate-800/70 rounded-xl p-2.5 flex flex-col justify-between transition hover:border-slate-700">
          <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
            Extra Words
          </span>
          <span className={`text-xl font-bold mt-1 ${report.extra_words > 0 ? 'text-indigo-400' : 'text-slate-200'}`}>
            {report.extra_words}
          </span>
          <span className="text-[10px] text-slate-400 mt-0.5">Unmatched added</span>
        </div>

        <div className="bg-slate-950/70 border border-slate-800/70 rounded-xl p-2.5 flex flex-col justify-between transition hover:border-slate-700">
          <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
            Changed Words
          </span>
          <span className={`text-xl font-bold mt-1 ${report.changed_words > 0 ? 'text-amber-400' : 'text-slate-200'}`}>
            {report.changed_words}
          </span>
          <span className="text-[10px] text-slate-400 mt-0.5">Substituted terms</span>
        </div>

        <div className={`rounded-xl p-2.5 flex flex-col justify-between border transition ${
          report.number_mismatches > 0
            ? 'bg-rose-950/20 border-rose-500/40 text-rose-300'
            : 'bg-slate-950/70 border-slate-800/70'
        }`}>
          <div className="flex items-center space-x-1">
            <span className={`text-[10px] uppercase font-semibold tracking-wider ${
              report.number_mismatches > 0 ? 'text-rose-400' : 'text-slate-400'
            }`}>
              Number Errors
            </span>
            {report.number_mismatches > 0 && <AlertOctagon className="w-3 h-3 text-rose-400" />}
          </div>
          <span className={`text-xl font-bold mt-1 ${
            report.number_mismatches > 0 ? 'text-rose-300' : 'text-slate-100'
          }`}>
            {report.number_mismatches}
          </span>
          <span className="text-[10px] text-slate-400 mt-0.5">Numeric shifts</span>
        </div>
      </div>

      {/* Summary Notes Bar */}
      {report.summary_notes.length > 0 && (
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 text-xs text-slate-300 flex flex-col space-y-1">
          {report.summary_notes.map((note, idx) => (
            <div key={idx} className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
              <span>{note}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

