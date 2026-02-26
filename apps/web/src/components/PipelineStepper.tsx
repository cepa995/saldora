'use client';

import { useTranslations } from 'next-intl';

/**
 * Visual pipeline stepper showing invoice processing stages.
 *
 * Stages: Otpremanje -> Na čekanju -> OCR obrada -> Pregled -> Izvoz
 * Each step can be completed, active (pulsing), pending, waiting, or error.
 */

export type PipelineStatus =
  | 'uploading'
  | 'uploaded'
  | 'queued'
  | 'processing'
  | 'completed'
  | 'review'
  | 'verified'
  | 'exported'
  | 'error';

interface PipelineStep {
  key: string;
  labelKey: string;
  descKey: string;
}

const PIPELINE_STEPS: PipelineStep[] = [
  { key: 'upload', labelKey: 'uploading', descKey: 'stepDescUpload' },
  { key: 'queued', labelKey: 'queued', descKey: 'stepDescQueued' },
  { key: 'processing', labelKey: 'ocrProcessing', descKey: 'stepDescProcessing' },
  { key: 'review', labelKey: 'review', descKey: 'stepDescReview' },
  { key: 'export', labelKey: 'exportStep', descKey: 'stepDescExport' },
];

const STATUS_TO_ACTIVE_INDEX: Record<PipelineStatus, number> = {
  uploading: 0,
  uploaded: 0,
  queued: 1,
  processing: 2,
  completed: 3,
  review: 3,
  verified: 4,
  exported: 5,
  error: -1,
};

interface PipelineStepperProps {
  currentStatus: PipelineStatus;
  errorMessage?: string;
}

type StepState = 'completed' | 'active' | 'pending' | 'waiting' | 'error';

function getStepStates(currentStatus: PipelineStatus): StepState[] {
  if (currentStatus === 'error') {
    return PIPELINE_STEPS.map(() => 'error');
  }

  const activeIndex = STATUS_TO_ACTIVE_INDEX[currentStatus];

  if (currentStatus === 'uploaded') {
    return PIPELINE_STEPS.map((_, i) => (i === 0 ? 'completed' : 'waiting'));
  }

  return PIPELINE_STEPS.map((_, i) => {
    if (i < activeIndex) return 'completed';
    if (i === activeIndex) return 'active';
    return 'pending';
  });
}

function UploadStepIcon({ className }: { className: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
    </svg>
  );
}

function QueueStepIcon({ className }: { className: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function ScanStepIcon({ className }: { className: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  );
}

function ReviewStepIcon({ className }: { className: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
    </svg>
  );
}

function ExportStepIcon({ className }: { className: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    </svg>
  );
}

function CheckStepIcon({ className }: { className: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
    </svg>
  );
}

function ErrorStepIcon({ className }: { className: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

const STEP_ICONS = [UploadStepIcon, QueueStepIcon, ScanStepIcon, ReviewStepIcon, ExportStepIcon];

function StepCircle({ state, index }: { state: StepState; index: number }) {
  const Icon = STEP_ICONS[index];
  const size = 'w-12 h-12';
  const iconSize = 'w-5 h-5';

  if (state === 'completed') {
    return (
      <div className={`${size} rounded-full bg-violet-600 flex items-center justify-center shadow-md shadow-violet-200`}>
        <CheckStepIcon className={`${iconSize} text-white`} />
      </div>
    );
  }

  if (state === 'active') {
    return (
      <div className="relative flex items-center justify-center">
        <div className={`absolute ${size} rounded-full bg-violet-400 animate-pulse-soft opacity-40`} />
        <div className={`absolute w-16 h-16 rounded-full bg-violet-300 opacity-20 animate-ping`} />
        <div className={`${size} rounded-full bg-gradient-to-br from-violet-500 to-violet-700 flex items-center justify-center relative shadow-lg shadow-violet-300`}>
          <Icon className={`${iconSize} text-white`} />
        </div>
      </div>
    );
  }

  if (state === 'error') {
    return (
      <div className={`${size} rounded-full bg-red-500 flex items-center justify-center shadow-md shadow-red-200`}>
        <ErrorStepIcon className={`${iconSize} text-white`} />
      </div>
    );
  }

  if (state === 'waiting') {
    return (
      <div className={`${size} rounded-full bg-amber-100 border-2 border-amber-300 border-dashed flex items-center justify-center`}>
        <Icon className={`${iconSize} text-amber-500`} />
      </div>
    );
  }

  return (
    <div className={`${size} rounded-full bg-gray-100 border-2 border-gray-200 flex items-center justify-center`}>
      <Icon className={`${iconSize} text-gray-400`} />
    </div>
  );
}

function ConnectorLine({ leftState, rightState }: { leftState: StepState; rightState: StepState }) {
  const isActive =
    leftState === 'completed' && (rightState === 'completed' || rightState === 'active');

  return (
    <div className="flex-1 h-1 mx-2 rounded-full overflow-hidden">
      {isActive ? (
        <div className="h-full bg-gradient-to-r from-violet-500 to-violet-600 rounded-full transition-all duration-700" />
      ) : (
        <div className="h-full bg-gray-200 rounded-full" />
      )}
    </div>
  );
}

export function PipelineStepper({ currentStatus, errorMessage }: PipelineStepperProps) {
  const t = useTranslations('upload');
  const stepStates = getStepStates(currentStatus);

  return (
    <div className="w-full">
      <div className="flex items-start">
        {PIPELINE_STEPS.map((step, i) => (
          <div key={step.key} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center min-w-[72px]">
              <StepCircle state={stepStates[i]} index={i} />

              <span
                className={`mt-3 text-xs font-semibold text-center whitespace-nowrap tracking-wide ${
                  stepStates[i] === 'completed' || stepStates[i] === 'active'
                    ? 'text-violet-700'
                    : stepStates[i] === 'error'
                      ? 'text-red-600'
                      : stepStates[i] === 'waiting'
                        ? 'text-amber-600'
                        : 'text-gray-400'
                }`}
              >
                {t(step.labelKey)}
              </span>

              <span
                className={`mt-0.5 text-[11px] text-center transition-opacity duration-300 ${
                  stepStates[i] === 'active'
                    ? 'text-violet-500 opacity-100'
                    : stepStates[i] === 'completed'
                      ? 'text-violet-400 opacity-100'
                      : stepStates[i] === 'waiting'
                        ? 'text-amber-400 opacity-100'
                        : stepStates[i] === 'error'
                          ? 'text-red-400 opacity-100'
                          : 'text-gray-300 opacity-0'
                }`}
              >
                {stepStates[i] === 'waiting' ? t('waitingForService') : t(step.descKey)}
              </span>
            </div>

            {i < PIPELINE_STEPS.length - 1 && (
              <div className="flex-1 pt-[22px]">
                <ConnectorLine leftState={stepStates[i]} rightState={stepStates[i + 1]} />
              </div>
            )}
          </div>
        ))}
      </div>

      {currentStatus === 'error' && errorMessage && (
        <div className="mt-5 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
          <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd" />
          </svg>
          <p className="text-sm text-red-700">{errorMessage}</p>
        </div>
      )}
    </div>
  );
}
