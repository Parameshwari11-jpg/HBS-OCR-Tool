import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Header } from '../components/Header';
import { UploadArea } from '../components/UploadArea';
import { ExtractionProgress } from '../components/ExtractionProgress';
import { Statistics } from '../components/Statistics';
import { PageViewer } from '../components/PageViewer';
import { ResultsTabs } from '../components/ResultsTabs';
import { ExportButtons } from '../components/ExportButtons';
import { uploadFile, startExtraction, getJobStatus, getJobResults, lookupJobResults } from '../api/extractionApi';
import { ExtractionJobStatus, ExtractionResult, ExtractedElement } from '../types/extraction';
import { ExtractorLoadRequest } from '../App';
import { AlertCircle, RefreshCw, FileText, FileCode, ShieldCheck } from 'lucide-react';

interface HomeProps {
  loadRequest?: ExtractorLoadRequest | null;
  onClearLoadRequest?: () => void;
  onNavigateToOriginality?: (jobId: string, filename: string, extractedText?: string) => void;
  onNavigate?: (view: 'extractor' | 'originality') => void;
}

export const Home: React.FC<HomeProps> = ({
  loadRequest,
  onClearLoadRequest,
  onNavigateToOriginality,
  onNavigate,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<ExtractionJobStatus | null>(null);
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedElement, setSelectedElement] = useState<ExtractedElement | null>(null);

  // Synchronized Scrolling and Page Navigation State
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [isSyncScroll, setIsSyncScroll] = useState(true);

  const leftContainerRef = useRef<HTMLDivElement | null>(null);
  const rightContainerRef = useRef<HTMLDivElement | null>(null);
  const leftPageRefs = useRef<(HTMLDivElement | null)[]>([]);
  const rightPageRefs = useRef<(HTMLDivElement | null)[]>([]);

  const activeScroller = useRef<'left' | 'right' | 'programmatic' | null>(null);
  const scrollLockTimeout = useRef<any>(null);

  // Restore previous extraction result from sessionStorage or server on mount if available
  useEffect(() => {
    if (!result && !jobId && !isLoading) {
      try {
        if (sessionStorage.getItem('new_upload_mode') === 'true') {
          return;
        }
        const savedJobId = sessionStorage.getItem('last_extraction_job_id');
        if (savedJobId) {
          getJobResults(savedJobId)
            .then((res) => {
              if (res && res.job_id) {
                setJobId(res.job_id);
                setResult(res);
              }
            })
            .catch(() => {
              sessionStorage.removeItem('last_extraction_job_id');
            });
        }
      } catch (e) {}
    }
  }, []);

  // Handle explicit request to load a specific document's extracted text OR trigger a fresh upload
  useEffect(() => {
    if (!loadRequest) return;

    // DIRECT NEW FILE UPLOAD: Reset state completely so user sees empty UploadArea
    if (loadRequest.action === 'new_upload') {
      setSelectedFile(null);
      setJobId(null);
      setJobStatus(null);
      setResult(null);
      setErrorMessage(null);
      setIsLoading(false);
      setCurrentPageIndex(0);
      leftPageRefs.current = [];
      rightPageRefs.current = [];
      try {
        sessionStorage.removeItem('last_extraction_job_id');
        sessionStorage.setItem('new_upload_mode', 'true');
      } catch (e) {}
      onClearLoadRequest?.();
      return;
    }

    try {
      sessionStorage.removeItem('new_upload_mode');
    } catch (e) {}

    // Check if currently displayed result already matches
    if (result) {
      const matchesJob = Boolean(loadRequest.jobId && result.job_id === loadRequest.jobId);
      const normalize = (s?: string) => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
      const reqNameNorm = normalize(loadRequest.filename);
      const resNameNorm = normalize(result.filename);
      const matchesName = Boolean(
        reqNameNorm && resNameNorm && (reqNameNorm.includes(resNameNorm) || resNameNorm.includes(reqNameNorm))
      );

      if (matchesJob || matchesName) {
        onClearLoadRequest?.();
        return;
      }
    }

    let isCancelled = false;
    setIsLoading(true);
    setErrorMessage(null);

    const loadRequestedData = async () => {
      try {
        // 1. Try by jobId if provided
        if (loadRequest.jobId) {
          try {
            const res = await getJobResults(loadRequest.jobId);
            if (!isCancelled && res && res.job_id) {
              setJobId(res.job_id);
              setResult(res);
              setIsLoading(false);
              sessionStorage.setItem('last_extraction_job_id', res.job_id);
              onClearLoadRequest?.();
              return;
            }
          } catch (e) {
            console.warn('Could not fetch by jobId:', e);
          }
        }

        // 2. Try lookup by filename (or latest)
        try {
          const res = await lookupJobResults(loadRequest.filename);
          if (!isCancelled && res && res.job_id) {
            setJobId(res.job_id);
            setResult(res);
            setIsLoading(false);
            sessionStorage.setItem('last_extraction_job_id', res.job_id);
            onClearLoadRequest?.();
            return;
          }
        } catch (e) {
          console.warn('Could not find by filename lookup:', e);
        }

        // 3. Fallback: synthesize extraction result from extractedText & filename so upload screen NEVER shows
        if (loadRequest.extractedText || loadRequest.filename) {
          const fallbackText = loadRequest.extractedText || '';
          const fallbackName = loadRequest.filename || 'Extracted Document';
          const ext = fallbackName.toLowerCase().endsWith('.docx') ? 'docx' : 'pdf';
          const syntheticJobId = loadRequest.jobId || 'imported_' + Date.now();

          const pageSplits = fallbackText.split(/\n\s*--- Page \d+ ---\s*\n/);
          const rawPages = pageSplits.length > 1 ? pageSplits.filter((p) => p.trim()) : [fallbackText];

          const pages = rawPages.map((pt, idx) => ({
            page: idx + 1,
            width: 612,
            height: 792,
            elements: pt
              .split('\n')
              .filter((l) => l.trim())
              .map((line, lIdx) => ({
                id: `el_p${idx + 1}_${lIdx}`,
                type: 'text',
                source: 'native' as const,
                text: line,
                page: idx + 1,
                reading_order: lIdx + 1,
                bbox: [50, 50 + lIdx * 20, 550, 68 + lIdx * 20] as [number, number, number, number],
              })),
          }));

          const syntheticResult: ExtractionResult = {
            job_id: syntheticJobId,
            filename: fallbackName,
            file_type: ext,
            reconstructed_text: fallbackText,
            pages: pages,
            statistics: {
              total_pages: pages.length,
              native_text_blocks: pages.reduce((acc, p) => acc + p.elements.length, 0),
              ocr_text_blocks: 0,
              pp_structure_regions: 0,
              images_count: 0,
              tables_count: 0,
              formulas_count: 0,
              textboxes_count: 0,
              headers_count: 0,
              footers_count: 0,
              footnotes_count: 0,
              possible_duplicates_count: 0,
            },
          };

          if (!isCancelled) {
            setJobId(syntheticJobId);
            setResult(syntheticResult);
            setIsLoading(false);
            onClearLoadRequest?.();
            return;
          }
        }

        if (!isCancelled) {
          setIsLoading(false);
          onClearLoadRequest?.();
        }
      } catch (err: any) {
        if (!isCancelled) {
          console.error('Error restoring extraction:', err);
          setIsLoading(false);
          onClearLoadRequest?.();
        }
      }
    };

    loadRequestedData();

    return () => {
      isCancelled = true;
    };
  }, [loadRequest]);

  // Poll job status during extraction with fast 500ms intervals
  useEffect(() => {
    if (!jobId || !isLoading) return;

    const pollStatus = async () => {
      try {
        const status = await getJobStatus(jobId);
        setJobStatus(status);

        if (status.status === 'completed') {
          setIsLoading(false);
          const finalResult = await getJobResults(jobId);
          setResult(finalResult);
          try {
            sessionStorage.removeItem('new_upload_mode');
            sessionStorage.setItem('last_extraction_job_id', finalResult.job_id);
          } catch (e) {}
          setCurrentPageIndex(0);
        } else if (status.status === 'failed') {
          setIsLoading(false);
          setErrorMessage(status.error || 'Extraction failed during processing.');
        }
      } catch (err: any) {
        console.error('Error polling status:', err);
      }
    };

    pollStatus();
    const interval = setInterval(pollStatus, 500);

    return () => clearInterval(interval);
  }, [jobId, isLoading]);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setErrorMessage(null);
    setResult(null);
    setJobId(null);
    setJobStatus(null);
    setCurrentPageIndex(0);
    leftPageRefs.current = [];
    rightPageRefs.current = [];
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setJobId(null);
    setJobStatus(null);
    setResult(null);
    setErrorMessage(null);
    setIsLoading(false);
    setCurrentPageIndex(0);
    leftPageRefs.current = [];
    rightPageRefs.current = [];
    try {
      sessionStorage.removeItem('last_extraction_job_id');
      sessionStorage.setItem('new_upload_mode', 'true');
    } catch (e) {}
  };

  const handleStartExtraction = async () => {
    if (!selectedFile) return;

    setIsLoading(true);
    setErrorMessage(null);
    setResult(null);

    const isDocx = selectedFile.name.toLowerCase().endsWith('.docx');

    // Immediately display responsive progress UI
    setJobStatus({
      job_id: 'pending',
      filename: selectedFile.name,
      file_type: isDocx ? 'docx' : 'pdf',
      status: 'processing',
      stage: 'uploading',
      progress: 6,
      stage_message: `Uploading ${selectedFile.name} to server...`,
    });

    try {
      // 1. Upload
      const uploadRes = await uploadFile(selectedFile);
      setJobId(uploadRes.job_id);

      setJobStatus((prev) => ({
        ...prev!,
        job_id: uploadRes.job_id,
        stage: isDocx ? 'converting' : 'parsing',
        progress: 12,
        stage_message: isDocx
          ? 'Converting Word document to preserve 100% original visual layout...'
          : 'Parsing document structure & pages...',
      }));

      // 2. Start Extract
      await startExtraction(uploadRes.job_id);
    } catch (err: any) {
      setIsLoading(false);
      setErrorMessage(err.message || 'Failed to start document extraction.');
    }
  };

  const handleReset = () => {
    handleRemoveFile();
  };

  const handleToggleSyncScroll = () => {
    setIsSyncScroll((prev) => !prev);
  };

  const handlePageChange = useCallback((index: number) => {
    setCurrentPageIndex(index);
    activeScroller.current = 'programmatic';
    if (scrollLockTimeout.current) clearTimeout(scrollLockTimeout.current);
    scrollLockTimeout.current = setTimeout(() => {
      activeScroller.current = null;
    }, 700);

    leftPageRefs.current[index]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    rightPageRefs.current[index]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  const syncScroll = (from: 'left' | 'right', to: 'right' | 'left') => {
    if (!result || !result.pages || result.pages.length === 0) return;

    const sourceContainer = from === 'left' ? leftContainerRef.current : rightContainerRef.current;
    const targetContainer = to === 'right' ? rightContainerRef.current : leftContainerRef.current;
    const sourceRefs = from === 'left' ? leftPageRefs.current : rightPageRefs.current;
    const targetRefs = to === 'right' ? rightPageRefs.current : leftPageRefs.current;

    if (!sourceContainer || !targetContainer) return;

    const totalPages = result.pages.length;
    const sourceScrollTop = sourceContainer.scrollTop;
    const sourceContainerRect = sourceContainer.getBoundingClientRect();
    const targetContainerRect = targetContainer.getBoundingClientRect();

    let activeIndex = 0;
    let pageProgress = 0;

    for (let i = 0; i < totalPages; i++) {
      const el = sourceRefs[i];
      if (!el) continue;

      const elRect = el.getBoundingClientRect();
      const elTopInContainer = elRect.top - sourceContainerRect.top + sourceScrollTop;
      const elHeight = el.offsetHeight;
      const elBottomInContainer = elTopInContainer + elHeight;

      if (sourceScrollTop >= elTopInContainer && sourceScrollTop <= elBottomInContainer) {
        activeIndex = i;
        pageProgress = (sourceScrollTop - elTopInContainer) / Math.max(1, elHeight);
        break;
      } else if (sourceScrollTop < elTopInContainer && i === 0) {
        activeIndex = 0;
        pageProgress = 0;
        break;
      } else if (sourceScrollTop > elBottomInContainer && i === totalPages - 1) {
        activeIndex = totalPages - 1;
        pageProgress = 1;
        break;
      } else if (sourceScrollTop >= elTopInContainer) {
        activeIndex = i;
        pageProgress = Math.min(1, (sourceScrollTop - elTopInContainer) / Math.max(1, elHeight));
      }
    }

    if (activeIndex !== currentPageIndex && activeIndex >= 0 && activeIndex < totalPages) {
      setCurrentPageIndex(activeIndex);
    }

    const targetEl = targetRefs[activeIndex];
    if (targetEl) {
      const targetElRect = targetEl.getBoundingClientRect();
      const targetElTopInContainer = targetElRect.top - targetContainerRect.top + targetContainer.scrollTop;
      const targetElHeight = targetEl.offsetHeight;

      const newTargetScrollTop = targetElTopInContainer + pageProgress * targetElHeight;
      targetContainer.scrollTop = newTargetScrollTop;
    } else {
      // Fallback: proportional scroll if target page element is not mounted
      const maxSource = sourceContainer.scrollHeight - sourceContainer.clientHeight;
      const maxTarget = targetContainer.scrollHeight - targetContainer.clientHeight;
      if (maxSource > 0 && maxTarget > 0) {
        const ratio = sourceScrollTop / maxSource;
        targetContainer.scrollTop = ratio * maxTarget;
      }
    }
  };

  const handleLeftScroll = () => {
    if (!isSyncScroll) return;
    if (activeScroller.current === 'right' || activeScroller.current === 'programmatic') return;

    activeScroller.current = 'left';
    if (scrollLockTimeout.current) clearTimeout(scrollLockTimeout.current);
    scrollLockTimeout.current = setTimeout(() => {
      activeScroller.current = null;
    }, 120);

    syncScroll('left', 'right');
  };

  const handleRightScroll = () => {
    if (!isSyncScroll) return;
    if (activeScroller.current === 'left' || activeScroller.current === 'programmatic') return;

    activeScroller.current = 'right';
    if (scrollLockTimeout.current) clearTimeout(scrollLockTimeout.current);
    scrollLockTimeout.current = setTimeout(() => {
      activeScroller.current = null;
    }, 120);

    syncScroll('right', 'left');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Header activeView="extractor" onNavigate={onNavigate} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Upload Section */}
        {!result && (
          <div className="space-y-6">
            <UploadArea
              onFileSelect={handleFileSelect}
              onExtract={handleStartExtraction}
              selectedFile={selectedFile}
              onRemoveFile={handleRemoveFile}
              isLoading={isLoading}
            />

            {isLoading && jobStatus && (
              <ExtractionProgress status={jobStatus} />
            )}

            {errorMessage && (
              <div className="max-w-4xl mx-auto p-4 bg-rose-500/10 border border-rose-500/30 rounded-2xl flex items-center space-x-3 text-rose-300 text-sm">
                <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400" />
                <span>{errorMessage}</span>
              </div>
            )}
          </div>
        )}

        {/* Results Section */}
        {result && (
          <div className="space-y-6 animate-fadeIn">
            {/* Top Toolbar / Reset & Export & Check Originality */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-slate-900 border border-slate-800 rounded-2xl shadow-lg">
              <div>
                <h3 className="text-base font-bold text-white flex items-center space-x-2">
                  <span>{result.filename}</span>
                  <span className="px-2 py-0.5 rounded-full text-xs bg-indigo-500/20 text-indigo-300 uppercase font-semibold">
                    {result.file_type}
                  </span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">Extraction completed successfully.</p>
              </div>

              <div className="flex flex-wrap items-center gap-2.5">
                {/* PROMINENT CHECK ORIGINALITY BUTTON */}
                <button
                  type="button"
                  onClick={() => onNavigateToOriginality?.(result.job_id, result.filename, result.reconstructed_text)}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 via-teal-600 to-indigo-600 hover:from-emerald-500 hover:to-indigo-500 text-white text-xs font-bold flex items-center space-x-2 transition shadow-lg shadow-emerald-950/40 border border-emerald-400/40 cursor-pointer transform hover:-translate-y-0.5 active:translate-y-0"
                  title="Verify if extracted text accurately matches the original document"
                >
                  <ShieldCheck className="w-4 h-4 text-emerald-200" />
                  <span>CHECK ORIGINALITY</span>
                </button>

                <ExportButtons jobId={result.job_id} />

                <button
                  onClick={handleReset}
                  className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold flex items-center space-x-1.5 transition border border-slate-700 cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>New Extraction</span>
                </button>
              </div>
            </div>

            {/* Statistics */}
            <Statistics stats={result.statistics} />

            {/* Main Interactive Dual View (Page Viewer + Results Tabs) */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left Pane: Uploaded File */}
              <div className="flex flex-col space-y-2">
                <div className="flex items-center justify-between px-2">
                  <div className="flex items-center space-x-2">
                    <span className="p-1 rounded-lg bg-blue-500/20 text-blue-400">
                      <FileText className="w-4 h-4" />
                    </span>
                    <h4 className="text-sm font-bold text-white tracking-wide">Uploaded File</h4>
                    <span className="text-[11px] text-blue-300/80 bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 rounded-full font-medium">
                      Original Document
                    </span>
                  </div>
                </div>

                <PageViewer
                  pages={result.pages}
                  selectedElementId={selectedElement?.id || null}
                  onSelectElement={setSelectedElement}
                  currentPageIndex={currentPageIndex}
                  onPageChange={handlePageChange}
                  onActivePageChange={setCurrentPageIndex}
                  isSyncScroll={isSyncScroll}
                  onToggleSyncScroll={handleToggleSyncScroll}
                  onScrollContainerScroll={handleLeftScroll}
                  containerRefExternal={leftContainerRef}
                  pageRefsExternal={leftPageRefs}
                />
              </div>

              {/* Right Pane: Converted Text */}
              <div className="flex flex-col space-y-2">
                <div className="flex items-center justify-between px-2">
                  <div className="flex items-center space-x-2">
                    <span className="p-1 rounded-lg bg-indigo-500/20 text-indigo-400">
                      <FileCode className="w-4 h-4" />
                    </span>
                    <h4 className="text-sm font-bold text-white tracking-wide">Converted Text</h4>
                    <span className="text-[11px] text-indigo-300/80 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-full font-medium">
                      Extracted & Structured
                    </span>
                  </div>
                </div>

                <ResultsTabs
                  result={result}
                  selectedElementId={selectedElement?.id || null}
                  onSelectElement={setSelectedElement}
                  currentPageIndex={currentPageIndex}
                  onPageChange={handlePageChange}
                  isSyncScroll={isSyncScroll}
                  onToggleSyncScroll={handleToggleSyncScroll}
                  onScrollContainerScroll={handleRightScroll}
                  containerRefExternal={rightContainerRef}
                  pageRefsExternal={rightPageRefs}
                />
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-500">
        Text Extractor Tool • Built with FastAPI, PaddleOCR & React
      </footer>
    </div>
  );
};
