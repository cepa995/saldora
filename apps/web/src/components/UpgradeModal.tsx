"use client";

import { useEffect, useRef } from "react";
import { useOrgPath } from "@/lib/navigation";

export interface PlanErrorInfo {
  detail: string;
  code:
    | "invoice_limit_exceeded"
    | "member_limit_exceeded"
    | "feature_unavailable";
  plan: string;
  limit?: number;
  usage?: number;
  required_plan?: string;
}

interface UpgradeModalProps {
  error: PlanErrorInfo;
  onClose: () => void;
}

interface UpgradePlanInfo {
  label: string;
  price: number;
  invoiceLimit: number;
  userLimit: number;
  features: string[];
}

const UPGRADE_PLANS: Record<string, UpgradePlanInfo> = {
  starter: {
    label: "Starter",
    price: 29,
    invoiceLimit: 100,
    userLimit: 2,
    features: [
      "OCR obrada faktura",
      "Excel/CSV izvoz",
      "MiniMax XML izvoz",
      "NBS kursna lista",
    ],
  },
  pro: {
    label: "Pro",
    price: 79,
    invoiceLimit: 400,
    userLimit: 5,
    features: [
      "Sve iz Starter plana",
      "SEF integracija",
      "Automatsko knjiženje",
      "MiniMax direktan import",
      "Revizorski izvoz",
    ],
  },
  agency: {
    label: "Agency",
    price: 199,
    invoiceLimit: 1500,
    userLimit: 15,
    features: [
      "Sve iz Pro plana",
      "Automatizovana pravila",
      "Prioritetna podrška",
    ],
  },
};

const PLAN_LABELS: Record<string, string> = {
  free: "Free",
  starter: "Starter",
  pro: "Pro",
  agency: "Agency",
};

function CheckIcon() {
  return (
    <svg
      className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2.5}
        d="M5 13l4 4L19 7"
      />
    </svg>
  );
}

export function UpgradeModal({ error, onClose }: UpgradeModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const orgPath = useOrgPath();

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (dialogRef.current && !dialogRef.current.contains(e.target as Node)) {
      onClose();
    }
  };

  const isQuota =
    error.code === "invoice_limit_exceeded" ||
    error.code === "member_limit_exceeded";

  const icon = isQuota ? (
    <svg
      className="w-10 h-10 text-amber-500"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
      />
    </svg>
  ) : (
    <svg
      className="w-10 h-10 text-violet-500"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
      />
    </svg>
  );

  const title = isQuota
    ? "Dostigli ste limit plana"
    : "Funkcionalnost zaključana";

  const currentPlanLabel = PLAN_LABELS[error.plan] || error.plan;
  const targetPlanKey = error.required_plan?.toLowerCase();
  const targetPlan = targetPlanKey ? UPGRADE_PLANS[targetPlanKey] : undefined;
  const ctaLabel = targetPlan
    ? `Nadogradite na ${targetPlan.label}`
    : "Nadogradite plan";

  return (
    <div
      className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50"
      onClick={handleBackdropClick}
    >
      <div
        ref={dialogRef}
        className="bg-white rounded-2xl shadow-2xl max-w-lg w-full mx-4 p-6"
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            {icon}
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
              <p className="text-xs text-gray-400 mt-0.5">
                Trenutni plan: {currentPlanLabel}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Message */}
        <p className="text-sm text-gray-600 mb-4">{error.detail}</p>

        {/* Usage bar for quota errors */}
        {isQuota && error.limit != null && error.usage != null && (
          <div className="mb-4">
            <div className="flex items-center justify-between text-xs text-gray-500 mb-1.5">
              <span>Iskorišćeno</span>
              <span className="font-medium text-gray-700">
                {error.usage} / {error.limit}
              </span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
              <div
                className="h-2 rounded-full bg-gradient-to-r from-amber-400 to-red-500 transition-all"
                style={{
                  width: `${Math.min(Math.round((error.usage / error.limit) * 100), 100)}%`,
                }}
              />
            </div>
          </div>
        )}

        {/* Target plan card */}
        {targetPlan && (
          <div className="border-l-4 border-violet-500 bg-violet-50/60 rounded-xl p-4 mb-5">
            {/* Plan header */}
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-base font-bold text-gray-900">
                  {targetPlan.label} plan
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  {targetPlan.invoiceLimit} faktura/mes. &middot;{" "}
                  {targetPlan.userLimit} korisnika
                </p>
              </div>
              <div className="text-right">
                <span className="text-2xl font-bold text-gray-900">
                  &euro;{targetPlan.price}
                </span>
                <span className="text-xs text-gray-500">/mes.</span>
              </div>
            </div>

            {/* Features */}
            <ul className="space-y-2">
              {targetPlan.features.map((feature) => (
                <li key={feature} className="flex items-center gap-2.5">
                  <div className="w-5 h-5 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0">
                    <CheckIcon />
                  </div>
                  <span className="text-sm text-gray-700">{feature}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Fallback for unknown plan */}
        {!targetPlan && error.required_plan && (
          <div className="bg-gray-50 rounded-xl p-4 mb-5">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">Potreban plan</span>
              <span className="font-medium text-violet-600">
                {error.required_plan}
              </span>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors"
          >
            Zatvori
          </button>
          <a
            href={orgPath("/billing")}
            className="flex-1 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 rounded-xl transition-all text-center shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40"
          >
            {ctaLabel}
          </a>
        </div>
      </div>
    </div>
  );
}
