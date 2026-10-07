import React, { useState, useEffect } from 'react';
import { Home } from './pages/Home';
import { OriginalityCheck } from './pages/OriginalityCheck';

export interface ExtractorLoadRequest {
  jobId?: string;
  filename?: string;
  extractedText?: string;
  action?: 'load_extracted' | 'new_upload';
}

export function App() {
  const [activeView, setActiveView] = useState<'extractor' | 'originality'>(() => {
    return window.location.hash === '#originality' ? 'originality' : 'extractor';
  });

  const [origJobId, setOrigJobId] = useState<string | null>(null);
  const [origFilename, setOrigFilename] = useState<string | null>(null);
  const [origExtractedText, setOrigExtractedText] = useState<string | null>(null);
  const [extractorLoadRequest, setExtractorLoadRequest] = useState<ExtractorLoadRequest | null>(null);
  const [hasVisitedOriginality, setHasVisitedOriginality] = useState<boolean>(false);

  // Sync view with URL hash
  useEffect(() => {
    const handleHashChange = () => {
      if (window.location.hash === '#originality') {
        setActiveView('originality');
        setHasVisitedOriginality(true);
      } else {
        setActiveView('extractor');
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handleNavigate = (view: 'extractor' | 'originality') => {
    if (view === 'originality') {
      setHasVisitedOriginality(true);
    }
    setActiveView(view);
    window.location.hash = view === 'originality' ? '#originality' : '#extractor';
  };

  const handleNavigateToOriginality = (jobId: string, filename: string, extractedText?: string) => {
    setOrigJobId(jobId);
    setOrigFilename(filename);
    setOrigExtractedText(extractedText || null);
    setHasVisitedOriginality(true);
    handleNavigate('originality');
  };

  const handleNavigateToNewOriginality = () => {
    setOrigJobId(null);
    setOrigFilename(null);
    setOrigExtractedText(null);
    setHasVisitedOriginality(true);
    handleNavigate('originality');
  };

  const handleBackToExtractor = (info?: ExtractorLoadRequest) => {
    if (info) {
      setExtractorLoadRequest(info);
    }
    handleNavigate('extractor');
  };

  return (
    <>
      <div style={{ display: activeView === 'extractor' ? 'block' : 'none' }}>
        <Home
          loadRequest={extractorLoadRequest}
          onClearLoadRequest={() => setExtractorLoadRequest(null)}
          onNavigateToOriginality={handleNavigateToOriginality}
          onNavigateToNewOriginality={handleNavigateToNewOriginality}
          onNavigate={handleNavigate}
          hasVisitedOriginality={hasVisitedOriginality}
        />
      </div>
      {activeView === 'originality' && (
        <OriginalityCheck
          key={`${origJobId || 'new'}-${origFilename || 'empty'}`}
          initialJobId={origJobId}
          initialOriginalFileName={origFilename}
          initialExtractedText={origExtractedText}
          onBackToExtractor={handleBackToExtractor}
          onNewVerification={handleNavigateToNewOriginality}
        />
      )}
    </>
  );
}

export default App;
