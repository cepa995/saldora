'use client';

import { useTranslations } from 'next-intl';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import type { StatusCount } from '@/lib/api/dashboard';

interface Props {
  data: StatusCount[];
}

const ALL_STATUSES = ['processing', 'review', 'verified', 'exported', 'error'] as const;

const STATUS_COLORS: Record<string, string> = {
  processing: '#f59e0b',
  review: '#3b82f6',
  verified: '#10b981',
  exported: '#8b5cf6',
  error: '#ef4444',
};

const STATUS_LABELS: Record<string, string> = {
  processing: 'processing',
  review: 'inReview',
  verified: 'verified',
  exported: 'exported',
  error: 'error',
};

export default function StatusDonutChart({ data }: Props) {
  const t = useTranslations('dashboard');

  const countMap = Object.fromEntries(data.map((d) => [d.status, d.count]));
  const total = data.reduce((sum, d) => sum + d.count, 0);
  const hasData = total > 0;

  // Pie slices — only statuses with data
  const pieData = ALL_STATUSES.filter((s) => (countMap[s] ?? 0) > 0).map((s) => ({
    name: t(STATUS_LABELS[s]),
    value: countMap[s],
    color: STATUS_COLORS[s],
  }));

  // Legend — all statuses, always visible
  const legendData = ALL_STATUSES.map((s) => {
    const count = countMap[s] ?? 0;
    return {
      status: s,
      name: t(STATUS_LABELS[s]),
      count,
      pct: total > 0 ? Math.round((count / total) * 100) : 0,
      color: STATUS_COLORS[s],
    };
  });

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 h-full flex flex-col">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">{t('statusDistribution')}</h3>
      {hasData ? (
        <div className="flex flex-col items-center flex-1">
          <div className="relative w-full" style={{ height: 240 }}>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={95}
                  paddingAngle={2}
                  dataKey="value"
                  stroke="none"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    borderRadius: '0.75rem',
                    border: '1px solid #e5e7eb',
                    boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                    fontSize: '0.875rem',
                  }}
                  formatter={(value) => [value, t('invoiceCount')]}
                />
              </PieChart>
            </ResponsiveContainer>
            {/* Center label */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-2xl font-bold text-gray-900 tabular-nums">{total}</span>
              <span className="text-xs text-gray-500">{t('total')}</span>
            </div>
          </div>
          <div className="w-full space-y-1.5 mt-2">
            {legendData.map((entry) => (
              <div key={entry.status} className="flex items-center gap-2 text-xs">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-gray-600 flex-1">{entry.name}</span>
                <span className="font-medium text-gray-900 tabular-nums">{entry.pct}%</span>
                <span className="text-gray-400 tabular-nums w-8 text-right">({entry.count})</span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-center h-[260px] text-sm text-gray-400">
          {t('noChartData')}
        </div>
      )}
    </div>
  );
}
