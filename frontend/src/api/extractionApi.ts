import { ExtractionJobStatus, ExtractionResult } from '../types/extraction';

const API_BASE = '';

export async function uploadFile(file: File): Promise<{ job_id: string; filename: string; status: string }> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/api/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(errorData.detail || 'Failed to upload document');
  }

  return res.json();
}

export async function startExtraction(job_id: string): Promise<{ job_id: string; status: string }> {
  const res = await fetch(`${API_BASE}/api/extract`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_id }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Extraction request failed' }));
    throw new Error(errorData.detail || 'Failed to start extraction');
  }

  return res.json();
}

export async function getJobStatus(job_id: string): Promise<ExtractionJobStatus> {
  const res = await fetch(`${API_BASE}/api/status/${job_id}`);
  if (!res.ok) {
    throw new Error('Failed to fetch job status');
  }
  return res.json();
}

export async function getJobResults(job_id: string): Promise<ExtractionResult> {
  const res = await fetch(`${API_BASE}/api/results/${job_id}`);
  if (!res.ok) {
    throw new Error('Failed to fetch job results');
  }
  return res.json();
}

export async function lookupJobResults(filename?: string): Promise<ExtractionResult> {
  const query = filename ? `?filename=${encodeURIComponent(filename)}` : '';
  const res = await fetch(`${API_BASE}/api/results/lookup${query}`);
  if (!res.ok) {
    throw new Error('Failed to find extraction results');
  }
  return res.json();
}

export function getExportTxtUrl(job_id: string): string {
  return `${API_BASE}/api/export/${job_id}/txt`;
}

export function getExportJsonUrl(job_id: string): string {
  return `${API_BASE}/api/export/${job_id}/json`;
}
