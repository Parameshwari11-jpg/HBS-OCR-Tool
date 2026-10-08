import React, { useState, useRef } from 'react';
import { UploadCloud, File, X, AlertCircle, Play, FileType, Globe } from 'lucide-react';
import { SUPPORTED_LANGUAGES } from '../config/languages';

interface UploadAreaProps {
  onFileSelect: (file: File) => void;
  onExtract: () => void;
  selectedFile: File | null;
  onRemoveFile: () => void;
  isLoading: boolean;
  selectedLanguage: string;
  onLanguageChange: (lang: string) => void;
}

export const UploadArea: React.FC<UploadAreaProps> = ({
  onFileSelect,
  onExtract,
  selectedFile,
  onRemoveFile,
  isLoading,
  selectedLanguage,
  onLanguageChange,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateAndSelect = (file: File) => {
    setErrorMsg(null);
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext !== 'pdf' && ext !== 'docx') {
      setErrorMsg('Unsupported file type. Please upload a PDF or DOCX file.');
      return;
    }
    onFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSelect(e.target.files[0]);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const canExtract = !!selectedFile && !!selectedLanguage && !isLoading;

  const handleExtractClick = () => {
    if (!selectedLanguage) {
      // Defensive: button is disabled, but guard just in case
      return;
    }
    onExtract();
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-4">
      {errorMsg && (
        <div className="flex items-center space-x-3 p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400" />
          <span>{errorMsg}</span>
        </div>
      )}

      {!selectedFile ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-300 ${
            isDragging
              ? 'border-indigo-500 bg-indigo-500/10 scale-[1.01]'
              : 'border-slate-800 bg-slate-900/50 hover:border-slate-700 hover:bg-slate-900/80'
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".pdf,.docx"
            className="hidden"
          />

          <div className="mx-auto w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-4 text-indigo-400 shadow-inner">
            <UploadCloud className="w-8 h-8 animate-bounce" />
          </div>

          <h3 className="text-lg font-semibold text-white mb-1">
            Drag &amp; Drop your document here
          </h3>
          <p className="text-sm text-slate-400 mb-4">
            Supported formats: <span className="font-semibold text-indigo-400">PDF (.pdf)</span> or <span className="font-semibold text-cyan-400">Word (.docx)</span>
          </p>

          <button
            type="button"
            className="inline-flex items-center px-4 py-2 rounded-xl bg-slate-800 text-sm font-medium text-slate-200 border border-slate-700 hover:bg-slate-700 transition"
          >
            <FileType className="w-4 h-4 mr-2 text-indigo-400" />
            Browse Files
          </button>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          {/* File info row */}
          <div className="flex items-center justify-between p-4 bg-slate-950/60 rounded-xl border border-slate-800/80">
            <div className="flex items-center space-x-4 min-w-0">
              <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 flex-shrink-0">
                <File className="w-6 h-6" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-100 truncate">{selectedFile.name}</p>
                <p className="text-xs text-slate-400 mt-0.5">{formatFileSize(selectedFile.size)}</p>
              </div>
            </div>

            <button
              onClick={onRemoveFile}
              disabled={isLoading}
              className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
              title="Remove File"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Language selection — mandatory */}
          <div className="space-y-1.5">
            <label
              htmlFor="language-select"
              className="flex items-center space-x-1.5 text-xs font-semibold text-slate-300 uppercase tracking-wider"
            >
              <Globe className="w-3.5 h-3.5 text-indigo-400" />
              <span>Document Language <span className="text-rose-400 ml-0.5">*</span></span>
            </label>

            <div className="relative">
              <select
                id="language-select"
                value={selectedLanguage}
                onChange={(e) => onLanguageChange(e.target.value)}
                disabled={isLoading}
                className={`w-full appearance-none pl-4 pr-10 py-3 rounded-xl border text-sm font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/60 ${
                  isLoading
                    ? 'bg-slate-800 border-slate-700 text-slate-500 cursor-not-allowed'
                    : selectedLanguage
                    ? 'bg-slate-800 border-indigo-500/50 text-slate-100 cursor-pointer hover:border-indigo-400'
                    : 'bg-slate-800 border-amber-500/50 text-slate-400 cursor-pointer hover:border-amber-400'
                }`}
              >
                <option value="" disabled>Select document language…</option>
                {SUPPORTED_LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.label}
                  </option>
                ))}
              </select>

              {/* Custom chevron */}
              <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>

            {/* Inline hint when no language is selected */}
            {!selectedLanguage && !isLoading && (
              <p className="flex items-center space-x-1.5 text-xs text-amber-400/90 mt-1">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                <span>Please select the document language before extracting text.</span>
              </p>
            )}
          </div>

          {/* Extract button */}
          <button
            id="extract-btn"
            onClick={handleExtractClick}
            disabled={!canExtract}
            title={
              !selectedLanguage
                ? 'Please select the document language before extracting text.'
                : isLoading
                ? 'Extraction in progress…'
                : 'Extract text from document'
            }
            className={`w-full py-3.5 px-6 rounded-xl font-semibold text-white flex items-center justify-center space-x-2 shadow-lg transition-all duration-200 ${
              !canExtract
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed opacity-60'
                : 'bg-gradient-to-r from-indigo-600 via-indigo-500 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 shadow-indigo-500/25 cursor-pointer active:scale-[0.99]'
            }`}
          >
            <Play className="w-5 h-5 fill-current" />
            <span>{isLoading ? 'Extracting Content…' : 'Extract Text'}</span>
          </button>
        </div>
      )}
    </div>
  );
};
