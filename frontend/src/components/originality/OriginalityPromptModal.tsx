import React from 'react';
import { AlertCircle, X, CheckCircle2, FileText, ArrowRight } from 'lucide-react';

interface OriginalityPromptModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  onConfirmNewVerification?: () => void;
  filename?: string;
}

export const OriginalityPromptModal: React.FC<OriginalityPromptModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  onConfirmNewVerification,
  filename,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fadeIn">
      <div 
        className="relative w-full max-w-lg bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl shadow-indigo-950/50 p-6 space-y-5 animate-scaleUp text-slate-100"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-400">
              <AlertCircle className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
                Check Originality Verification?
              </h3>
              <p className="text-xs text-amber-400/90 font-medium mt-0.5">
                Two-File Verification Required
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition cursor-pointer"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Informative Body */}
        <div className="space-y-3.5 text-xs text-slate-300 bg-slate-950/70 p-4 rounded-xl border border-slate-800">
          <p className="leading-relaxed">
            Check Originality verifies your document by performing an exact ground-truth comparison:
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
            <div className="p-2.5 rounded-lg bg-slate-900/90 border border-blue-500/30 flex items-start space-x-2">
              <FileText className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-white block">1. Original File</span>
                <span className="text-[11px] text-slate-400">
                  {filename ? (
                    <span className="text-blue-300 font-mono truncate block max-w-[140px]" title={filename}>
                      {filename}
                    </span>
                  ) : (
                    'Original PDF / Word (.docx)'
                  )}
                </span>
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-900/90 border border-emerald-500/30 flex items-start space-x-2">
              <FileText className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-white block">2. Extracted Text File</span>
                <span className="text-[11px] text-slate-400">
                  Separate extracted <code className="text-emerald-300 font-mono">.txt</code> content
                </span>
              </div>
            </div>
          </div>

          <p className="text-[11px] text-slate-400 italic pt-1">
            Do you want to proceed to Check Originality with separate original and extracted text files?
          </p>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 pt-1">
          <button
            type="button"
            onClick={onClose}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white bg-slate-800/80 hover:bg-slate-700 transition cursor-pointer border border-slate-700/80 order-3 sm:order-1 text-center"
          >
            Cancel
          </button>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 order-1 sm:order-2">
            {onConfirmNewVerification && (
              <button
                type="button"
                onClick={() => {
                  onConfirmNewVerification();
                  onClose();
                }}
                className="px-3.5 py-2 rounded-xl text-xs font-bold text-indigo-300 hover:text-white bg-indigo-950/70 hover:bg-indigo-900 border border-indigo-700/60 transition cursor-pointer flex items-center justify-center space-x-1.5 shadow-md shadow-indigo-950/40"
                title="Upload a new original document and a separate extracted .txt file"
              >
                <span>Upload New Files</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => {
                onConfirm();
                onClose();
              }}
              className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 transition shadow-lg shadow-emerald-950/40 border border-emerald-400/40 cursor-pointer flex items-center justify-center space-x-1.5"
            >
              <span>{filename ? 'Check Current Document' : 'Proceed to Check'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
