import React, { useState, useEffect } from 'react';
import {
  FileText,
  FileCode,
  Upload,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  FileCheck,
  Sparkles,
  Loader2,
  ChevronLeft,
  X,
} from 'lucide-react';
import { OriginalityReport, DocumentMetadata } from '../types/originality';
import { checkOriginality, inspectMetadata } from '../api/originalityApi';
import { SummaryDashboard } from '../components/originality/SummaryDashboard';
import { PageAccuracyList } from '../components/originality/PageAccuracyList';
import { DifferenceViewer } from '../components/originality/DifferenceViewer';
import { MismatchDetails } from '../components/originality/MismatchDetails';
import { ReportModal } from '../components/originality/ReportModal';

interface OriginalityCheckProps {
  initialJobId?: string | null;
  initialOriginalFileName?: string | null;
  initialExtractedText?: string | null;
  onBackToExtractor?: () => void;
}

export const OriginalityCheck: React.FC<OriginalityCheckProps> = ({
  initialJobId,
  initialOriginalFileName,
  initialExtractedText,
  onBackToExtractor,
}) => {
  // File & Input State
  const [originalFile, setOriginalFile] = useState<File | null>(null);
  const [extractedFile, setExtractedFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(initialJobId || null);
  const [originalDocName, setOriginalDocName] = useState<string>(initialOriginalFileName || '');
  const [extractedText, setExtractedText] = useState<string>(initialExtractedText || '');
  const [originalMeta, setOriginalMeta] = useState<DocumentMetadata | null>(null);

  // Comparison State
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadingStep, setLoadingStep] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [report, setReport] = useState<OriginalityReport | null>(null);
  const [selectedPageIndex, setSelectedPageIndex] = useState<number>(0);
  const [isReportModalOpen, setIsReportModalOpen] = useState<boolean>(false);

  // Sync initial props
  useEffect(() => {
    if (initialJobId) setJobId(initialJobId);
    if (initialOriginalFileName) setOriginalDocName(initialOriginalFileName);
    if (initialExtractedText) setExtractedText(initialExtractedText);
  }, [initialJobId, initialOriginalFileName, initialExtractedText]);

  // Handle Original File Upload & Metadata Inspection
  const handleOriginalFileSelect = async (file: File) => {
    const ext = file.name.toLowerCase();
    if (!ext.endsWith('.pdf') && !ext.endsWith('.docx') && !ext.endsWith('.doc')) {
      setErrorMessage('Please select a valid PDF or Microsoft Word (.docx) file.');
      return;
    }

    setOriginalFile(file);
    setOriginalDocName(file.name);
    setJobId(null); // use the direct file upload
    setErrorMessage(null);

    try {
      const meta = await inspectMetadata(file);
      setOriginalMeta(meta);
    } catch (err) {
      console.warn('Could not inspect metadata:', err);
    }
  };

  // Handle Extracted Text File Upload (.txt)
  const handleExtractedFileSelect = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.txt') && !file.type.includes('text')) {
      setErrorMessage('Please upload a valid .txt extracted text file.');
      return;
    }

    setExtractedFile(file);
    setErrorMessage(null);
    try {
      const text = await file.text();
      setExtractedText(text);
    } catch (err) {
      setErrorMessage('Failed to read extracted text file.');
    }
  };

  // Calculate stats for extracted text
  const extractedLinesCount = extractedText ? extractedText.split('\n').filter((l) => l.trim()).length : 0;
  const extractedWordsCount = extractedText ? extractedText.split(/\s+/).filter(Boolean).length : 0;
  const extractedCharsCount = extractedText ? extractedText.length : 0;

  // Execute Comparison Check
  const handleStartCheck = async () => {
    if (!originalFile && !jobId) {
      setErrorMessage('Please provide an original PDF or Word document.');
      return;
    }
    if (!extractedText.trim() && !extractedFile) {
      setErrorMessage('Please provide the extracted text or upload a .txt file.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setLoadingStep('Initializing comparison engine...');

    try {
      setLoadingStep('Comparing content line-by-line and page-by-page...');

      const resultReport = await checkOriginality({
        originalFile,
        extractedFile,
        jobId,
        extractedText,
        originalFilename: originalDocName,
        extractedFilename: extractedFile?.name || `${originalDocName.replace(/\.[^/.]+$/, '')}_extracted.txt`,
      });

      setReport(resultReport);
      setSelectedPageIndex(0);
    } catch (err: any) {
      console.error('Originality comparison error:', err);
      setErrorMessage(err.message || 'An error occurred while verifying originality.');
    } finally {
      setIsLoading(false);
      setLoadingStep('');
    }
  };

  const handleReset = () => {
    setReport(null);
    setSelectedPageIndex(0);
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Subheader / Breadcrumbs */}
      <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur px-4 py-3">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            {onBackToExtractor && (
              <button
                type="button"
                onClick={onBackToExtractor}
                className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold flex items-center space-x-1 transition cursor-pointer"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Document Extractor</span>
              </button>
            )}
            <div className="flex items-center space-x-2">
              <span className="p-1 rounded-lg bg-indigo-500/20 text-indigo-400">
                <ShieldCheck className="w-4 h-4" />
              </span>
              <h2 className="text-sm font-bold text-white tracking-wide">
                Originality & Extraction Accuracy Verification
              </h2>
            </div>
          </div>

          {/* Workflow Stepper Indicator */}
          <div className="hidden md:flex items-center space-x-2 text-[11px] font-medium text-slate-400">
            <span className="text-slate-500">1. Extract</span>
            <span>&rarr;</span>
            <span className="text-indigo-400 font-bold bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/30">
              2. Check Originality
            </span>
            <span>&rarr;</span>
            <span className={report ? 'text-indigo-400 font-bold' : 'text-slate-500'}>
              3. Review Differences
            </span>
            <span>&rarr;</span>
            <span className={report ? 'text-indigo-400 font-bold' : 'text-slate-500'}>
              4. Generate Report
            </span>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Error Alert Message */}
        {errorMessage && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start space-x-3 text-rose-300 text-xs animate-shake">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-bold block mb-0.5">Verification Error</span>
              <p>{errorMessage}</p>
            </div>
            <button
              type="button"
              onClick={() => setErrorMessage(null)}
              className="text-rose-400 hover:text-white cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* STEP 1: Input Setup Cards (Always visible or collapsible after check) */}
        {!report ? (
          <div className="space-y-6 animate-fadeIn">
            {/* Introductory Hero Card */}
            <div className="bg-gradient-to-br from-indigo-950/40 via-slate-900 to-slate-950 border border-indigo-500/20 rounded-3xl p-6 sm:p-8 relative overflow-hidden shadow-2xl">
              <div className="max-w-3xl space-y-2">
                <div className="inline-flex items-center space-x-2 text-xs font-bold text-indigo-400 bg-indigo-500/10 border border-indigo-500/30 px-3 py-1 rounded-full uppercase tracking-wider">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Automated Quality & Originality Audit</span>
                </div>
                <h3 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
                  Verify Extraction Fidelity Against Original File
                </h3>
                <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
                  Perform an intelligent line-by-line, word-level, and character-level comparison between your
                  source document (PDF or Word) and the extracted text. Identify omitted content, number mismatches,
                  OCR hallucinations, and reading order anomalies with mathematically verified accuracy.
                </p>
              </div>
            </div>

            {/* Input Dual Section: Original File + Extracted Text */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left Box: Original File (PDF / DOCX) */}
              <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl flex flex-col justify-between space-y-4">
                <div>
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div className="flex items-center space-x-2">
                      <span className="p-1.5 rounded-lg bg-blue-500/20 text-blue-400">
                        <FileText className="w-4 h-4" />
                      </span>
                      <h4 className="text-sm font-bold text-white tracking-wide">
                        1. Original Document
                      </h4>
                    </div>
                    <span className="text-[10px] text-blue-300 font-mono bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                      PDF or DOCX
                    </span>
                  </div>

                  {originalDocName ? (
                    <div className="mt-4 p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3 overflow-hidden">
                          <span className="p-2 rounded-xl bg-blue-500/10 text-blue-400 shrink-0">
                            <FileCheck className="w-5 h-5" />
                          </span>
                          <div className="truncate">
                            <span className="text-xs font-bold text-white block truncate">
                              {originalDocName}
                            </span>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold">
                              {originalDocName.toLowerCase().endsWith('.pdf') ? 'PDF Document' : 'Word Document'}
                            </span>
                          </div>
                        </div>

                        <label className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 hover:underline cursor-pointer">
                          Change
                          <input
                            type="file"
                            accept=".pdf,.docx,.doc"
                            className="hidden"
                            onChange={(e) => {
                              if (e.target.files && e.target.files[0]) {
                                handleOriginalFileSelect(e.target.files[0]);
                              }
                            }}
                          />
                        </label>
                      </div>

                      {/* Metadata Stats */}
                      <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/80 text-[11px]">
                        <div>
                          <span className="text-slate-500 block">Pages / Sections:</span>
                          <span className="text-slate-200 font-semibold font-mono">
                            {originalMeta?.total_pages
                              ? `${originalMeta.total_pages} pages`
                              : originalMeta?.total_sections
                              ? `${originalMeta.total_sections} sections`
                              : 'Ready for inspection'}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Reference Source:</span>
                          <span className="text-emerald-400 font-medium">
                            {jobId ? 'Attached from extraction' : 'Local file'}
                          </span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    /* Dropzone when no file selected */
                    <label className="mt-4 border-2 border-dashed border-slate-800 hover:border-indigo-500/50 rounded-2xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition bg-slate-950/40 hover:bg-slate-950 group">
                      <input
                        type="file"
                        accept=".pdf,.docx,.doc"
                        className="hidden"
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            handleOriginalFileSelect(e.target.files[0]);
                          }
                        }}
                      />
                      <Upload className="w-8 h-8 text-slate-500 group-hover:text-indigo-400 transition mb-2" />
                      <span className="text-xs font-bold text-slate-200 block">
                        Click or drag & drop original document
                      </span>
                      <span className="text-[11px] text-slate-500 mt-1 block">
                        Supports PDF and Microsoft Word (.docx)
                      </span>
                    </label>
                  )}
                </div>

                <div className="text-[11px] text-slate-500 flex items-center space-x-1.5 pt-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
                  <span>Extracts textual blocks, tables, headers & footers for ground-truth comparison.</span>
                </div>
              </div>

              {/* Right Box: Extracted Text (.txt) */}
              <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl flex flex-col justify-between space-y-4">
                <div>
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div className="flex items-center space-x-2">
                      <span className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400">
                        <FileCode className="w-4 h-4" />
                      </span>
                      <h4 className="text-sm font-bold text-white tracking-wide">
                        2. Extracted Text Content
                      </h4>
                    </div>
                    <span className="text-[10px] text-indigo-300 font-mono bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                      .TXT Content
                    </span>
                  </div>

                  {extractedText ? (
                    <div className="mt-4 p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3 overflow-hidden">
                          <span className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 shrink-0">
                            <FileText className="w-5 h-5" />
                          </span>
                          <div className="truncate">
                            <span className="text-xs font-bold text-white block truncate">
                              {extractedFile?.name || (originalDocName ? `${originalDocName.replace(/\.[^/.]+$/, '')}.txt` : 'Extracted Text')}
                            </span>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold">
                              UTF-8 Plain Text
                            </span>
                          </div>
                        </div>

                        <label className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 hover:underline cursor-pointer">
                          Upload .TXT
                          <input
                            type="file"
                            accept=".txt,text/plain"
                            className="hidden"
                            onChange={(e) => {
                              if (e.target.files && e.target.files[0]) {
                                handleExtractedFileSelect(e.target.files[0]);
                              }
                            }}
                          />
                        </label>
                      </div>

                      {/* Text Statistics */}
                      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800/80 text-[11px]">
                        <div>
                          <span className="text-slate-500 block">Lines:</span>
                          <span className="text-slate-200 font-semibold font-mono">{extractedLinesCount}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Words:</span>
                          <span className="text-slate-200 font-semibold font-mono">{extractedWordsCount}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Characters:</span>
                          <span className="text-slate-200 font-semibold font-mono">{extractedCharsCount}</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    /* Dropzone when no extracted text */
                    <label className="mt-4 border-2 border-dashed border-slate-800 hover:border-indigo-500/50 rounded-2xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition bg-slate-950/40 hover:bg-slate-950 group">
                      <input
                        type="file"
                        accept=".txt,text/plain"
                        className="hidden"
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            handleExtractedFileSelect(e.target.files[0]);
                          }
                        }}
                      />
                      <Upload className="w-8 h-8 text-slate-500 group-hover:text-indigo-400 transition mb-2" />
                      <span className="text-xs font-bold text-slate-200 block">
                        Upload extracted .txt file
                      </span>
                      <span className="text-[11px] text-slate-500 mt-1 block">
                        Or verify current extraction directly
                      </span>
                    </label>
                  )}
                </div>

                <div className="text-[11px] text-slate-500 flex items-center space-x-1.5 pt-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
                  <span>Evaluates line breaks, numbers, case, punctuation, and character alignment.</span>
                </div>
              </div>
            </div>

            {/* Central Start Verification Action */}
            <div className="flex flex-col items-center justify-center pt-4">
              <button
                type="button"
                onClick={handleStartCheck}
                disabled={isLoading || (!originalDocName && !originalFile && !jobId) || !extractedText}
                className="px-8 py-4 rounded-2xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-sm flex items-center space-x-3 transition-all transform hover:-translate-y-0.5 active:translate-y-0 shadow-xl shadow-indigo-600/30 disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none cursor-pointer"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>{loadingStep || 'Comparing Documents...'}</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-5 h-5" />
                    <span>START ORIGINALITY CHECK</span>
                    <ArrowRight className="w-4 h-4 ml-1" />
                  </>
                )}
              </button>
              <p className="text-xs text-slate-500 mt-2 text-center">
                Performs deep character, word, and numeric verification across all pages.
              </p>
            </div>
          </div>
        ) : (
          /* STEP 2: Comprehensive Verification Results Dashboard */
          <div className="space-y-6 animate-fadeIn">
            {/* Top Summary Banner */}
            <SummaryDashboard
              report={report}
              onReset={handleReset}
              onOpenReportModal={() => setIsReportModalOpen(true)}
            />

            {/* Page-by-Page Selection List */}
            {report.pages.length > 0 && (
              <PageAccuracyList
                pages={report.pages}
                selectedPageIndex={selectedPageIndex}
                onSelectPage={setSelectedPageIndex}
              />
            )}

            {/* Main Interactive Dual Diff & Mismatch Details */}
            {report.pages[selectedPageIndex] && (
              <div className="space-y-6">
                {/* Visual Difference Viewer & Document Preview */}
                <DifferenceViewer
                  pageResult={report.pages[selectedPageIndex]}
                  pages={report.pages}
                  selectedPageIndex={selectedPageIndex}
                  onSelectPage={setSelectedPageIndex}
                  originalFilename={report.original_filename}
                  jobId={report.job_id || jobId || undefined}
                  reportId={report.report_id}
                />

                {/* Detailed Mismatch Cards */}
                <MismatchDetails
                  mismatches={report.pages[selectedPageIndex].mismatches}
                  pageNumber={report.pages[selectedPageIndex].page}
                />
              </div>
            )}
          </div>
        )}

        {/* Report Modal */}
        {report && (
          <ReportModal
            report={report}
            isOpen={isReportModalOpen}
            onClose={() => setIsReportModalOpen(false)}
          />
        )}
      </main>
    </div>
  );
};
