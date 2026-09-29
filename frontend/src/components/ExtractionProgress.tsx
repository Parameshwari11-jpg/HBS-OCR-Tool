import React, { useState, useEffect } from 'react';
import { Loader2, CheckCircle2, Clock, FileText } from 'lucide-react';
import { ExtractionJobStatus } from '../types/extraction';

interface ExtractionProgressProps {
  status: ExtractionJobStatus;
}

const STAGE_LABELS: Record<string, string> = {
  uploading: 'Uploading document to extraction server...',
  converting: 'Converting Word document to preserve exact visual layout...',
  parsing: 'Parsing document structure & pages...',
  native_extraction: 'Extracting digital text, fonts & formatting...',
  page_processing: 'Extracting pages, text, formulas & visual elements...',
  rendering: 'Rendering high-fidelity preview canvases...',
  ocr: 'Running PaddleOCR engine on image content...',
  structure_analysis: 'Analyzing layout structure & formulas...',
  layout_analysis: 'Detecting spatial overlaps & relations...',
  duplicate_detection: 'Filtering redundant text & duplicates...',
  finalizing: 'Assembling reading order & formatting output...',
  completed: 'Extraction complete!',
  failed: 'Extraction failed.',
};

export const ExtractionProgress: React.FC<ExtractionProgressProps> = ({ status }) => {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatElapsed = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const remainingSecs = sec % 60;
    return `${mins.toString().padStart(2, '0')}:${remainingSecs.toString().padStart(2, '0')}`;
  };

  const stageName = status.stage_message || STAGE_LABELS[status.stage] || status.stage || 'Processing document...';

  // Pipeline step status helpers
  const getStepStatus = (minProgress: number, maxProgress: number) => {
    if (status.progress >= maxProgress) return 'done';
    if (status.progress >= minProgress) return 'active';
    return 'pending';
  };

  const steps = [
    { label: 'Upload & Layout', status: getStepStatus(0, 20) },
    { label: 'Native Text & Tables', status: getStepStatus(20, 50) },
    { label: 'OCR & MathType', status: getStepStatus(50, 85) },
    { label: 'Reading Order', status: getStepStatus(85, 100) },
  ];

  return (
    <div className="w-full max-w-4xl mx-auto bg-slate-900/90 backdrop-blur-md border border-indigo-500/30 rounded-2xl p-6 shadow-2xl space-y-5 animate-fadeIn">
      {/* Header with Title, Status & Timer */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3.5">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/30">
            <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
            <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-indigo-500"></span>
            </span>
          </div>

          <div>
            <div className="flex items-center space-x-2">
              <h4 className="text-sm font-bold text-white tracking-wide">Text Extractor Tool</h4>
              {status.file_type && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-slate-800 text-slate-300 border border-slate-700">
                  {status.file_type}
                </span>
              )}
            </div>
            <p className="text-xs text-indigo-300 font-medium mt-0.5 flex items-center space-x-1.5">
              <span>{stageName}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {/* Real-time Elapsed Timer */}
          <div className="hidden sm:flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-xs text-slate-300">
            <Clock className="w-3.5 h-3.5 text-indigo-400" />
            <span className="font-mono text-indigo-200">{formatElapsed(elapsedSeconds)}</span>
          </div>

          {/* Current Page Indicator if multi-page */}
          {status.current_page && status.total_pages && (
            <div className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-xs font-semibold text-indigo-300">
              <FileText className="w-3.5 h-3.5" />
              <span>Page {status.current_page} of {status.total_pages}</span>
            </div>
          )}

          {/* Percentage */}
          <div className="text-right">
            <span className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-cyan-300 to-emerald-400">
              {Math.min(100, Math.max(5, status.progress))}%
            </span>
          </div>
        </div>
      </div>

      {/* Main Glowing Progress Bar */}
      <div className="space-y-1.5">
        <div className="w-full bg-slate-950/80 rounded-full h-3.5 p-0.5 border border-slate-800 overflow-hidden shadow-inner">
          <div
            className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-cyan-400 to-emerald-400 transition-all duration-500 ease-out shadow-lg shadow-indigo-500/20"
            style={{ width: `${Math.min(100, Math.max(5, status.progress))}%` }}
          />
        </div>
        <div className="flex justify-between items-center text-[11px] text-slate-400 px-1">
          <span>{status.filename || 'Document'}</span>
          <span>
            {status.progress < 100 ? 'Processing document layers & formulas...' : 'Ready! Rendering results...'}
          </span>
        </div>
      </div>

      {/* 4 Pipeline Milestones */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-3 border-t border-slate-800/80 text-xs">
        {steps.map((step, idx) => (
          <div
            key={idx}
            className={`flex items-center space-x-2 p-2 rounded-xl transition-colors border ${
              step.status === 'done'
                ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-300 font-medium'
                : step.status === 'active'
                ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-200 font-semibold'
                : 'bg-slate-950/40 border-slate-800/40 text-slate-500'
            }`}
          >
            {step.status === 'done' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            ) : step.status === 'active' ? (
              <Loader2 className="w-4 h-4 text-indigo-400 animate-spin flex-shrink-0" />
            ) : (
              <div className="w-4 h-4 rounded-full border border-slate-700 flex-shrink-0" />
            )}
            <span className="truncate">{step.label}</span>
          </div>
        ))}
      </div>

      {/* Reassurance Footer Tip */}
      <div className="flex items-center space-x-2 pt-1 text-[11px] text-slate-400/90 italic">
        <span>
          Extracting normal text, textboxes, MathType equations, tables, and images while preserving 100% original visual layout.
        </span>
      </div>
    </div>
  );
};
