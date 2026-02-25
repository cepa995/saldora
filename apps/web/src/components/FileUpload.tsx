'use client';

import { useCallback, useMemo, useState, InputHTMLAttributes } from 'react';
import { useDropzone, FileRejection } from 'react-dropzone';
import { apiClient } from '@/lib/api-client';
import { usePollingStatus, ProcessingStatusResponse } from '@/hooks/usePollingStatus';
import { PipelineStepper } from './PipelineStepper';
import type { PipelineStatus } from './PipelineStepper';

// FR-4.2.1: Supported formats and size limits
const ACCEPTED_FILE_TYPES = {
  'application/pdf': ['.pdf'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
  'image/tiff': ['.tiff', '.tif'],
  'image/bmp': ['.bmp'],
  'image/webp': ['.webp'],
};

const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20 MB per file
const MAX_BATCH_FILES = 50;
const MAX_BATCH_TOTAL_SIZE = 200 * 1024 * 1024; // 200 MB total

// Supported format labels for display
const SUPPORTED_FORMATS = ['PDF', 'JPEG', 'PNG', 'TIFF', 'BMP', 'WEBP'];

export interface UploadedFile {
  file: File;
  preview: string | null;
  status: 'pending' | 'uploading' | 'uploaded' | 'processing' | 'success' | 'error';
  progress: number;
  error?: string;
  jobId?: string;
}

export interface BatchUploadResult {
  id: string;
  status: string;
  progress: number;
  estimated_time: number | null;
  error_message: string | null;
  document_id: string | null;
  created_at: string;
}

interface FileUploadProps {
  onFilesAccepted?: (files: File[]) => void;
  onUploadStart?: () => void;
  onUploadComplete?: (results: BatchUploadResult[]) => void;
  onError?: (error: string) => void;
  disabled?: boolean;
}

// Format file size for display
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

// Map UploadedFile status → PipelineStepper status
function toPipelineStatus(fileStatus: UploadedFile['status']): PipelineStatus {
  switch (fileStatus) {
    case 'uploading':
      return 'uploading';
    case 'uploaded':
      return 'queued';
    case 'processing':
      return 'processing';
    case 'success':
      return 'review';
    case 'error':
      return 'error';
    default:
      return 'uploading';
  }
}

export function FileUpload({
  onFilesAccepted,
  onUploadStart,
  onUploadComplete,
  onError,
  disabled = false,
}: FileUploadProps) {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [validationError, setValidationError] = useState<string | null>(null);

  const isUploading = uploadedFiles.some((f) => f.status === 'uploading');
  const allDone =
    uploadedFiles.length > 0 &&
    uploadedFiles.every((f) => f.status === 'success' || f.status === 'error');
  const hasPending = uploadedFiles.some((f) => f.status === 'pending');

  // Collect job IDs that need polling (uploaded or processing, not yet terminal)
  const pollableJobIds = useMemo(
    () =>
      uploadedFiles
        .filter((f) => f.jobId && (f.status === 'uploaded' || f.status === 'processing'))
        .map((f) => f.jobId!),
    [uploadedFiles],
  );

  // Handle status updates from polling
  const handleStatusUpdate = useCallback(
    (jobId: string, data: ProcessingStatusResponse) => {
      setUploadedFiles((prev) =>
        prev.map((f) => {
          if (f.jobId !== jobId) return f;
          switch (data.status) {
            case 'queued':
              return { ...f, status: 'uploaded' as const, progress: data.progress };
            case 'processing':
              return { ...f, status: 'processing' as const, progress: data.progress };
            case 'completed':
              return { ...f, status: 'success' as const, progress: 100 };
            case 'failed':
              return {
                ...f,
                status: 'error' as const,
                error: data.error_message || 'Greška pri obradi fakture.',
              };
            default:
              return f;
          }
        }),
      );
    },
    [],
  );

  usePollingStatus(pollableJobIds, { onStatusUpdate: handleStatusUpdate });

  // Generate preview URL for images
  const generatePreview = (file: File): string | null => {
    if (file.type.startsWith('image/')) {
      return URL.createObjectURL(file);
    }
    return null;
  };

  // Handle file drop/selection
  const onDrop = useCallback(
    (acceptedFiles: File[], fileRejections: FileRejection[]) => {
      setValidationError(null);

      // Handle rejections
      if (fileRejections.length > 0) {
        const errors = fileRejections.flatMap((r) => r.errors);

        if (errors.some((e) => e.code === 'file-too-large')) {
          const errorMsg = `Fajl je prevelik. Maksimalna veličina po fajlu je ${formatFileSize(MAX_FILE_SIZE)}.`;
          setValidationError(errorMsg);
          onError?.(errorMsg);
        } else if (errors.some((e) => e.code === 'file-invalid-type')) {
          const errorMsg = `Nepodržan format fajla. Podržani formati: ${SUPPORTED_FORMATS.join(', ')}.`;
          setValidationError(errorMsg);
          onError?.(errorMsg);
        } else if (errors.some((e) => e.code === 'too-many-files')) {
          const errorMsg = `Maksimalan broj fajlova je ${MAX_BATCH_FILES}.`;
          setValidationError(errorMsg);
          onError?.(errorMsg);
        } else {
          const errorMsg = 'Greška pri učitavanju fajla.';
          setValidationError(errorMsg);
          onError?.(errorMsg);
        }
        if (acceptedFiles.length === 0) return;
      }

      if (acceptedFiles.length > 0) {
        const currentPending = uploadedFiles.filter((f) => f.status === 'pending');
        const totalCount = currentPending.length + acceptedFiles.length;

        if (totalCount > MAX_BATCH_FILES) {
          const errorMsg = `Maksimalan broj fajlova je ${MAX_BATCH_FILES}. Već imate ${currentPending.length} odabranih.`;
          setValidationError(errorMsg);
          onError?.(errorMsg);
          return;
        }

        const currentTotalSize = currentPending.reduce((sum, f) => sum + f.file.size, 0);
        const newTotalSize = currentTotalSize + acceptedFiles.reduce((sum, f) => sum + f.size, 0);

        if (newTotalSize > MAX_BATCH_TOTAL_SIZE) {
          const errorMsg = `Ukupna veličina prevazilazi ${formatFileSize(MAX_BATCH_TOTAL_SIZE)}.`;
          setValidationError(errorMsg);
          onError?.(errorMsg);
          return;
        }

        const newFiles: UploadedFile[] = acceptedFiles.map((file) => ({
          file,
          preview: generatePreview(file),
          status: 'pending' as const,
          progress: 0,
        }));

        const updated = [...currentPending, ...newFiles];
        setUploadedFiles(updated);
        onFilesAccepted?.(acceptedFiles);
      }
    },
    [uploadedFiles, onFilesAccepted, onError]
  );

  // Configure dropzone
  const dropzoneConfig = {
    onDrop,
    accept: ACCEPTED_FILE_TYPES,
    maxSize: MAX_FILE_SIZE,
    maxFiles: MAX_BATCH_FILES,
    multiple: true,
    disabled: disabled || isUploading || allDone,
  };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { getRootProps, getInputProps, isDragActive, isDragAccept, isDragReject } = useDropzone(dropzoneConfig as any);

  // Upload files to API via batch endpoint
  const handleUpload = async () => {
    const pendingFiles = uploadedFiles.filter((f) => f.status === 'pending');
    if (pendingFiles.length === 0) return;

    setUploadedFiles((prev) =>
      prev.map((f) => (f.status === 'pending' ? { ...f, status: 'uploading' as const, progress: 0 } : f))
    );
    onUploadStart?.();

    try {
      const formData = new FormData();
      for (const uf of pendingFiles) {
        formData.append('files', uf.file);
      }

      const results = await apiClient<BatchUploadResult[]>('/api/v1/invoices/upload/batch', {
        method: 'POST',
        body: formData,
      });

      // Map results back to files by index (batch endpoint returns results in same order)
      setUploadedFiles((prev) => {
        let resultIdx = 0;
        return prev.map((f) => {
          if (f.status !== 'uploading') return f;
          const result = results[resultIdx++];
          if (!result) return f;

          if (result.status === 'failed') {
            return {
              ...f,
              status: 'error' as const,
              error: result.error_message || 'Greška pri obradi fajla.',
            };
          }
          return {
            ...f,
            status: 'uploaded' as const,
            progress: 100,
            jobId: result.id,
          };
        });
      });

      onUploadComplete?.(results);
    } catch (error) {
      const errorMsg =
        error && typeof error === 'object' && 'message' in error
          ? String((error as { message: string }).message)
          : 'Greška pri slanju fajlova.';
      setUploadedFiles((prev) =>
        prev.map((f) => (f.status === 'uploading' ? { ...f, status: 'error' as const, error: errorMsg } : f))
      );
      onError?.(errorMsg);
    }
  };

  // Remove a specific file
  const handleRemoveFile = (index: number) => {
    setUploadedFiles((prev) => {
      const file = prev[index];
      if (file?.preview) URL.revokeObjectURL(file.preview);
      return prev.filter((_, i) => i !== index);
    });
    setValidationError(null);
  };

  // Clear all files and reset
  const handleClearAll = () => {
    uploadedFiles.forEach((f) => {
      if (f.preview) URL.revokeObjectURL(f.preview);
    });
    setUploadedFiles([]);
    setValidationError(null);
  };

  // Determine dropzone styling based on state
  const getDropzoneClassName = (): string => {
    const baseClasses =
      'relative flex flex-col items-center justify-center w-full p-8 border-2 border-dashed rounded-2xl cursor-pointer transition-all duration-200';
    const heightClass = uploadedFiles.length > 0 ? 'min-h-[160px]' : 'min-h-[300px]';

    if (disabled || isUploading || allDone) {
      return `${baseClasses} ${heightClass} border-gray-200 bg-gray-50 cursor-not-allowed`;
    }
    if (isDragReject) return `${baseClasses} ${heightClass} border-red-400 bg-red-50`;
    if (isDragAccept) return `${baseClasses} ${heightClass} border-green-400 bg-green-50`;
    if (isDragActive) return `${baseClasses} ${heightClass} border-blue-400 bg-blue-50`;
    return `${baseClasses} ${heightClass} border-gray-300 bg-white hover:border-blue-400 hover:bg-blue-50`;
  };

  const pendingCount = uploadedFiles.filter((f) => f.status === 'pending').length;
  const totalSize = uploadedFiles.filter((f) => f.status === 'pending').reduce((sum, f) => sum + f.file.size, 0);

  return (
    <div className="w-full max-w-5xl mx-auto">
      {/* Dropzone Area */}
      <div {...getRootProps({ className: getDropzoneClassName() })}>
        <input {...(getInputProps() as InputHTMLAttributes<HTMLInputElement>)} />

        <div className="flex flex-col items-center text-center">
          {/* Upload Icon — stacked documents to hint at multi-file */}
          <div className="mb-4 relative">
            {/* Back document (offset) */}
            <svg
              className={`w-10 h-10 absolute -top-1 -left-1 ${isDragActive ? 'text-blue-300' : 'text-gray-300'}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
              />
            </svg>
            {/* Front document */}
            <svg
              className={`w-10 h-10 relative z-10 ${isDragActive ? 'text-blue-500' : 'text-gray-400'}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
              />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 13l-3-3m0 0l-3 3m3-3v8" />
            </svg>
          </div>

          {/* Instructions */}
          {isDragActive ? (
            <p className="text-lg font-medium text-blue-600">Pustite fajlove ovde...</p>
          ) : (
            <>
              <p className="text-lg font-medium text-gray-700 mb-1">
                Prevucite fakture ovde ili kliknite za odabir
              </p>
              <p className="text-sm font-medium text-blue-600 mb-3">
                Možete odabrati jednu ili više faktura odjednom
              </p>
              <div className="flex items-center gap-4 text-xs text-gray-400">
                <span>{SUPPORTED_FORMATS.join(', ')}</span>
                <span className="w-1 h-1 rounded-full bg-gray-300" />
                <span>do {MAX_BATCH_FILES} fajlova</span>
                <span className="w-1 h-1 rounded-full bg-gray-300" />
                <span>{formatFileSize(MAX_FILE_SIZE)} po fajlu</span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Validation Error Message */}
      {validationError && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <p className="text-sm text-red-700">{validationError}</p>
          </div>
        </div>
      )}

      {/* File List */}
      {uploadedFiles.length > 0 && (
        <div className="mt-4">
          {/* Header with count and clear button */}
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-medium text-gray-700">
              {hasPending
                ? `${pendingCount} ${pendingCount === 1 ? 'fajl odabran' : 'fajlova odabrano'} (${formatFileSize(totalSize)})`
                : `${uploadedFiles.length} ${uploadedFiles.length === 1 ? 'fajl' : 'fajlova'}`}
            </p>
            {!isUploading && (
              <button
                type="button"
                onClick={handleClearAll}
                className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
              >
                Obriši sve
              </button>
            )}
          </div>

          {/* File items */}
          <div className="space-y-4">
            {uploadedFiles.map((uf, index) =>
              uf.status === 'pending' ? (
                /* Compact card for pending files */
                <div
                  key={`${uf.file.name}-${index}`}
                  className="flex items-center gap-3 p-3 bg-white rounded-xl border border-gray-200"
                >
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center">
                    {uf.preview ? (
                      // eslint-disable-next-line @next/next/no-img-element -- blob URL preview
                      <img src={uf.preview} alt="Preview" className="w-full h-full object-cover" />
                    ) : (
                      <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zM6 20V4h7v5h5v11H6z" />
                      </svg>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{uf.file.name}</p>
                    <p className="text-xs text-gray-500">{formatFileSize(uf.file.size)}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveFile(index)}
                    className="flex-shrink-0 p-1 rounded-full hover:bg-gray-100 transition-colors"
                    aria-label="Ukloni fajl"
                  >
                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ) : (
                /* Wide card: preview left | pipeline right */
                <div
                  key={`${uf.file.name}-${index}`}
                  className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden"
                >
                  <div className="flex">
                    {/* Left: preview + file info */}
                    <div className="flex-shrink-0 w-48 bg-gray-50 border-r border-gray-100 flex flex-col items-center justify-center p-5 gap-3">
                      <div className="w-28 h-36 rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center shadow-inner">
                        {uf.preview ? (
                          // eslint-disable-next-line @next/next/no-img-element -- blob URL preview
                          <img src={uf.preview} alt="Preview" className="w-full h-full object-cover" />
                        ) : (
                          <svg className="w-12 h-12 text-red-400" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zM6 20V4h7v5h5v11H6z" />
                            <path d="M8 12h8v2H8zm0 4h8v2H8z" />
                          </svg>
                        )}
                      </div>
                      <div className="text-center min-w-0 w-full">
                        <p className="text-sm font-semibold text-gray-900 truncate px-1">{uf.file.name}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{formatFileSize(uf.file.size)}</p>
                      </div>
                    </div>

                    {/* Right: pipeline stepper + status message */}
                    <div className="flex-1 p-6 flex flex-col justify-center">
                      <PipelineStepper
                        currentStatus={toPipelineStatus(uf.status)}
                        errorMessage={uf.error}
                      />

                      {/* Per-card status messages */}
                      {uf.status === 'uploaded' && (
                        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-xl">
                          <div className="flex items-center gap-2">
                            <svg className="animate-spin h-4 w-4 text-blue-500" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                            </svg>
                            <p className="text-xs font-medium text-blue-800">Čeka na obradu...</p>
                          </div>
                        </div>
                      )}

                      {uf.status === 'processing' && (
                        <div className="mt-4 flex items-center justify-center gap-2">
                          <svg className="animate-spin h-4 w-4 text-violet-600" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                          </svg>
                          <p className="text-sm text-violet-600">OCR obrada u toku — ekstrahujemo podatke...</p>
                        </div>
                      )}

                      {uf.status === 'success' && (
                        <div className="mt-4 text-center">
                          <p className="text-sm text-green-600">Obrada završena! Faktura je spremna za pregled.</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            )}
          </div>
        </div>
      )}

      {/* Upload Button */}
      {hasPending && (
        <div className="mt-6 flex justify-center">
          <button
            type="button"
            onClick={handleUpload}
            className="px-6 py-3 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
          >
            {pendingCount === 1 ? 'Obradi fakturu' : `Obradi fakture (${pendingCount})`}
          </button>
        </div>
      )}

      {/* Upload More Button */}
      {allDone && (
        <div className="mt-6 flex justify-center">
          <button
            type="button"
            onClick={handleClearAll}
            className="px-6 py-3 bg-gray-100 text-gray-700 font-medium rounded-xl hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors"
          >
            Učitaj nove fakture
          </button>
        </div>
      )}
    </div>
  );
}
