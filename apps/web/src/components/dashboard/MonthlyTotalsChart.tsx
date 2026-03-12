'use client';

import { useTranslations } from 'next-intl';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { MonthlyTotal } from '@/lib/api/dashboard';

interface Props {
  data: MonthlyTotal[];
}

function formatRsd(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
  return String(Math.round(value));
}

function formatTooltipRsd(value: number): string {
  return new Intl.NumberFormat('sr-Latn-RS', {
    style: 'decimal',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value) + ' RSD';
}

export default function MonthlyTotalsChart({ data }: Props) {
  const t = useTranslations('dashboard');

  const chartData = data.map((d) => {
    const [, mm] = d.month.split('-');
    return {
      month: t(`monthShort.${parseInt(mm, 10)}`),
      total: d.total_rsd,
    };
  });

  const hasData = data.some((d) => d.total_rsd > 0);

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">{t('monthlyTotals')}</h3>
      {hasData ? (
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="totalGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#7c3aed" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 12, fill: '#6b7280' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 12, fill: '#6b7280' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={formatRsd}
            />
            <Tooltip
              contentStyle={{
                borderRadius: '0.75rem',
                border: '1px solid #e5e7eb',
                boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                fontSize: '0.875rem',
              }}
              formatter={(value) => [formatTooltipRsd(Number(value)), t('totalAmount')]}
              cursor={{ stroke: '#7c3aed', strokeWidth: 1, strokeDasharray: '4 4' }}
            />
            <Area
              type="monotone"
              dataKey="total"
              stroke="#7c3aed"
              strokeWidth={2}
              fill="url(#totalGradient)"
              dot={{ r: 3, fill: '#7c3aed', strokeWidth: 0 }}
              activeDot={{ r: 5, fill: '#7c3aed', strokeWidth: 2, stroke: '#fff' }}
            />
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <div className="flex items-center justify-center h-[260px] text-sm text-gray-400">
          {t('noChartData')}
        </div>
      )}
    </div>
  );
}
