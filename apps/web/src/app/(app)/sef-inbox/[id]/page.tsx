"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/AuthContext";
import {
  fetchSefInvoice,
  processSefInvoice,
  rejectSefInvoice,
  archiveSefInvoice,
} from "@/lib/api/sef";
import { formatDateSr, formatAmountSr } from "@/lib/formatters";
import type { SefInvoice, SefStatus } from "@/lib/types/sef";

const SEF_STATUS_CONFIG: Record<
  SefStatus,
  { dotClass: string; badgeClass: string; labelKey: string }
> = {
  new: {
    dotClass: "bg-blue-500",
    badgeClass: "bg-blue-50 text-blue-700 ring-1 ring-blue-600/20",
    labelKey: "statusNew",
  },
  pending: {
    dotClass: "bg-amber-500",
    badgeClass: "bg-amber-50 text-amber-700 ring-1 ring-amber-600/20",
    labelKey: "statusPending",
  },
  processed: {
    dotClass: "bg-green-500",
    badgeClass: "bg-green-50 text-green-700 ring-1 ring-green-600/20",
    labelKey: "statusProcessed",
  },
  rejected: {
    dotClass: "bg-red-500",
    badgeClass: "bg-red-50 text-red-700 ring-1 ring-red-600/20",
    labelKey: "statusRejected",
  },
  archived: {
    dotClass: "bg-gray-400",
    badgeClass: "bg-gray-50 text-gray-600 ring-1 ring-gray-500/20",
    labelKey: "statusArchived",
  },
};

export default function SefInvoiceDetailPage() {
  const params = useParams();
  const { hasRole } = useAuth();
  const t = useTranslations("sef");
  const tCommon = useTranslations("common");
  const id = params.id as string;
  const canWrite = hasRole("operator");

  const [invoice, setInvoice] = useState<SefInvoice | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState<"process" | "reject" | null>(
    null,
  );

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchSefInvoice(id);
      setInvoice(data);
    } catch {
      setError("Greška pri učitavanju SEF fakture");
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleProcess() {
    setActionLoading("process");
    try {
      const updated = await processSefInvoice(id);
      setInvoice(updated);
      setShowConfirm(null);
    } catch {
      setError("Greška pri obradi SEF fakture");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleReject() {
    setActionLoading("reject");
    try {
      const updated = await rejectSefInvoice(id);
      setInvoice(updated);
      setShowConfirm(null);
    } catch {
      setError("Greška pri odbijanju SEF fakture");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleArchive() {
    setActionLoading("archive");
    try {
      const updated = await archiveSefInvoice(id);
      setInvoice(updated);
    } catch {
      setError("Greška pri arhiviranju SEF fakture");
    } finally {
      setActionLoading(null);
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-40 bg-gray-100 rounded animate-pulse" />
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
          <div className="space-y-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex gap-4">
                <div className="w-32 h-5 bg-gray-100 rounded animate-pulse" />
                <div className="w-48 h-5 bg-gray-100 rounded animate-pulse" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error && !invoice) {
    return (
      <div className="space-y-6">
        <Link
          href="/sef-inbox"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          {t("backToInbox")}
        </Link>
        <div className="flex items-center gap-3 px-4 py-3 bg-red-50 rounded-xl border border-red-100">
          <svg
            className="w-5 h-5 text-red-500 shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span className="text-sm text-red-700">{error}</span>
          <button
            onClick={load}
            className="ml-auto text-sm font-medium text-red-700 hover:text-red-800"
          >
            {tCommon("retry")}
          </button>
        </div>
      </div>
    );
  }

  if (!invoice) return null;

  const statusConfig = SEF_STATUS_CONFIG[invoice.status];
  const canProcess = invoice.status === "new" || invoice.status === "pending";
  const canReject = invoice.status === "new" || invoice.status === "pending";
  const canReprocess = invoice.status === "rejected";
  const canArchive = invoice.status !== "archived";

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link
        href="/sef-inbox"
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 19l-7-7 7-7"
          />
        </svg>
        {t("backToInbox")}
      </Link>

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-3 px-4 py-3 bg-red-50 rounded-xl border border-red-100">
          <svg
            className="w-5 h-5 text-red-500 shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900">
            {t("invoiceDetail")}
          </h1>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${statusConfig.badgeClass}`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${statusConfig.dotClass}`}
            />
            {t(statusConfig.labelKey)}
          </span>
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {canWrite && (canProcess || canReprocess) && (
            <button
              onClick={() => setShowConfirm("process")}
              disabled={!!actionLoading}
              className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-xl hover:bg-green-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              {canReprocess ? t("reprocess") : t("process")}
            </button>
          )}
          {canWrite && canReject && (
            <button
              onClick={() => setShowConfirm("reject")}
              disabled={!!actionLoading}
              className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-xl hover:bg-red-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <svg
                className="w-4 h-4"
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
              {t("reject")}
            </button>
          )}
          {canWrite && canArchive && (
            <button
              onClick={handleArchive}
              disabled={!!actionLoading}
              className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-xl hover:bg-gray-200 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
                />
              </svg>
              {t("archive")}
            </button>
          )}
          {invoice.status === "processed" && invoice.processed_invoice_id && (
            <Link
              href={`/invoices/${invoice.processed_invoice_id}`}
              className="inline-flex items-center gap-2 px-4 py-2 bg-violet-600 text-white text-sm font-medium rounded-xl hover:bg-violet-700 transition-colors"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                />
              </svg>
              {t("viewInvoice")}
            </Link>
          )}
        </div>
      </div>

      {/* Invoice details card */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 sm:p-8">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <DetailField label={t("sefId")} value={invoice.sef_id} mono />
          <DetailField
            label={t("columnInvoiceNumber")}
            value={invoice.invoice_number || t("noInvoiceNumber")}
            mono
          />
          <DetailField
            label={t("invoiceDate")}
            value={formatDateSr(invoice.invoice_date)}
          />
          <DetailField
            label={t("receivedAt")}
            value={formatDateSr(invoice.received_at)}
          />
          <DetailField
            label={t("supplierName")}
            value={invoice.supplier_name || t("noSupplier")}
          />
          <DetailField
            label={t("supplierPib")}
            value={invoice.supplier_pib || "—"}
            mono
          />
          <DetailField
            label={t("amount")}
            value={formatAmountSr(invoice.amount, invoice.currency)}
            highlight
          />
          <DetailField label={t("currency")} value={invoice.currency} />
        </div>

        {/* Linked invoice */}
        {invoice.processed_invoice_id && (
          <div className="mt-6 pt-6 border-t border-gray-100">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-500">
                {t("linkedInvoice")}:
              </span>
              <Link
                href={`/invoices/${invoice.processed_invoice_id}`}
                className="text-sm font-medium text-violet-600 hover:text-violet-700 transition-colors"
              >
                {invoice.processed_invoice_id}
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* Confirmation modals */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/30 backdrop-blur-sm"
            onClick={() => setShowConfirm(null)}
          />
          <div className="relative bg-white rounded-2xl shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {showConfirm === "process"
                ? t("processConfirmTitle")
                : t("rejectConfirmTitle")}
            </h3>
            <p className="text-sm text-gray-600 mb-6">
              {showConfirm === "process"
                ? t("processConfirmMessage")
                : t("rejectConfirmMessage")}
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowConfirm(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-xl transition-colors"
              >
                {tCommon("cancel")}
              </button>
              <button
                onClick={
                  showConfirm === "process" ? handleProcess : handleReject
                }
                disabled={!!actionLoading}
                className={`px-4 py-2 text-sm font-medium text-white rounded-xl transition-colors disabled:opacity-60 ${
                  showConfirm === "process"
                    ? "bg-green-600 hover:bg-green-700"
                    : "bg-red-600 hover:bg-red-700"
                }`}
              >
                {actionLoading
                  ? tCommon("loading")
                  : showConfirm === "process"
                    ? tCommon("confirm")
                    : tCommon("confirm")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function DetailField({
  label,
  value,
  mono = false,
  highlight = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
  highlight?: boolean;
}) {
  return (
    <div>
      <dt className="text-sm font-medium text-gray-500 mb-1">{label}</dt>
      <dd
        className={`text-sm ${
          highlight ? "text-lg font-semibold text-gray-900" : "text-gray-900"
        } ${mono ? "font-mono" : ""}`}
      >
        {value}
      </dd>
    </div>
  );
}
