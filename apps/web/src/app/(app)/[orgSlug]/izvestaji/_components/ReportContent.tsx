'use client';

import { useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import {
  fetchReceivedGoods,
  fetchSpendingBySupplier,
  fetchMonthlyBreakdown,
  fetchPriceComparison,
  fetchExpenseSummary,
  fetchKalkulacija,
  fetchRuc,
  fetchCategorySpending,
  type ReportParams,
  type ReceivedGoodsResponse,
  type SpendingBySupplierResponse,
  type MonthlyBreakdownResponse,
  type PriceComparisonResponse,
  type ExpenseSummaryResponse,
  type KalkulacijaResponse,
  type RucResponse,
  type CategorySpendingResponse,
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
  | 'categorySpending';

type ReportData =
  | ReceivedGoodsResponse
  | SpendingBySupplierResponse
  | MonthlyBreakdownResponse
  | PriceComparisonResponse
  | ExpenseSummaryResponse
  | KalkulacijaResponse
  | RucResponse
  | CategorySpendingResponse
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
          <TableHead cols={[t('sellerName'), t('sellerPib'), t('invoiceCount'), t('total')]} />
          <tbody>
            {data.items.map((row, i) => (
              <tr key={i} className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50 transition-colors">
                <td className="px-3 py-2.5 text-gray-900 font-medium">{row.seller_name || '—'}</td>
                <td className="px-3 py-2.5 text-gray-500 font-mono text-xs">{row.seller_pib || '—'}</td>
                <td className="px-3 py-2.5 text-center text-gray-700">{row.invoice_count}</td>
                <td className="px-3 py-2.5 text-gray-900 font-semibold tabular-nums">{fmtAmount(row.total_amount)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-gray-200 bg-gray-50/80">
              <td className="px-3 py-2 text-xs font-semibold text-gray-700 uppercase" colSpan={3}>{t('grandTotal')}</td>
              <td className="px-3 py-2 text-sm font-bold text-violet-700 tabular-nums">{fmtAmount(data.grand_total)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

function MonthlyBreakdownTable({ data, t }: { data: MonthlyBreakdownResponse; t: ReturnType<typeof useTranslations<'reports'>> }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <TableHead cols={[t('period'), t('sellerName'), t('description'), t('quantity'), t('unitPrice'), 'PDV %', 'PDV iznos', t('total')]} />
          <tbody>
            {data.items.map((row, i) => (
              <tr key={i} className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50 transition-colors">
                <td className="px-3 py-2.5 text-gray-500 text-xs whitespace-nowrap">{row.invoice_date || '—'}</td>
                <td className="px-3 py-2.5 text-gray-700 max-w-[150px] truncate">{row.seller_name || '—'}</td>
                <td className="px-3 py-2.5 text-gray-900 max-w-[200px] truncate font-medium">{row.description}</td>
                <td className="px-3 py-2.5 text-gray-700 tabular-nums">{fmtNum(row.quantity)}</td>
                <td className="px-3 py-2.5 text-gray-700 tabular-nums">{fmtNum(row.unit_price)}</td>
                <td className="px-3 py-2.5 text-gray-500 tabular-nums">{row.tax_rate != null ? `${row.tax_rate}%` : '—'}</td>
                <td className="px-3 py-2.5 text-gray-500 tabular-nums">{row.tax_amount != null ? fmtAmount(row.tax_amount) : '—'}</td>
                <td className="px-3 py-2.5 text-gray-900 font-semibold tabular-nums">{fmtAmount(row.total)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-gray-200 bg-gray-50/80">
              <td className="px-3 py-2 text-xs font-semibold text-gray-700 uppercase" colSpan={7}>{t('grandTotal')}</td>
              <td className="px-3 py-2 text-sm font-bold text-violet-700 tabular-nums">{fmtAmount(data.total_amount)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

function PriceComparisonTable({ data, t }: { data: PriceComparisonResponse; t: ReturnType<typeof useTranslations<'reports'>> }) {
  return (
    <div className="space-y-3">
      {data.items.map((item, i) => (
        <div key={i} className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 bg-gray-50/60 flex items-center justify-between gap-3">
            <span className="text-sm font-semibold text-gray-900 truncate">{item.description}</span>
            <div className="flex items-center gap-3 shrink-0 text-xs text-gray-500">
              <span>min <span className="font-medium text-gray-700">{fmtNum(item.global_min)}</span></span>
              <span>avg <span className="font-medium text-gray-700">{fmtNum(item.global_avg)}</span></span>
              <span>max <span className="font-medium text-gray-700">{fmtNum(item.global_max)}</span></span>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <TableHead cols={[t('sellerName'), t('sellerPib'), 'Min', 'Avg', 'Max', t('invoiceCount')]} />
              <tbody>
                {item.supplier_prices.map((sp, j) => (
                  <tr key={j} className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50 transition-colors">
                    <td className="px-3 py-2.5 text-gray-900 font-medium">{sp.seller_name || '—'}</td>
                    <td className="px-3 py-2.5 text-gray-500 font-mono text-xs">{sp.seller_pib || '—'}</td>
                    <td className="px-3 py-2.5 text-gray-700 tabular-nums">{fmtNum(sp.min_price)}</td>
                    <td className="px-3 py-2.5 text-gray-700 tabular-nums">{fmtNum(sp.avg_price)}</td>
                    <td className="px-3 py-2.5 text-gray-700 tabular-nums">{fmtNum(sp.max_price)}</td>
                    <td className="px-3 py-2.5 text-center text-gray-700">{sp.occurrence_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}

function ExpenseSummaryTable({ data, t }: { data: ExpenseSummaryResponse; t: ReturnType<typeof useTranslations<'reports'>> }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <TableHead cols={[t('period'), t('invoiceCount'), t('supplierCount'), t('total')]} />
          <tbody>
            {data.items.map((row, i) => (
              <tr key={i} className="border-b border-gray-100 last:border-0 hover:bg-gray-50/50 transition-colors">
                <td className="px-3 py-2.5 text-gray-900 font-medium">{row.period}</td>
                <td className="px-3 py-2.5 text-center text-gray-700">{row.invoice_count}</td>
                <td className="px-3 py-2.5 text-center text-gray-700">{row.seller_count}</td>
                <td className="px-3 py-2.5 text-gray-900 font-semibold tabular-nums">{fmtAmount(row.total_amount)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-gray-200 bg-gray-50/80">
              <td className="px-3 py-2 text-xs font-semibold text-gray-700 uppercase" colSpan={3}>{t('grandTotal')}</td>
              <td className="px-3 py-2 text-sm font-bold text-violet-700 tabular-nums">{fmtAmount(data.grand_total)}</td>
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
      ['Dobavljac', 'PIB', 'Br. faktura', 'Ukupno'],
      ...d.items.map((r) => [r.seller_name ?? '', r.seller_pib ?? '', String(r.invoice_count), String(r.total_amount)]),
      ['', '', '', String(d.grand_total)],
    ];
  } else if (templateId === 'monthlyBreakdown') {
    const d = data as MonthlyBreakdownResponse;
    rows = [
      ['Datum', 'Dobavljac', 'PIB', 'Opis', 'Kolicina', 'Jed. cena', 'PDV %', 'PDV iznos', 'Ukupno'],
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
      ]),
      ['', '', '', '', '', '', '', '', String(d.total_amount)],
    ];
  } else if (templateId === 'priceComparison') {
    const d = data as PriceComparisonResponse;
    rows = [['Opis', 'Dobavljac', 'PIB', 'Min', 'Avg', 'Max', 'Br.']];
    for (const item of d.items) {
      for (const sp of item.supplier_prices) {
        rows.push([
          item.description,
          sp.seller_name ?? '',
          sp.seller_pib ?? '',
          String(sp.min_price),
          String(sp.avg_price),
          String(sp.max_price),
          String(sp.occurrence_count),
        ]);
      }
    }
  } else if (templateId === 'expenseSummary') {
    const d = data as ExpenseSummaryResponse;
    rows = [
      ['Period', 'Br. faktura', 'Br. dobavljaca', 'Ukupno'],
      ...d.items.map((r) => [r.period, String(r.invoice_count), String(r.seller_count), String(r.total_amount)]),
      ['', '', '', String(d.grand_total)],
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

function EmptyState({ t }: { t: ReturnType<typeof useTranslations<'reports'>> }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 bg-white border border-gray-200 rounded-xl">
      <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-3">
        <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>
      <p className="text-sm font-medium text-gray-700">{t('noData')}</p>
      <p className="text-xs text-gray-400 mt-0.5">{t('noDataDesc')}</p>
    </div>
  );
}

// ── Skeleton col counts ──────────────────────────────────────────────

const SKELETON_COLS: Record<TemplateId, number> = {
  receivedGoods: 6,
  spendingBySupplier: 4,
  monthlyBreakdown: 8,
  priceComparison: 6,
  expenseSummary: 4,
  kalkulacija: 8,
  ruc: 7,
  categorySpending: 4,
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

  const now = new Date();
  const [dateFrom, setDateFrom] = useState(`${now.getFullYear()}-01-01`);
  const [dateTo, setDateTo] = useState(now.toISOString().slice(0, 10));
  const [sellerPib, setSellerPib] = useState('');
  const [description, setDescription] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState<ReportData>(null);

  const handleGenerate = useCallback(async () => {
    setLoading(true);
    setError('');
    setData(null);

    const params: ReportParams = {
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      seller_pib: sellerPib.trim() || undefined,
      description: description.trim() || undefined,
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
          <EmptyState t={t} />
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
          </>
        )}
      </div>
    </div>
  );
}
