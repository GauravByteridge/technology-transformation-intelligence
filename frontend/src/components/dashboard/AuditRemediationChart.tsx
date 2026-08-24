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
import { LoadingState, ErrorState, EmptyState } from '@/components/common';
import { ChartDetailPanel, type ChartDetailData } from './ChartDetailPanel';

export interface AuditRemediationData {
  openAuditFindings: number;
  openRemediationItems: number;
}

export interface AuditRemediationChartProps {
  /** Derived audit/remediation aggregated counts from portfolio summary */
  data: AuditRemediationData | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}

/**
 * AuditRemediationChart — renders a bar chart showing open audit findings
 * and open remediation items. Accepts pre-derived data props.
 */
export function AuditRemediationChart({ data, isLoading, isError, onRetry }: AuditRemediationChartProps) {
  const [detail, setDetail] = useState<ChartDetailData | null>(null);

  if (isLoading) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Audit & Remediation</h3>
        <LoadingState variant="skeleton" message="Loading audit data" />
      </div>
    );
  }

  if (isError) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Audit & Remediation</h3>
        <ErrorState message="Failed to load audit data" onRetry={onRetry} />
      </div>
    );
  }

  if (!data || (data.openAuditFindings === 0 && data.openRemediationItems === 0)) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Audit & Remediation</h3>
        <EmptyState message="No audit data available" />
      </div>
    );
  }

  const chartData = [
    { name: 'Open Audit Findings', value: data.openAuditFindings },
    { name: 'Open Remediation Items', value: data.openRemediationItems },
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
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Audit & Remediation</h3>
      <ChartDetailPanel data={detail} onClose={() => setDetail(null)} />
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 11 }}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            label={{ value: 'Count', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip formatter={(value, name) => [value, name]} />
          <Legend />
          <Bar
            dataKey="value"
            name="Count"
            onClick={(data) => handleClick(data as { name: string; value: number })}
            style={{ cursor: 'pointer' }}
            fill="#3b82f6"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
