'use client';

import { useCallback, useEffect, useMemo, useState, InputHTMLAttributes } from 'react';
import { useRouter } from 'next/navigation';
import { useDropzone, FileRejection } from 'react-dropzone';
import { useTranslations } from 'next-intl';
import { apiClient } from '@/lib/api-client';
import { usePollingStatus, ProcessingStatusResponse } from '@/hooks/usePollingStatus';
import {
  useUploadFiles,
  setUploadFiles,
  clearUploadFiles,
  removeUploadFile,
  type UploadedFile,
} from '@/stores/uploadStore';
import { PipelineStepper } from './PipelineStepper';
import type { PipelineStatus } from './PipelineStepper';

const ACCEPTED_FILE_TYPES = {
  'application/pdf': ['.pdf'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
  'image/tiff': ['.tiff', '.tif'],
  'image/bmp': ['.bmp'],
  'image/webp': ['.webp'],
};

const MAX_FILE_SIZE = 20 * 1024 * 1024;
const MAX_BATCH_FILES = 50;
const MAX_BATCH_TOTAL_SIZE = 200 * 1024 * 1024;

const SUPPORTED_FORMATS = ['PDF', 'JPEG', 'PNG', 'TIFF', 'BMP', 'WEBP'];

const STAGE_KEYS: Record<string, string> = {
  downloading: 'stageDownloading',
  preprocessing: 'stagePreprocessing',
  ocr: 'stageOcr',
  ocr_running: 'stageOcr',
  extraction: 'stageExtracting',
  extracting_fields: 'stageExtracting',
  validation: 'stageValidating',
  saving: 'stageSaving',
};

export type { UploadedFile };

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
  onFileCountChange?: (count: number) => void;
  disabled?: boolean;
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

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
  onFileCountChange,
  disabled = false,
}: FileUploadProps) {
  const t = useTranslations('upload');
  const router = useRouter();
  const uploadedFiles = useUploadFiles();
  const [validationError, setValidationError] = useState<string | null>(null);

  const isUploading = uploadedFiles.some((f) => f.status === 'uploading');
  const allDone =
    uploadedFiles.length > 0 &&
    uploadedFiles.every((f) => f.status === 'success' || f.status === 'error');
  const hasPending = uploadedFiles.some((f) => f.status === 'pending');

  // Notify parent of file count changes
  useEffect(() => {
    onFileCountChange?.(uploadedFiles.length);
  }, [uploadedFiles.length, onFileCountChange]);

  // Auto-redirect for single file upload on completion
  useEffect(() => {
    if (uploadedFiles.length === 1 && uploadedFiles[0].status === 'success' && uploadedFiles[0].jobId) {
      const jobId = uploadedFiles[0].jobId;
      const timer = setTimeout(() => {
        clearUploadFiles();
        router.push(`/invoices/${jobId}`);
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [uploadedFiles, router]);

  const pollableJobIds = useMemo(
    () =>
      uploadedFiles
        .filter((f) => f.jobId && (f.status === 'uploaded' || f.status === 'processing'))
        .map((f) => f.jobId!),
    [uploadedFiles],
  );

  const handleStatusUpdate = useCallback(
    (jobId: string, data: ProcessingStatusResponse) => {
      setUploadFiles((prev) =>
        prev.map((f) => {
          if (f.jobId !== jobId) return f;
          switch (data.status) {
            case 'queued':
              return { ...f, status: 'uploaded' as const, progress: data.progress };
            case 'processing':
              return { ...f, status: 'processing' as const, progress: data.progress, stage: data.stage };
            case 'completed':
              return { ...f, status: 'success' as const, progress: 100, stage: null };
            case 'failed':
              return {
                ...f,
                status: 'error' as const,
                error: data.error_message || t('errorProcessing'),
              };
            default:
              return f;
          }
        }),
      );
    },
    [t],
  );

  usePollingStatus(pollableJobIds, { onStatusUpdate: handleStatusUpdate });

  const generatePreview = (file: File): string | null => {
    if (file.type.startsWith('image/')) {
      return URL.createObjectURL(file);
    }
    return null;
  };

  const onDrop = useCallback(
    (acceptedFiles: File[], fileRejections: FileRejection[]) => {
      setValidationError(null);

      if (fileRejections.length > 0) {
        const errors = fileRejections.flatMap((r) => r.errors);

        if (errors.some((e) => e.code === 'file-too-large')) {
          const errorMsg = t('fileTooBig', { max: '20' });
          setValidationError(errorMsg);
          onError?.(errorMsg);
        } else if (errors.some((e) => e.code === 'file-invalid-type')) {
          const errorMsg = t('unsupportedFormat');
          setValidationError(errorMsg);
          onError?.(errorMsg);
        } else if (errors.some((e) => e.code === 'too-many-files')) {
          const errorMsg = t('tooManyFiles', { max: String(MAX_BATCH_FILES) });
          setValidationError(errorMsg);
          onError?.(errorMsg);
        } else {
          const errorMsg = t('uploadError');
          setValidationError(errorMsg);
          onError?.(errorMsg);
        }
        if (acceptedFiles.length === 0) return;
      }

      if (acceptedFiles.length > 0) {
        const currentPending = uploadedFiles.filter((f) => f.status === 'pending');
        const totalCount = currentPending.length + acceptedFiles.length;

        if (totalCount > MAX_BATCH_FILES) {
          const errorMsg = t('tooManyFiles', { max: String(MAX_BATCH_FILES) });
          setValidationError(errorMsg);
          onError?.(errorMsg);
          return;
        }

        const currentTotalSize = currentPending.reduce((sum, f) => sum + f.file.size, 0);
        const newTotalSize = currentTotalSize + acceptedFiles.reduce((sum, f) => sum + f.size, 0);

        if (newTotalSize > MAX_BATCH_TOTAL_SIZE) {
          const errorMsg = t('totalSizeTooLarge', { max: '200' });
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
        setUploadFiles(updated);
        onFilesAccepted?.(acceptedFiles);
      }
    },
    [uploadedFiles, onFilesAccepted, onError, t]
  );

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

  const handleUpload = async () => {
    const pendingFiles = uploadedFiles.filter((f) => f.status === 'pending');
    if (pendingFiles.length === 0) return;

    setUploadFiles((prev) =>
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

      setUploadFiles((prev) => {
        let resultIdx = 0;
        return prev.map((f) => {
          if (f.status !== 'uploading') return f;
          const result = results[resultIdx++];
          if (!result) return f;

          if (result.status === 'failed') {
            return {
              ...f,
              status: 'error' as const,
              error: result.error_message || t('processingError'),
            };
          }
          return {
            ...f,
            status: 'uploaded' as const,
            progress: 0,
            jobId: result.id,
          };
        });
      });

      onUploadComplete?.(results);
    } catch (error) {
      const errorMsg =
        error && typeof error === 'object' && 'message' in error
          ? String((error as { message: string }).message)
          : t('uploadError');
      setUploadFiles((prev) =>
        prev.map((f) => (f.status === 'uploading' ? { ...f, status: 'error' as const, error: errorMsg } : f))
      );
      onError?.(errorMsg);
    }
  };

  const handleRemoveFile = (index: number) => {
    removeUploadFile(index);
    setValidationError(null);
  };

  const handleClearAll = () => {
    clearUploadFiles();
    setValidationError(null);
  };

  const getDropzoneClassName = (): string => {
    const baseClasses =
      'relative flex flex-col items-center justify-center w-full p-8 border-2 border-dashed rounded-2xl cursor-pointer transition-all duration-200';
    const heightClass = uploadedFiles.length > 0 ? 'min-h-[160px]' : 'min-h-[300px]';

    if (disabled || isUploading || allDone) {
      return `${baseClasses} ${heightClass} border-gray-200 bg-gray-50 cursor-not-allowed`;
    }
    if (isDragReject) return `${baseClasses} ${heightClass} border-red-400 bg-red-50`;
    if (isDragAccept) return `${baseClasses} ${heightClass} border-green-400 bg-green-50`;
    if (isDragActive) return `${baseClasses} ${heightClass} border-violet-400 bg-violet-50`;
    return `${baseClasses} ${heightClass} border-gray-300 bg-white hover:border-violet-400 hover:bg-violet-50`;
  };

  const pendingCount = uploadedFiles.filter((f) => f.status === 'pending').length;
  const totalSize = uploadedFiles.filter((f) => f.status === 'pending').reduce((sum, f) => sum + f.file.size, 0);

  const getStageText = (stage: string | null | undefined): string => {
    if (!stage) return t('ocrInProgress');
    const key = STAGE_KEYS[stage];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return key ? (t as any)(key) : t('ocrInProgress');
  };

  const isSingleFileRedirecting = uploadedFiles.length === 1 && uploadedFiles[0].status === 'success';

  return (
    <div className="w-full max-w-5xl mx-auto">
      {/* Dropzone Area */}
      <div {...getRootProps({ className: getDropzoneClassName() })}>
        <input {...(getInputProps() as InputHTMLAttributes<HTMLInputElement>)} />

        <div className="flex flex-col items-center text-center">
          <div className="mb-4 relative">
            <svg
              className={`w-10 h-10 absolute -top-1 -left-1 ${isDragActive ? 'text-violet-300' : 'text-gray-300'}`}
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
            <svg
              className={`w-10 h-10 relative z-10 ${isDragActive ? 'text-violet-500' : 'text-gray-400'}`}
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

          {isDragActive ? (
            <p className="text-lg font-medium text-violet-600">{t('dropActive')}</p>
          ) : (
            <>
              <p className="text-lg font-medium text-gray-700 mb-1">{t('dropzone')}</p>
              <p className="text-sm font-medium text-violet-600 mb-3">{t('multipleHint')}</p>
              <div className="flex items-center gap-4 text-xs text-gray-400">
                <span>{SUPPORTED_FORMATS.join(', ')}</span>
                <span className="w-1 h-1 rounded-full bg-gray-300" />
                <span>{t('maxFilesNote', { max: String(MAX_BATCH_FILES) })}</span>
                <span className="w-1 h-1 rounded-full bg-gray-300" />
                <span>{t('maxSizeNote', { size: formatFileSize(MAX_FILE_SIZE) })}</span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Validation Error */}
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
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-medium text-gray-700">
              {hasPending
                ? pendingCount === 1
                  ? t('fileSelected', { size: formatFileSize(totalSize) })
                  : t('filesSelected', { count: String(pendingCount), size: formatFileSize(totalSize) })
                : uploadedFiles.length === 1
                  ? t('fileCount')
                  : t('filesCount', { count: String(uploadedFiles.length) })}
            </p>
            {!isUploading && (
              <button
                type="button"
                onClick={handleClearAll}
                className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
              >
                {t('clearAll')}
              </button>
            )}
          </div>

          <div className="space-y-4">
            {uploadedFiles.map((uf, index) =>
              uf.status === 'pending' ? (
                <div
                  key={`${uf.file.name}-${index}`}
                  className="flex items-center gap-3 p-3 bg-white rounded-2xl border border-gray-200 shadow-sm"
                >
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center">
                    {uf.preview ? (
                      // eslint-disable-next-line @next/next/no-img-element
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
                    aria-label={t('removeFile')}
                  >
                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ) : (
                <div
                  key={`${uf.file.name}-${index}`}
                  className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden"
                >
                  <div className="flex">
                    <div className="flex-shrink-0 w-48 bg-gray-50 border-r border-gray-100 flex flex-col items-center justify-center p-5 gap-3">
                      <div className="w-28 h-36 rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center shadow-inner">
                        {uf.preview ? (
                          // eslint-disable-next-line @next/next/no-img-element
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

                    <div className="flex-1 p-6 flex flex-col justify-center">
                      <PipelineStepper
                        currentStatus={toPipelineStatus(uf.status)}
                        errorMessage={uf.error}
                        invoiceId={uf.jobId}
                      />

                      {/* Progress bar for queued/processing */}
                      {(uf.status === 'uploaded' || uf.status === 'processing') && (
                        <div className="mt-4">
                          <div className="flex items-center gap-3">
                            <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-gradient-to-r from-violet-500 to-violet-600 rounded-full transition-all duration-500 ease-out"
                                style={{ width: `${Math.max(uf.progress, uf.status === 'processing' ? 5 : 0)}%` }}
                              />
                            </div>
                            <span className="text-xs font-semibold text-violet-600 tabular-nums w-10 text-right">
                              {uf.progress}%
                            </span>
                          </div>
                          <div className="mt-1.5 flex items-center gap-2">
                            <svg className="animate-spin h-3.5 w-3.5 text-violet-500" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                            </svg>
                            <p className="text-xs text-gray-500">
                              {uf.status === 'uploaded' ? t('waitingForProcessing') : getStageText(uf.stage)}
                            </p>
                          </div>
                        </div>
                      )}

                      {/* Success state */}
                      {uf.status === 'success' && (
                        <div className="mt-4 flex items-center justify-center gap-2">
                          {isSingleFileRedirecting ? (
                            <>
                              <svg className="animate-spin h-4 w-4 text-violet-600" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                              </svg>
                              <p className="text-sm text-violet-600">{t('redirecting')}</p>
                            </>
                          ) : (
                            <p className="text-sm text-green-600">{t('processingComplete')}</p>
                          )}
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
            className="px-6 py-3 bg-violet-600 text-white font-medium rounded-xl hover:bg-violet-700 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:ring-offset-2 transition-colors"
          >
            {pendingCount === 1
              ? t('processOne')
              : t('processMultiple', { count: String(pendingCount) })}
          </button>
        </div>
      )}

      {/* Upload More Button — hidden during single-file auto-redirect */}
      {allDone && !isSingleFileRedirecting && (
        <div className="mt-6 flex justify-center">
          <button
            type="button"
            onClick={handleClearAll}
            className="px-6 py-3 bg-gray-100 text-gray-700 font-medium rounded-xl hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors"
          >
            {t('uploadMore')}
          </button>
        </div>
      )}
    </div>
  );
}
