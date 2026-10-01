import { OriginalityReport, DocumentMetadata } from '../types/originality';

const API_BASE = '';

export interface CheckOriginalityParams {
  originalFile?: File | null;
  extractedFile?: File | null;
  jobId?: string | null;
  extractedText?: string | null;
  originalFilename?: string | null;
  extractedFilename?: string | null;
}

export async function inspectMetadata(file: File): Promise<DocumentMetadata> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/api/originality/metadata`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Metadata extraction failed' }));
    throw new Error(errorData.detail || 'Failed to inspect document metadata');
  }

  return res.json();
}

export async function checkOriginality(params: CheckOriginalityParams): Promise<OriginalityReport> {
  const formData = new FormData();

  if (params.originalFile) {
    formData.append('original_file', params.originalFile);
  }
  if (params.extractedFile) {
    formData.append('extracted_file', params.extractedFile);
  }
  if (params.jobId) {
    formData.append('job_id', params.jobId);
  }
  if (params.extractedText) {
    formData.append('extracted_text', params.extractedText);
  }
  if (params.originalFilename) {
    formData.append('original_filename', params.originalFilename);
  }
  if (params.extractedFilename) {
    formData.append('extracted_filename', params.extractedFilename);
  }

  const res = await fetch(`${API_BASE}/api/originality/check`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Originality check failed' }));
    throw new Error(errorData.detail || 'Failed to perform originality comparison');
  }

  return res.json();
}

export async function getOriginalityReport(reportId: string): Promise<OriginalityReport> {
  const res = await fetch(`${API_BASE}/api/originality/report/${reportId}`);
  if (!res.ok) {
    throw new Error('Failed to retrieve originality report');
  }
  return res.json();
}

export function getReportPdfUrl(reportId: string): string {
  return `${API_BASE}/api/originality/report/${reportId}/pdf`;
}

export function getReportJsonUrl(reportId: string): string {
  return `${API_BASE}/api/originality/report/${reportId}/json`;
}

export function getReportCsvUrl(reportId: string): string {
  return `${API_BASE}/api/originality/report/${reportId}/csv`;
}
