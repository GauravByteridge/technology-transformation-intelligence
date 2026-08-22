import { useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useAuditChart } from '../../hooks/useDashboard';
import { ChartErrorBoundary } from './ChartErrorBoundary';
import { ChartDetailPanel, type ChartDetailData } from './ChartDetailPanel';

function AuditRemediationChartInner() {
  const { data, isLoading, isError } = useAuditChart();
  const [detail, setDetail] = useState<ChartDetailData | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse bg-gray-200 rounded w-full h-48" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 border border-gray-200 rounded-lg">
        <p className="text-gray-500 text-sm">Chart unavailable</p>
      </div>
    );
  }

  const chartData = [
    { name: 'Open Findings', value: data.open_findings, color: '#f59e0b' },
    { name: 'Critical Findings', value: data.critical_findings, color: '#ef4444' },
    { name: 'Remediated', value: data.remediated_items, color: '#22c55e' },
    { name: 'Overdue', value: data.overdue_items, color: '#8b5cf6' },
  ];

  const handleClick = (entry: { name: string; value: number }) => {
    setDetail({
      label: entry.name,
      value: entry.value,
      category: 'Audit & Remediation',
    });
  };

  return (
    <div className="relative">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">
        Audit & Remediation
      </h3>
      <ChartDetailPanel data={detail} onClose={() => setDetail(null)} />
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 11 }}
            label={{ value: 'Metric', position: 'insideBottom', offset: -5 }}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            label={{ value: 'Count', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            formatter={(value, name) => [value, name]}
          />
          <Legend />
          <Bar
            dataKey="value"
            name="Count"
            onClick={(data) => handleClick(data as { name: string; value: number })}
            style={{ cursor: 'pointer' }}
            fill="#3b82f6"
          >
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function AuditRemediationChart() {
  return (
    <ChartErrorBoundary>
      <AuditRemediationChartInner />
    </ChartErrorBoundary>
  );
}
