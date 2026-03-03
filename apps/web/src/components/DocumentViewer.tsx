'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

interface DocumentViewerProps {
  url: string | null;
}

/**
 * Document viewer for PDF and image files with zoom and rotate controls.
 *
 * Uses native <img> for images and <iframe> for PDFs.
 */
export function DocumentViewer({ url }: DocumentViewerProps) {
  const t = useTranslations('detail');
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);

  if (!url) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-gray-50 rounded-xl p-8">
        <svg className="w-16 h-16 text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <p className="text-sm text-gray-400">{t('noDocument')}</p>
      </div>
    );
  }

  const isPdf = (() => {
    try {
      return new URL(url).pathname.toLowerCase().endsWith('.pdf');
    } catch {
      return url.toLowerCase().includes('.pdf');
    }
  })();

  function zoomIn() {
    setZoom((z) => Math.min(z + 0.25, 4));
  }

  function zoomOut() {
    setZoom((z) => Math.max(z - 0.25, 0.25));
  }

  function zoomFit() {
    setZoom(1);
    setRotation(0);
  }

  function rotate() {
    setRotation((r) => (r + 90) % 360);
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-1 px-3 py-2 bg-gray-50 border-b border-gray-200 rounded-t-xl">
        <button
          onClick={zoomOut}
          className="p-1.5 rounded-lg text-gray-500 hover:bg-gray-200 hover:text-gray-700 transition-colors"
          title={t('zoomOut')}
          aria-label={t('zoomOut')}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
          </svg>
        </button>
        <span className="text-xs text-gray-500 min-w-[48px] text-center font-mono">
          {Math.round(zoom * 100)}%
        </span>
        <button
          onClick={zoomIn}
          className="p-1.5 rounded-lg text-gray-500 hover:bg-gray-200 hover:text-gray-700 transition-colors"
          title={t('zoomIn')}
          aria-label={t('zoomIn')}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7" />
          </svg>
        </button>
        <div className="w-px h-4 bg-gray-300 mx-1" />
        <button
          onClick={zoomFit}
          className="p-1.5 rounded-lg text-gray-500 hover:bg-gray-200 hover:text-gray-700 transition-colors"
          title={t('zoomFit')}
          aria-label={t('zoomFit')}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
        </button>
        <button
          onClick={rotate}
          className="p-1.5 rounded-lg text-gray-500 hover:bg-gray-200 hover:text-gray-700 transition-colors"
          title={t('rotate')}
          aria-label={t('rotate')}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto bg-gray-100 rounded-b-xl">
        {isPdf ? (
          <iframe
            src={`${url}#toolbar=0`}
            className="w-full h-full border-0"
            title="Invoice PDF"
            style={{
              transform: `scale(${zoom}) rotate(${rotation}deg)`,
              transformOrigin: 'top left',
              width: `${100 / zoom}%`,
              height: `${100 / zoom}%`,
            }}
          />
        ) : (
          <div className="flex items-center justify-center min-h-full p-4">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={url}
              alt="Invoice document"
              className="max-w-full transition-transform duration-200"
              style={{
                transform: `scale(${zoom}) rotate(${rotation}deg)`,
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
