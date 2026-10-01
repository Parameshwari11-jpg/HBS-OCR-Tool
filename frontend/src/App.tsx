import React, { useState, useEffect } from 'react';
import { Home } from './pages/Home';
import { OriginalityCheck } from './pages/OriginalityCheck';

export function App() {
  const [activeView, setActiveView] = useState<'extractor' | 'originality'>(() => {
    return window.location.hash === '#originality' ? 'originality' : 'extractor';
  });

  const [origJobId, setOrigJobId] = useState<string | null>(null);
  const [origFilename, setOrigFilename] = useState<string | null>(null);
  const [origExtractedText, setOrigExtractedText] = useState<string | null>(null);

  // Sync view with URL hash
  useEffect(() => {
    const handleHashChange = () => {
      if (window.location.hash === '#originality') {
        setActiveView('originality');
      } else {
        setActiveView('extractor');
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handleNavigate = (view: 'extractor' | 'originality') => {
    setActiveView(view);
    window.location.hash = view === 'originality' ? '#originality' : '#extractor';
  };

  const handleNavigateToOriginality = (jobId: string, filename: string, extractedText?: string) => {
    setOrigJobId(jobId);
    setOrigFilename(filename);
    setOrigExtractedText(extractedText || null);
    handleNavigate('originality');
  };

  if (activeView === 'originality') {
    return (
      <OriginalityCheck
        initialJobId={origJobId}
        initialOriginalFileName={origFilename}
        initialExtractedText={origExtractedText}
        onBackToExtractor={() => handleNavigate('extractor')}
      />
    );
  }

  return (
    <Home
      onNavigateToOriginality={handleNavigateToOriginality}
      onNavigate={handleNavigate}
    />
  );
}

export default App;
