/**
 * Module-level store for upload state.
 *
 * Keeps upload progress alive across page navigations so users can
 * leave /upload and come back without losing in-flight uploads.
 * Uses useSyncExternalStore (React 18+) — no external dependency.
 */

import { useSyncExternalStore } from 'react';

export interface UploadedFile {
  file: File;
  preview: string | null;
  status: 'pending' | 'uploading' | 'uploaded' | 'processing' | 'success' | 'error';
  progress: number;
  stage?: string | null;
  error?: string;
  jobId?: string;
}

type Listener = () => void;

let files: UploadedFile[] = [];
const listeners = new Set<Listener>();

function emit() {
  listeners.forEach((l) => l());
}

function subscribe(listener: Listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot(): UploadedFile[] {
  return files;
}

export function setUploadFiles(updater: UploadedFile[] | ((prev: UploadedFile[]) => UploadedFile[])) {
  files = typeof updater === 'function' ? updater(files) : updater;
  emit();
}

export function clearUploadFiles() {
  files.forEach((f) => {
    if (f.preview) URL.revokeObjectURL(f.preview);
  });
  files = [];
  emit();
}

export function removeUploadFile(index: number) {
  const file = files[index];
  if (file?.preview) URL.revokeObjectURL(file.preview);
  files = files.filter((_, i) => i !== index);
  emit();
}

export function useUploadFiles(): UploadedFile[] {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}
