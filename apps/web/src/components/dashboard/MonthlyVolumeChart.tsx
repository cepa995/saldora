'use client';

import { useTranslations } from 'next-intl';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { MonthlyVolume } from '@/lib/api/dashboard';

interface Props {
  data: MonthlyVolume[];
}

export default function MonthlyVolumeChart({ data }: Props) {
  const t = useTranslations('dashboard');

  const chartData = data.map((d) => {
    const [, mm] = d.month.split('-');
    return {
      month: t(`monthShort.${parseInt(mm, 10)}`),
      count: d.count,
    };
  });

  const hasData = data.some((d) => d.count > 0);
  const periodTotal = data.reduce((sum, d) => sum + d.count, 0);
  const monthsWithData = data.filter((d) => d.count > 0).length;
  const avgPerMonth = monthsWithData > 0 ? Math.round(periodTotal / monthsWithData) : 0;

  // Find peak month
  const peakMonth = data.reduce(
    (max, d) => (d.count > max.count ? d : max),
    { month: '', count: 0 },
  );
  const peakLabel = peakMonth.month
    ? t(`monthShort.${parseInt(peakMonth.month.split('-')[1], 10)}`)
    : '—';

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 h-full flex flex-col">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">{t('monthlyVolume')}</h3>
      {hasData ? (
        <>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
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
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: '0.75rem',
                  border: '1px solid #e5e7eb',
                  boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                  fontSize: '0.875rem',
                }}
                formatter={(value) => [value, t('invoiceCount')]}
                cursor={{ fill: 'rgba(124, 58, 237, 0.05)' }}
              />
              <Bar
                dataKey="count"
                fill="#7c3aed"
                radius={[6, 6, 0, 0]}
                maxBarSize={40}
              />
            </BarChart>
          </ResponsiveContainer>
          <div className="grid grid-cols-3 gap-3 mt-auto pt-4 border-t border-gray-100">
            <div>
              <p className="text-lg font-bold text-gray-900 tabular-nums">{periodTotal}</p>
              <p className="text-xs text-gray-500">{t('periodTotal')}</p>
            </div>
            <div>
              <p className="text-lg font-bold text-gray-900 tabular-nums">{avgPerMonth}</p>
              <p className="text-xs text-gray-500">{t('avgPerMonth')}</p>
            </div>
            <div>
              <p className="text-lg font-bold text-gray-900 tabular-nums">
                {peakMonth.count}
                <span className="text-xs font-normal text-gray-400 ml-1">({peakLabel})</span>
              </p>
              <p className="text-xs text-gray-500">{t('peakMonth')}</p>
            </div>
          </div>
        </>
      ) : (
        <div className="flex items-center justify-center h-[260px] text-sm text-gray-400">
          {t('noChartData')}
        </div>
      )}
    </div>
  );
}
