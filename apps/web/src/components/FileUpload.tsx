'use client';

import { useCallback, useState, InputHTMLAttributes } from 'react';
import { useDropzone, FileRejection } from 'react-dropzone';
import { apiClient } from '@/lib/api-client';

// FR-4.2.1: Supported formats and size limits
const ACCEPTED_FILE_TYPES = {
  'application/pdf': ['.pdf'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
  'image/tiff': ['.tiff', '.tif'],
  'image/bmp': ['.bmp'],
  'image/webp': ['.webp'],
};

const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20 MB

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

interface FileUploadProps {
  onFileAccepted?: (file: File) => void;
  onUploadStart?: (file: File) => void;
  onUploadComplete?: (file: File, jobId: string) => void;
  onError?: (error: string) => void;
  disabled?: boolean;
}

export function FileUpload({
  onFileAccepted,
  onUploadStart,
  onUploadComplete,
  onError,
  disabled = false,
}: FileUploadProps) {
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Format file size for display
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

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
        const rejection = fileRejections[0];
        const errors = rejection.errors;

        if (errors.some((e) => e.code === 'file-too-large')) {
          const errorMsg = `Fajl je prevelik. Maksimalna veličina je ${formatFileSize(MAX_FILE_SIZE)}.`;
          setValidationError(errorMsg);
          onError?.(errorMsg);
        } else if (errors.some((e) => e.code === 'file-invalid-type')) {
          const errorMsg = `Nepodržan format fajla. Podržani formati: ${SUPPORTED_FORMATS.join(', ')}.`;
          setValidationError(errorMsg);
          onError?.(errorMsg);
        } else {
          const errorMsg = 'Greška pri učitavanju fajla.';
          setValidationError(errorMsg);
          onError?.(errorMsg);
        }
        return;
      }

      // Handle accepted file
      if (acceptedFiles.length > 0) {
        const file = acceptedFiles[0];

        // Cleanup previous preview URL if exists
        if (uploadedFile?.preview) {
          URL.revokeObjectURL(uploadedFile.preview);
        }

        const newUploadedFile: UploadedFile = {
          file,
          preview: generatePreview(file),
          status: 'pending',
          progress: 0,
        };

        setUploadedFile(newUploadedFile);
        onFileAccepted?.(file);
      }
    },
    [uploadedFile, onFileAccepted, onError]
  );

  // Configure dropzone - using type assertion to work around React 19 compatibility
  const dropzoneConfig = {
    onDrop,
    accept: ACCEPTED_FILE_TYPES,
    maxSize: MAX_FILE_SIZE,
    maxFiles: 1,
    multiple: false,
    disabled: disabled || uploadedFile?.status === 'uploading' || uploadedFile?.status === 'uploaded',
  };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { getRootProps, getInputProps, isDragActive, isDragAccept, isDragReject } = useDropzone(dropzoneConfig as any);

  // Upload file to API
  const handleUpload = async () => {
    if (!uploadedFile) return;

    setUploadedFile((prev) => (prev ? { ...prev, status: 'uploading', progress: 0 } : null));
    onUploadStart?.(uploadedFile.file);

    try {
      const formData = new FormData();
      formData.append('file', uploadedFile.file);

      const data = await apiClient<{ id: string }>('/api/v1/invoices/upload', {
        method: 'POST',
        body: formData,
      });

      setUploadedFile((prev) =>
        prev
          ? {
              ...prev,
              status: 'uploaded',
              progress: 100,
              jobId: data.id,
            }
          : null
      );

      onUploadComplete?.(uploadedFile.file, data.id);
    } catch (error) {
      const errorMsg =
        error && typeof error === 'object' && 'message' in error
          ? String((error as { message: string }).message)
          : 'Greška pri slanju fajla.';
      setUploadedFile((prev) =>
        prev
          ? {
              ...prev,
              status: 'error',
              error: errorMsg,
            }
          : null
      );
      onError?.(errorMsg);
    }
  };

  // Remove uploaded file
  const handleRemove = () => {
    if (uploadedFile?.preview) {
      URL.revokeObjectURL(uploadedFile.preview);
    }
    setUploadedFile(null);
    setValidationError(null);
  };

  // Determine dropzone styling based on state
  const getDropzoneClassName = (): string => {
    const baseClasses =
      'relative flex flex-col items-center justify-center w-full min-h-[300px] p-8 border-2 border-dashed rounded-2xl cursor-pointer transition-all duration-200';

    if (disabled) {
      return `${baseClasses} border-gray-200 bg-gray-50 cursor-not-allowed`;
    }

    if (isDragReject) {
      return `${baseClasses} border-red-400 bg-red-50`;
    }

    if (isDragAccept) {
      return `${baseClasses} border-green-400 bg-green-50`;
    }

    if (isDragActive) {
      return `${baseClasses} border-blue-400 bg-blue-50`;
    }

    if (uploadedFile) {
      return `${baseClasses} border-gray-300 bg-gray-50`;
    }

    return `${baseClasses} border-gray-300 bg-white hover:border-blue-400 hover:bg-blue-50`;
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Dropzone Area */}
      <div {...getRootProps({ className: getDropzoneClassName() })}>
        <input {...(getInputProps() as InputHTMLAttributes<HTMLInputElement>)} />

        {!uploadedFile ? (
          // Empty state - show drop instructions
          <div className="flex flex-col items-center text-center">
            {/* Upload Icon */}
            <div className="mb-4">
              <svg
                className={`w-16 h-16 ${isDragActive ? 'text-blue-500' : 'text-gray-400'}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
            </div>

            {/* Instructions */}
            {isDragActive ? (
              <p className="text-lg font-medium text-blue-600">Pustite fajl ovde...</p>
            ) : (
              <>
                <p className="text-lg font-medium text-gray-700 mb-2">
                  Prevucite fakturu ovde ili kliknite za odabir
                </p>
                <p className="text-sm text-gray-500">
                  Podržani formati: {SUPPORTED_FORMATS.join(', ')}
                </p>
                <p className="text-sm text-gray-500">Maksimalna veličina: {formatFileSize(MAX_FILE_SIZE)}</p>
              </>
            )}
          </div>
        ) : (
          // File selected state - show preview
          <div className="flex flex-col items-center w-full" onClick={(e) => e.stopPropagation()}>
            {/* File Preview */}
            <div className="flex items-center gap-4 p-4 bg-white rounded-xl border border-gray-200 w-full max-w-md">
              {/* Thumbnail/Icon */}
              <div className="flex-shrink-0 w-16 h-16 rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center">
                {uploadedFile.preview ? (
                  // eslint-disable-next-line @next/next/no-img-element -- Using img for blob URL preview
                  <img
                    src={uploadedFile.preview}
                    alt="Preview"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  // PDF Icon
                  <svg className="w-8 h-8 text-red-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zM6 20V4h7v5h5v11H6z" />
                    <path d="M8 12h8v2H8zm0 4h8v2H8z" />
                  </svg>
                )}
              </div>

              {/* File Info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{uploadedFile.file.name}</p>
                <p className="text-sm text-gray-500">{formatFileSize(uploadedFile.file.size)}</p>

                {/* Status Indicator */}
                {uploadedFile.status === 'uploading' && (
                  <div className="mt-2">
                    <div className="w-full bg-gray-200 rounded-full h-1.5">
                      <div
                        className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                        style={{ width: `${uploadedFile.progress}%` }}
                      />
                    </div>
                    <p className="text-xs text-blue-600 mt-1">Slanje...</p>
                  </div>
                )}

                {uploadedFile.status === 'uploaded' && (
                  <div className="flex items-center gap-2 mt-2">
                    <svg className="h-4 w-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <p className="text-xs text-green-600">Uspešno otpremljeno</p>
                  </div>
                )}

                {uploadedFile.status === 'success' && (
                  <div className="flex items-center gap-2 mt-2">
                    <svg className="h-4 w-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <p className="text-xs text-green-600">Uspešno obrađeno</p>
                  </div>
                )}

                {uploadedFile.status === 'error' && (
                  <p className="text-xs text-red-600 mt-2">{uploadedFile.error}</p>
                )}
              </div>

              {/* Remove Button */}
              {uploadedFile.status !== 'uploading' && uploadedFile.status !== 'uploaded' && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemove();
                  }}
                  className="flex-shrink-0 p-1 rounded-full hover:bg-gray-100 transition-colors"
                  aria-label="Ukloni fajl"
                >
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        )}
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

      {/* Upload Button */}
      {uploadedFile && uploadedFile.status === 'pending' && (
        <div className="mt-6 flex justify-center">
          <button
            type="button"
            onClick={handleUpload}
            className="px-6 py-3 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
          >
            Obradi fakturu
          </button>
        </div>
      )}

      {/* Upload Another Button */}
      {uploadedFile && (uploadedFile.status === 'success' || uploadedFile.status === 'error') && (
        <div className="mt-6 flex justify-center">
          <button
            type="button"
            onClick={handleRemove}
            className="px-6 py-3 bg-gray-100 text-gray-700 font-medium rounded-xl hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors"
          >
            Učitaj novu fakturu
          </button>
        </div>
      )}
    </div>
  );
}
