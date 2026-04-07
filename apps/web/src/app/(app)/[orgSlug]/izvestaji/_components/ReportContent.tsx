'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { useTranslations } from 'next-intl';
import { useClient } from '@/contexts/ClientContext';
import {
  fetchReceivedGoods,
  fetchSpendingBySupplier,
  fetchMonthlyBreakdown,
  fetchPriceComparison,
  fetchExpenseSummary,
  fetchKalkulacija,
  fetchRuc,
  fetchCategorySpending,
  fetchOpenItems,
  fetchAging,
  type ReportParams,
  type ReceivedGoodsResponse,
  type SpendingBySupplierResponse,
  type MonthlyBreakdownResponse,
  type PriceComparisonResponse,
  type ExpenseSummaryResponse,
  type KalkulacijaResponse,
  type RucResponse,
  type CategorySpendingResponse,
  type OpenItemsResponse,
  type AgingResponse,
} from '@/lib/api/reports';

// ── Types ────────────────────────────────────────────────────────────

export type TemplateId =
  | 'receivedGoods'
  | 'spendingBySupplier'
  | 'monthlyBreakdown'
  | 'priceComparison'
  | 'expenseSummary'
  | 'kalkulacija'
  | 'ruc'
  | 'categorySpending'
  | 'openItems'
  | 'aging';

type ReportData =
  | ReceivedGoodsResponse
  | SpendingBySupplierResponse
  | MonthlyBreakdownResponse
  | PriceComparisonResponse
  | ExpenseSummaryResponse
  | KalkulacijaResponse
  | RucResponse
  | CategorySpendingResponse
  | OpenItemsResponse
  | AgingResponse
  | null;

// ── Formatting ───────────────────────────────────────────────────────

function fmtAmount(n: number): string {
  return new Intl.NumberFormat('sr-Latn-RS', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n);
}

function fmtNum(n: number | null): string {
  if (n === null || n === undefined) return '—';
  return new Intl.NumberFormat('sr-Latn-RS', { maximumFractionDigits: 4 }).format(n);
}

// ── Loading skeleton ─────────────────────────────────────────────────

function TableSkeleton({ cols }: { cols: number }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden animate-pulse">
      <div className="h-9 bg-gray-50 border-b border-gray-100" />
      {[...Array(5)].map((_, i) => (
        <div key={i} className={`flex gap-3 px-3 py-2.5 border-b border-gray-100 last:border-0 ${i % 2 === 1 ? 'bg-gray-50/40' : ''}`}>
          {[...Array(cols)].map((__, j) => (
            <div
              key={j}
              className="h-4 bg-gray-200 rounded"
              style={{ width: `${Math.floor(60 + Math.random() * 40)}%`, flex: 1 }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

// ── Table head helper ────────────────────────────────────────────────

function TableHead({ cols }: { cols: string[] }) {
  return (
    <thead>
      <tr className="border-b border-gray-200 bg-gray-50/60">
        {cols.map((c) => (
          <th
            key={c}
            className="px-3 py-2 text-left text-[11px] font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap"
          >
            {c}
          </th>
        ))}
      </tr>
    </thead>
  );
}

// ── Results tables ───────────────────────────────────────────────────

function ReceivedGoodsTable({ data, t }: { data: ReceivedGoodsResponse; t: ReturnType<typeof useTranslations<'reports'>> }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <TableHead
            cols={[
              t('description'),
              t('quantity'),
              t('avgPrice'),
              t('total'),
              t('supplierCount'),
              t('suppliers'),
            ]}
          />
          <tbody>
            {data.items.map((row, i) => (
              <tr key={i} className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50 transition-colors">
                <td className="px-3 py-2.5 text-gray-900 font-medium max-w-[220px] truncate">{row.description}</td>
                <td className="px-3 py-2.5 text-gray-700 tabular-nums">{fmtNum(row.total_quantity)}</td>
                <td className="px-3 py-2.5 text-gray-700 tabular-nums">{fmtNum(row.avg_unit_price)}</td>
                <td className="px-3 py-2.5 text-gray-900 font-semibold tabular-nums">{fmtAmount(row.total_amount)}</td>
                <td className="px-3 py-2.5 text-center text-gray-700">{row.supplier_count}</td>
                <td className="px-3 py-2.5 text-gray-500 text-xs max-w-[200px] truncate" title={row.suppliers.join(', ')}>
                  {row.suppliers.join(', ') || '—'}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-gray-200 bg-gray-50/80">
              <td className="px-3 py-2 text-xs font-semibold text-gray-700 uppercase">{t('grandTotal')}</td>
              <td colSpan={2} />
              <td className="px-3 py-2 text-sm font-bold text-violet-700 tabular-nums">{fmtAmount(data.grand_total)}</td>
              <td colSpan={2} />
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

function SpendingBySupplierTable({ data, t }: { data: SpendingBySupplierResponse; t: ReturnType<typeof useTranslations<'reports'>> }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <TableHead cols={[t('sellerName'), t('sellerPib'), t('invoiceCount'), t('total'), t('unpaidAmount')]} />
          <tbody>
            {data.items.map((row, i) => (
              <tr key={i} className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50 transition-colors">
                <td className="px-3 py-2.5 text-gray-900 font-medium">{row.seller_name || '—'}</td>
                <td className="px-3 py-2.5 text-gray-500 font-mono text-xs">{row.seller_pib || '—'}</td>
                <td className="px-3 py-2.5 text-right text-gray-700">{row.invoice_count}</td>
                <td className="px-3 py-2.5 text-right text-gray-900 font-semibold tabular-nums">{fmtAmount(row.total_amount)}</td>
                <td className={`px-3 py-2.5 text-right font-semibold tabular-nums ${row.unpaid_amount > 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {fmtAmount(row.unpaid_amount)}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-gray-200 bg-gray-50/80">
              <td className="px-3 py-2 text-xs font-semibold text-gray-700 uppercase" colSpan={3}>{t('grandTotal')}</td>
              <td className="px-3 py-2 text-right text-sm font-bold text-violet-700 tabular-nums">{fmtAmount(data.grand_total)}</td>
              <td className="px-3 py-2 text-right text-sm font-bold text-red-600 tabular-nums">
                {fmtAmount(data.items.reduce((s, r) => s + r.unpaid_amount, 0))}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

function PaymentBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    paid: 'bg-green-50 text-green-700',
    partially_paid: 'bg-amber-50 text-amber-700',
    unpaid: 'bg-gray-100 text-gray-600',
  };
  const labels: Record<string, string> = {
    paid: 'Plaćeno',
    partially_paid: 'Delimično',
    unpaid: 'Neplaćeno',
  };
  return (
    <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-semibold ${colors[status] || colors.unpaid}`}>
      {labels[status] || labels.unpaid}
    </span>
  );
}

function MonthlyBreakdownTable({ data, t }: { data: MonthlyBreakdownResponse; t: ReturnType<typeof useTranslations<'reports'>> }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <TableHead cols={[t('period'), t('sellerName'), t('description'), t('quantity'), t('unitPrice'), 'PDV %', 'PDV iznos', t('total'), t('paymentStatus')]} />
          <tbody>
            {data.items.map((row, i) => (
              <tr key={i} className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50 transition-colors">
                <td className="px-3 py-2.5 text-gray-500 text-xs whitespace-nowrap">{row.invoice_date || '—'}</td>
                <td className="px-3 py-2.5 text-gray-700 max-w-[150px] truncate">{row.seller_name || '—'}</td>
                <td className="px-3 py-2.5 text-gray-900 max-w-[200px] truncate font-medium">{row.description}</td>
                <td className="px-3 py-2.5 text-right text-gray-700 tabular-nums">{fmtNum(row.quantity)}</td>
                <td className="px-3 py-2.5 text-right text-gray-700 tabular-nums">{fmtNum(row.unit_price)}</td>
                <td className="px-3 py-2.5 text-right text-gray-500 tabular-nums">{row.tax_rate != null ? `${row.tax_rate}%` : '—'}</td>
                <td className="px-3 py-2.5 text-right text-gray-500 tabular-nums">{row.tax_amount != null ? fmtAmount(row.tax_amount) : '—'}</td>
                <td className="px-3 py-2.5 text-right text-gray-900 font-semibold tabular-nums">{fmtAmount(row.total)}</td>
                <td className="px-3 py-2.5 text-center"><PaymentBadge status={row.payment_status} /></td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-gray-200 bg-gray-50/80">
              <td className="px-3 py-2 text-xs font-semibold text-gray-700 uppercase" colSpan={7}>{t('grandTotal')}</td>
              <td className="px-3 py-2 text-right text-sm font-bold text-violet-700 tabular-nums">{fmtAmount(data.total_amount)}</td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

function PriceComparisonTable({ data, t }: { data: PriceComparisonResponse; t: ReturnType<typeof useTranslations<'reports'>> }) {
  // Group flat rows by description for side-by-side comparison
  const grouped = new Map<string, typeof data.items>();
  for (const item of data.items) {
    const key = item.description;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(item);
  }

  return (
    <div className="space-y-3">
      {Array.from(grouped.entries()).map(([desc, rows]) => {
        const allPrices = rows.map((r) => r.avg_unit_price).filter((p): p is number => p != null);
        const globalMin = allPrices.length ? Math.min(...allPrices) : null;
        const globalMax = allPrices.length ? Math.max(...allPrices) : null;
        const globalAvg = allPrices.length ? allPrices.reduce((a, b) => a + b, 0) / allPrices.length : null;

        return (
          <div key={desc} className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 bg-gray-50/60 flex items-center justify-between gap-3">
              <span className="text-sm font-semibold text-gray-900 truncate">{desc}</span>
              <div className="flex items-center gap-3 shrink-0 text-xs text-gray-500">
                <span>min <span className="font-medium text-gray-700">{fmtNum(globalMin)}</span></span>
                <span>avg <span className="font-medium text-gray-700">{fmtNum(globalAvg)}</span></span>
                <span>max <span className="font-medium text-gray-700">{fmtNum(globalMax)}</span></span>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <TableHead cols={[t('sellerName'), t('sellerPib'), 'Min', 'Avg', 'Max', t('invoiceCount')]} />
                <tbody>
                  {rows.map((row, j) => (
                    <tr key={j} className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50 transition-colors">
                      <td className="px-3 py-2.5 text-gray-900 font-medium">{row.seller_name || '—'}</td>
                      <td className="px-3 py-2.5 text-gray-500 font-mono text-xs">{row.seller_pib || '—'}</td>
                      <td className="px-3 py-2.5 text-gray-700 tabular-nums">{fmtNum(row.min_unit_price)}</td>
                      <td className="px-3 py-2.5 text-gray-700 tabular-nums">{fmtNum(row.avg_unit_price)}</td>
                      <td className="px-3 py-2.5 text-gray-700 tabular-nums">{fmtNum(row.max_unit_price)}</td>
                      <td className="px-3 py-2.5 text-center text-gray-700">{row.invoice_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ExpenseSummaryTable({ data, t }: { data: ExpenseSummaryResponse; t: ReturnType<typeof useTranslations<'reports'>> }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden max-w-xl mx-auto">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50/60">
              <th className="px-4 py-2 text-center text-[11px] font-semibold text-gray-500 uppercase tracking-wider">{t('period')}</th>
              <th className="px-4 py-2 text-center text-[11px] font-semibold text-gray-500 uppercase tracking-wider">{t('itemCount')}</th>
              <th className="px-4 py-2 text-center text-[11px] font-semibold text-gray-500 uppercase tracking-wider">{t('total')}</th>
            </tr>
          </thead>
          <tbody>
            {data.buckets.map((row, i) => (
              <tr key={i} className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50 transition-colors">
                <td className="px-4 py-2.5 text-center text-gray-900 font-medium">{row.period}</td>
                <td className="px-4 py-2.5 text-center text-gray-700 tabular-nums">{row.item_count}</td>
                <td className="px-4 py-2.5 text-center text-gray-900 font-semibold tabular-nums">{fmtAmount(row.total_amount)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-gray-200 bg-gray-50/80">
              <td className="px-4 py-2 text-center text-xs font-semibold text-gray-700 uppercase" colSpan={2}>{t('grandTotal')}</td>
              <td className="px-4 py-2 text-center text-sm font-bold text-violet-700 tabular-nums">{fmtAmount(data.grand_total)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

function KalkulacijaTable({ data, t }: { data: KalkulacijaResponse; t: ReturnType<typeof useTranslations<'reports'>> }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <TableHead
            cols={[
              t('description'),
              t('unitOfMeasure'),
              t('quantity'),
              t('purchasePrice'),
              t('purchaseValue'),
              t('marginPct'),
              t('sellingPrice'),
              t('sellingValue'),
            ]}
          />
          <tbody>
            {data.items.map((row, i) => (
              <tr key={i} className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50 transition-colors">
                <td className="px-3 py-2.5 text-gray-900 font-medium max-w-[220px] truncate">{row.description}</td>
                <td className="px-3 py-2.5 text-gray-500 text-xs">{row.unit_of_measure || '—'}</td>
                <td className="px-3 py-2.5 text-gray-700 tabular-nums">{fmtNum(row.quantity)}</td>
                <td className="px-3 py-2.5 text-gray-700 tabular-nums">{fmtNum(row.purchase_price)}</td>
                <td className="px-3 py-2.5 text-gray-700 tabular-nums">{row.purchase_value !== null ? fmtAmount(row.purchase_value) : '—'}</td>
                <td className="px-3 py-2.5 text-gray-700 tabular-nums">{row.margin_pct !== null ? `${fmtNum(row.margin_pct)}%` : '—'}</td>
                <td className="px-3 py-2.5 text-gray-700 tabular-nums">{fmtNum(row.selling_price)}</td>
                <td className="px-3 py-2.5 text-gray-900 font-semibold tabular-nums">{row.selling_value !== null ? fmtAmount(row.selling_value) : '—'}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-gray-200 bg-gray-50/80">
              <td className="px-3 py-2 text-xs font-semibold text-gray-700 uppercase" colSpan={4}>{t('grandTotal')}</td>
              <td className="px-3 py-2 text-sm font-bold text-violet-700 tabular-nums">{fmtAmount(data.total_purchase_value)}</td>
              <td />
              <td />
              <td className="px-3 py-2 text-sm font-bold text-violet-700 tabular-nums">{fmtAmount(data.total_selling_value)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

function RucTable({ data, t }: { data: RucResponse; t: ReturnType<typeof useTranslations<'reports'>> }) {
  function rucBadgeClass(pct: number | null): string {
    if (pct === null) return 'text-gray-500';
    if (pct >= 30) return 'text-green-700 font-semibold';
    if (pct >= 15) return 'text-yellow-700 font-semibold';
    return 'text-red-700 font-semibold';
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <TableHead
            cols={[
              t('description'),
              t('category'),
              t('avgPurchasePrice'),
              t('sellingPrice'),
              t('rucAmount'),
              t('rucPct'),
              t('totalPurchased'),
              t('suppliers'),
            ]}
          />
          <tbody>
            {data.items.map((row, i) => (
              <tr key={i} className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50 transition-colors">
                <td className="px-3 py-2.5 text-gray-900 font-medium max-w-[220px] truncate">{row.description}</td>
                <td className="px-3 py-2.5 text-gray-500 text-xs">{row.category || '—'}</td>
                <td className="px-3 py-2.5 text-gray-700 tabular-nums">{fmtNum(row.avg_purchase_price)}</td>
                <td className="px-3 py-2.5 text-gray-700 tabular-nums">{fmtNum(row.selling_price)}</td>
                <td className="px-3 py-2.5 text-gray-700 tabular-nums">{fmtNum(row.ruc_amount)}</td>
                <td className={`px-3 py-2.5 tabular-nums ${rucBadgeClass(row.ruc_pct)}`}>
                  {row.ruc_pct !== null ? `${fmtNum(row.ruc_pct)}%` : '—'}
                </td>
                <td className="px-3 py-2.5 text-gray-700 tabular-nums">{fmtNum(row.total_purchased_qty)}</td>
                <td className="px-3 py-2.5 text-gray-500 text-xs max-w-[200px] truncate" title={row.suppliers.join(', ')}>
                  {row.suppliers.join(', ') || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CategorySpendingTable({ data, t }: { data: CategorySpendingResponse; t: ReturnType<typeof useTranslations<'reports'>> }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <TableHead
            cols={[
              t('category'),
              t('total'),
              t('itemCount'),
              t('invoiceCount'),
            ]}
          />
          <tbody>
            {data.items.map((row, i) => (
              <tr key={i} className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50 transition-colors">
                <td className="px-3 py-2.5 text-gray-900 font-medium">{row.category}</td>
                <td className="px-3 py-2.5 text-gray-900 font-semibold tabular-nums">{fmtAmount(row.total_amount)}</td>
                <td className="px-3 py-2.5 text-center text-gray-700">{row.item_count}</td>
                <td className="px-3 py-2.5 text-center text-gray-700">{row.invoice_count}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-gray-200 bg-gray-50/80">
              <td className="px-3 py-2 text-xs font-semibold text-gray-700 uppercase">{t('grandTotal')}</td>
              <td className="px-3 py-2 text-sm font-bold text-violet-700 tabular-nums">{fmtAmount(data.grand_total)}</td>
              <td colSpan={2} />
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

function OpenItemsTable({ data, t }: { data: OpenItemsResponse; t: ReturnType<typeof useTranslations<'reports'>> }) {
  return (
    <div className="space-y-3">
      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-white border border-gray-200 rounded-xl px-4 py-3">
          <p className="text-xs text-gray-500">{t('openItemsCount')}</p>
          <p className="text-lg font-bold text-gray-900">{data.count}</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl px-4 py-3">
          <p className="text-xs text-gray-500">{t('totalOpenAmount')}</p>
          <p className="text-lg font-bold text-gray-900">{fmtAmount(data.total_open_amount)}</p>
        </div>
        <div className="bg-white border border-red-200 rounded-xl px-4 py-3">
          <p className="text-xs text-red-500">{t('totalOverdueAmount')}</p>
          <p className="text-lg font-bold text-red-600">{fmtAmount(data.total_overdue_amount)}</p>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <TableHead
              cols={[
                'Br. fakture',
                t('sellerName'),
                'Datum fakture',
                'Valuta',
                t('total'),
                t('remaining'),
                t('paymentStatus'),
                t('daysOverdue'),
              ]}
            />
            <tbody>
              {data.items.map((row, i) => (
                <tr key={i} className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50 transition-colors">
                  <td className="px-3 py-2.5 text-gray-900 font-medium">{row.invoice_number || '—'}</td>
                  <td className="px-3 py-2.5 text-gray-700">{row.seller_name || '—'}</td>
                  <td className="px-3 py-2.5 text-gray-700">{row.invoice_date || '—'}</td>
                  <td className="px-3 py-2.5 text-gray-700">{row.due_date || '—'}</td>
                  <td className="px-3 py-2.5 text-gray-900 tabular-nums">{row.total_amount != null ? fmtAmount(row.total_amount) : '—'}</td>
                  <td className="px-3 py-2.5 text-gray-900 font-semibold tabular-nums">{fmtAmount(row.remaining_amount)}</td>
                  <td className="px-3 py-2.5">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                      row.payment_status === 'partially_paid'
                        ? 'bg-amber-50 text-amber-700'
                        : 'bg-gray-100 text-gray-600'
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${
                        row.payment_status === 'partially_paid' ? 'bg-amber-500' : 'bg-gray-400'
                      }`} />
                      {row.payment_status === 'partially_paid' ? t('partiallyPaid') : t('unpaid')}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-center">
                    {row.days_overdue > 0 ? (
                      <span className="text-red-600 font-medium">{row.days_overdue}</span>
                    ) : (
                      <span className="text-green-600">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function AgingTable({ data, t }: { data: AgingResponse; t: ReturnType<typeof useTranslations<'reports'>> }) {
  const bucketColors: Record<string, string> = {
    '0-30': 'bg-green-50 text-green-700',
    '31-60': 'bg-amber-50 text-amber-700',
    '61-90': 'bg-orange-50 text-orange-700',
    '90+': 'bg-red-50 text-red-700',
  };

  return (
    <div className="space-y-3">
      {/* Summary */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white border border-gray-200 rounded-xl px-4 py-3">
          <p className="text-xs text-gray-500">{t('grandTotal')}</p>
          <p className="text-lg font-bold text-gray-900">{fmtAmount(data.grand_total)}</p>
        </div>
        <div className="bg-white border border-red-200 rounded-xl px-4 py-3">
          <p className="text-xs text-red-500">{t('overdue')}</p>
          <p className="text-lg font-bold text-red-600">{fmtAmount(data.overdue_total)}</p>
        </div>
      </div>

      {/* Buckets */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <TableHead cols={[t('bucket'), t('bucketCount'), t('bucketTotal')]} />
            <tbody>
              {data.buckets.map((b, i) => (
                <tr key={i} className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50 transition-colors">
                  <td className="px-3 py-2.5">
                    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-semibold ${bucketColors[b.bucket] || 'bg-gray-100 text-gray-700'}`}>
                      {b.bucket} {t('daysOverdue').toLowerCase()}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-center text-gray-700">{b.count}</td>
                  <td className="px-3 py-2.5 text-gray-900 font-semibold tabular-nums">{fmtAmount(b.total_amount)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-gray-200 bg-gray-50/80">
                <td className="px-3 py-2 text-xs font-semibold text-gray-700 uppercase">{t('grandTotal')}</td>
                <td className="px-3 py-2 text-center text-gray-700">{data.buckets.reduce((s, b) => s + b.count, 0)}</td>
                <td className="px-3 py-2 text-sm font-bold text-violet-700 tabular-nums">{fmtAmount(data.grand_total)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}

// ── CSV export ───────────────────────────────────────────────────────

function exportToCsv(templateId: TemplateId, data: ReportData) {
  if (!data) return;

  let rows: string[][] = [];

  if (templateId === 'receivedGoods') {
    const d = data as ReceivedGoodsResponse;
    rows = [
      ['Opis', 'Kolicina', 'Prosecna cena', 'Ukupno', 'Br. dobavljaca', 'Dobavljaci'],
      ...d.items.map((r) => [
        r.description,
        String(r.total_quantity ?? ''),
        String(r.avg_unit_price ?? ''),
        String(r.total_amount),
        String(r.supplier_count),
        r.suppliers.join('; '),
      ]),
      ['', '', '', String(d.grand_total), '', ''],
    ];
  } else if (templateId === 'spendingBySupplier') {
    const d = data as SpendingBySupplierResponse;
    rows = [
      ['Dobavljac', 'PIB', 'Br. faktura', 'Ukupno', 'Neplaceno'],
      ...d.items.map((r) => [r.seller_name ?? '', r.seller_pib ?? '', String(r.invoice_count), String(r.total_amount), String(r.unpaid_amount)]),
      ['', '', '', String(d.grand_total), String(d.items.reduce((s, r) => s + r.unpaid_amount, 0))],
    ];
  } else if (templateId === 'monthlyBreakdown') {
    const d = data as MonthlyBreakdownResponse;
    rows = [
      ['Datum', 'Dobavljac', 'PIB', 'Opis', 'Kolicina', 'Jed. cena', 'PDV %', 'PDV iznos', 'Ukupno', 'Status placanja'],
      ...d.items.map((r) => [
        r.invoice_date ?? '',
        r.seller_name ?? '',
        r.seller_pib ?? '',
        r.description,
        String(r.quantity ?? ''),
        String(r.unit_price ?? ''),
        String(r.tax_rate ?? ''),
        String(r.tax_amount ?? ''),
        String(r.total),
        r.payment_status === 'paid' ? 'Placeno' : r.payment_status === 'partially_paid' ? 'Delimicno' : 'Neplaceno',
      ]),
      ['', '', '', '', '', '', '', '', String(d.total_amount)],
    ];
  } else if (templateId === 'priceComparison') {
    const d = data as PriceComparisonResponse;
    rows = [['Opis', 'Dobavljac', 'PIB', 'Min', 'Avg', 'Max', 'Br. faktura']];
    for (const item of d.items) {
      rows.push([
        item.description,
        item.seller_name ?? '',
        item.seller_pib ?? '',
        String(item.min_unit_price ?? ''),
        String(item.avg_unit_price ?? ''),
        String(item.max_unit_price ?? ''),
        String(item.invoice_count),
      ]);
    }
  } else if (templateId === 'expenseSummary') {
    const d = data as ExpenseSummaryResponse;
    rows = [
      ['Period', 'Br. stavki', 'Ukupno'],
      ...d.buckets.map((r) => [r.period, String(r.item_count), String(r.total_amount)]),
      ['', '', String(d.grand_total)],
    ];
  } else if (templateId === 'kalkulacija') {
    const d = data as KalkulacijaResponse;
    rows = [
      ['Naziv', 'J.M.', 'Kolicina', 'Nab. cena', 'Nab. vrednost', 'Marza %', 'Prod. cena', 'Prod. vrednost'],
      ...d.items.map((r) => [
        r.description,
        r.unit_of_measure ?? '',
        String(r.quantity ?? ''),
        String(r.purchase_price ?? ''),
        String(r.purchase_value ?? ''),
        String(r.margin_pct ?? ''),
        String(r.selling_price ?? ''),
        String(r.selling_value ?? ''),
      ]),
      ['', '', '', '', String(d.total_purchase_value), '', '', String(d.total_selling_value)],
    ];
  } else if (templateId === 'ruc') {
    const d = data as RucResponse;
    rows = [
      ['Proizvod', 'Kategorija', 'Prosecna nab. cena', 'Prod. cena', 'RUC iznos', 'RUC %', 'Ukupno nabavljeno', 'Dobavljaci'],
      ...d.items.map((r) => [
        r.description,
        r.category ?? '',
        String(r.avg_purchase_price ?? ''),
        String(r.selling_price ?? ''),
        String(r.ruc_amount ?? ''),
        String(r.ruc_pct ?? ''),
        String(r.total_purchased_qty ?? ''),
        r.suppliers.join('; '),
      ]),
    ];
  } else if (templateId === 'categorySpending') {
    const d = data as CategorySpendingResponse;
    rows = [
      ['Kategorija', 'Ukupan iznos', 'Broj artikala', 'Broj faktura'],
      ...d.items.map((r) => [r.category, String(r.total_amount), String(r.item_count), String(r.invoice_count)]),
      ['', String(d.grand_total), '', ''],
    ];
  } else if (templateId === 'openItems') {
    const d = data as OpenItemsResponse;
    rows = [
      ['Br. fakture', 'Dobavljac', 'Datum', 'Valuta', 'Iznos', 'Preostalo', 'Status', 'Dana kasnjenja'],
      ...d.items.map((r) => [
        r.invoice_number ?? '',
        r.seller_name ?? '',
        r.invoice_date ?? '',
        r.due_date ?? '',
        String(r.total_amount ?? ''),
        String(r.remaining_amount),
        r.payment_status === 'partially_paid' ? 'Delimicno' : 'Neplaceno',
        String(r.days_overdue),
      ]),
      ['', '', '', '', '', String(d.total_open_amount), '', ''],
    ];
  } else if (templateId === 'aging') {
    const d = data as AgingResponse;
    rows = [
      ['Period', 'Broj faktura', 'Iznos'],
      ...d.buckets.map((b) => [b.bucket, String(b.count), String(b.total_amount)]),
      ['Ukupno', '', String(d.grand_total)],
    ];
  }

  const csv = rows
    .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(';'))
    .join('\r\n');

  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `izvestaj_${templateId}_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ── Empty state ──────────────────────────────────────────────────────

const EMPTY_HINTS: Record<string, { title: string; hint: string }> = {
  receivedGoods: {
    title: 'Nema primljene robe',
    hint: 'Otpremite fakture dobavljača i verifikujte ih. Stavke sa faktura će se automatski pojaviti ovde.',
  },
  spendingBySupplier: {
    title: 'Nema podataka o potrošnji',
    hint: 'Verifikujte fakture da bi se potrošnja po dobavljačima prikazala. Proverite datum i filter.',
  },
  monthlyBreakdown: {
    title: 'Nema stavki za izabrani period',
    hint: 'Proverite datumski opseg. Stavke se popunjavaju kada verifikujete fakture.',
  },
  priceComparison: {
    title: 'Nema artikala za poređenje',
    hint: 'Poređenje cena prikazuje samo artikle koji se pojavljuju kod 2+ dobavljača. Spojite slične artikle u Katalogu proizvoda (tab Upravljanje).',
  },
  expenseSummary: {
    title: 'Nema troškova za izabrani period',
    hint: 'Proverite datumski opseg. Troškovi se prikazuju nakon verifikacije faktura.',
  },
  kalkulacija: {
    title: 'Nema stavki za kalkulaciju',
    hint: 'Otpremite i verifikujte fakture dobavljača. Za prilagođene marže, podesite prodajne cene u Katalogu proizvoda.',
  },
  ruc: {
    title: 'Nema podataka o maržama',
    hint: 'RUC izveštaj zahteva prodajne cene u Katalogu proizvoda. Idite na tab Upravljanje → dodajte prodajne cene za artikle.',
  },
  categorySpending: {
    title: 'Nema kategorisanih stavki',
    hint: 'Dodelite kategorije artiklima u Katalogu proizvoda (tab Upravljanje). Nekategorisani artikli se prikazuju kao "Nekategorisano".',
  },
  openItems: {
    title: 'Nema otvorenih stavki',
    hint: 'Sve fakture su plaćene ili nema verifikovanih faktura. Evidentiranje uplata možete uraditi na stranici faktura.',
  },
  aging: {
    title: 'Nema dospelih potraživanja',
    hint: 'Sve fakture su plaćene. Ovaj izveštaj prikazuje neplaćene fakture grupisane po danima kašnjenja.',
  },
};

function EmptyState({ t, templateId }: { t: ReturnType<typeof useTranslations<'reports'>>; templateId?: string }) {
  const hint = templateId ? EMPTY_HINTS[templateId] : null;
  return (
    <div className="flex flex-col items-center justify-center py-16 bg-white border border-gray-200 rounded-xl">
      <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-3">
        <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>
      <p className="text-sm font-medium text-gray-700">{hint?.title ?? t('noData')}</p>
      <p className="text-xs text-gray-400 mt-1 max-w-sm text-center">{hint?.hint ?? t('noDataDesc')}</p>
    </div>
  );
}

// ── Skeleton col counts ──────────────────────────────────────────────

const SKELETON_COLS: Record<TemplateId, number> = {
  receivedGoods: 6,
  spendingBySupplier: 5,
  monthlyBreakdown: 9,
  priceComparison: 6,
  expenseSummary: 3,
  kalkulacija: 8,
  ruc: 7,
  categorySpending: 4,
  openItems: 8,
  aging: 3,
};

// ── Props ────────────────────────────────────────────────────────────

interface ReportContentProps {
  selectedTemplate: string;
}

/**
 * Renders the filter bar and results table for the given report template ID.
 *
 * Args:
 *   selectedTemplate: One of the 8 report template IDs.
 *
 * Returns:
 *   A React element with date pickers, PIB filter, description search,
 *   generate/export buttons, and the results table.
 */
export default function ReportContent({ selectedTemplate }: ReportContentProps) {
  const t = useTranslations('reports');
  const templateId = selectedTemplate as TemplateId;
  const { selectedClientId } = useClient();

  const now = new Date();
  const [dateFrom, setDateFrom] = useState(`${now.getFullYear()}-01-01`);
  const [dateTo, setDateTo] = useState(now.toISOString().slice(0, 10));
  const [sellerPib, setSellerPib] = useState('');
  const [description, setDescription] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState<ReportData>(null);

  // Clear results when switching tabs (sync via ref to avoid stale renders)
  const prevTemplateRef = useRef(templateId);
  if (prevTemplateRef.current !== templateId) {
    prevTemplateRef.current = templateId;
    if (data !== null) setData(null);
    if (error) setError('');
  }

  const handleGenerate = useCallback(async () => {
    setLoading(true);
    setError('');
    setData(null);

    const params: ReportParams = {
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      seller_pib: sellerPib.trim() || undefined,
      description: description.trim() || undefined,
      client_id: selectedClientId || undefined,
    };

    try {
      let result: ReportData = null;
      if (templateId === 'receivedGoods') result = await fetchReceivedGoods(params);
      else if (templateId === 'spendingBySupplier') result = await fetchSpendingBySupplier(params);
      else if (templateId === 'monthlyBreakdown') result = await fetchMonthlyBreakdown(params);
      else if (templateId === 'priceComparison') result = await fetchPriceComparison(params);
      else if (templateId === 'expenseSummary') result = await fetchExpenseSummary(params);
      else if (templateId === 'kalkulacija') result = await fetchKalkulacija(params);
      else if (templateId === 'ruc') result = await fetchRuc(params);
      else if (templateId === 'categorySpending') result = await fetchCategorySpending(params);
      else if (templateId === 'openItems') result = await fetchOpenItems(params);
      else if (templateId === 'aging') result = await fetchAging(params);
      setData(result);
    } catch {
      setError(t('noData'));
    } finally {
      setLoading(false);
    }
  }, [templateId, dateFrom, dateTo, sellerPib, description, t]);

  function hasItems(): boolean {
    if (!data) return false;
    if ('items' in data) return (data as { items: unknown[] }).items.length > 0;
    if ('buckets' in data) return (data as { buckets: unknown[] }).buckets.length > 0;
    return false;
  }

  return (
    <div>
      {/* Filters bar */}
      <div className="mb-4 bg-white border border-gray-200 rounded-xl p-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[140px]">
            <label className="block text-[11px] font-medium text-gray-500 mb-1">{t('dateFrom')}</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-300 focus:border-violet-400"
            />
          </div>

          <div className="flex-1 min-w-[140px]">
            <label className="block text-[11px] font-medium text-gray-500 mb-1">{t('dateTo')}</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-300 focus:border-violet-400"
            />
          </div>

          <div className="flex-1 min-w-[140px]">
            <label className="block text-[11px] font-medium text-gray-500 mb-1">{t('supplierPib')}</label>
            <input
              type="text"
              value={sellerPib}
              onChange={(e) => setSellerPib(e.target.value)}
              placeholder="123456789"
              maxLength={20}
              className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-300 focus:border-violet-400"
            />
          </div>

          <div className="flex-1 min-w-[180px]">
            <label className="block text-[11px] font-medium text-gray-500 mb-1">{t('description')}</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t('searchItems')}
              className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-300 focus:border-violet-400"
            />
          </div>

          <div className="flex items-center gap-2 shrink-0 self-end">
            <button
              type="button"
              onClick={handleGenerate}
              disabled={loading}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 disabled:bg-violet-300 rounded-lg shadow-sm transition-colors"
            >
              {loading && (
                <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              )}
              {t('generate')}
            </button>

            {hasItems() && (
              <button
                type="button"
                onClick={() => exportToCsv(templateId, data)}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium text-violet-700 bg-violet-50 hover:bg-violet-100 border border-violet-200 rounded-lg transition-colors"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                {t('exportCsv')}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-3 p-2.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError('')} className="text-red-400 hover:text-red-600 ml-3 shrink-0">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Results */}
      <div>
        {loading ? (
          <TableSkeleton cols={SKELETON_COLS[templateId] ?? 4} />
        ) : data === null && !error ? (
          <div className="flex flex-col items-center justify-center py-12 bg-white border border-dashed border-gray-200 rounded-xl">
            <div className="w-10 h-10 rounded-full bg-violet-50 flex items-center justify-center mb-2">
              <svg className="w-5 h-5 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <p className="text-sm text-gray-500">{t('noDataDesc')}</p>
          </div>
        ) : !hasItems() ? (
          <EmptyState t={t} templateId={templateId} />
        ) : (
          <>
            {templateId === 'receivedGoods' && (
              <ReceivedGoodsTable data={data as ReceivedGoodsResponse} t={t} />
            )}
            {templateId === 'spendingBySupplier' && (
              <SpendingBySupplierTable data={data as SpendingBySupplierResponse} t={t} />
            )}
            {templateId === 'monthlyBreakdown' && (
              <MonthlyBreakdownTable data={data as MonthlyBreakdownResponse} t={t} />
            )}
            {templateId === 'priceComparison' && (
              <PriceComparisonTable data={data as PriceComparisonResponse} t={t} />
            )}
            {templateId === 'expenseSummary' && (
              <ExpenseSummaryTable data={data as ExpenseSummaryResponse} t={t} />
            )}
            {templateId === 'kalkulacija' && (
              <KalkulacijaTable data={data as KalkulacijaResponse} t={t} />
            )}
            {templateId === 'ruc' && (
              <RucTable data={data as RucResponse} t={t} />
            )}
            {templateId === 'categorySpending' && (
              <CategorySpendingTable data={data as CategorySpendingResponse} t={t} />
            )}
            {templateId === 'openItems' && (
              <OpenItemsTable data={data as OpenItemsResponse} t={t} />
            )}
            {templateId === 'aging' && (
              <AgingTable data={data as AgingResponse} t={t} />
            )}
          </>
        )}
      </div>
    </div>
  );
}
