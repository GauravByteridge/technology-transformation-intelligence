import { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { LoadingState, ErrorState, EmptyState } from '@/components/common';
import { ChartDetailPanel, type ChartDetailData } from './ChartDetailPanel';

export interface BurnDownDataPoint {
  date: string;
  planned: number;
  actual: number;
}

export interface BurnDownChartProps {
  /** Derived progress data — planned vs actual over time */
  data: BurnDownDataPoint[] | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}

/**
 * BurnDownChart — renders a line chart showing planned vs actual progress
 * over time. Accepts pre-derived data props. Since the portfolio summary
 * provides only per-project progress percentages (not time-series),
 * this chart may show empty state when burn-down data isn't available
 * at portfolio level.
 */
export function BurnDownChart({ data, isLoading, isError, onRetry }: BurnDownChartProps) {
  const [detail, setDetail] = useState<ChartDetailData | null>(null);

  if (isLoading) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Project Burn Down</h3>
        <LoadingState variant="skeleton" message="Loading progress data" />
      </div>
    );
  }

  if (isError) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Project Burn Down</h3>
        <ErrorState message="Failed to load progress data" onRetry={onRetry} />
      </div>
    );
  }

  if (!data || data.length < 2) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Project Burn Down</h3>
        <EmptyState message="No burn-down data available" />
      </div>
    );
  }

  const handleClick = (point: Record<string, unknown>, dataKey: string) => {
    setDetail({
      label: point.date as string,
      value: `${point[dataKey]}%`,
      category: dataKey === 'planned' ? 'Planned Progress' : 'Actual Progress',
    });
  };

  return (
    <div className="relative">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Project Burn Down</h3>
      <ChartDetailPanel data={detail} onClose={() => setDetail(null)} />
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            label={{ value: 'Date', position: 'insideBottom', offset: -5 }}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            domain={[0, 100]}
            label={{ value: 'Progress (%)', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            formatter={(value, name) => [
              `${value}%`,
              name === 'planned' ? 'Planned Progress' : 'Actual Progress',
            ]}
          />
          <Legend
            formatter={(value) =>
              value === 'planned' ? 'Planned Progress' : 'Actual Progress'
            }
          />
          <Line
            type="monotone"
            dataKey="planned"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ r: 4, cursor: 'pointer' }}
            activeDot={{
              r: 6,
              onClick: (_, event: unknown) => {
                const e = event as { payload?: Record<string, unknown> };
                if (e.payload) handleClick(e.payload, 'planned');
              },
            }}
          />
          <Line
            type="monotone"
            dataKey="actual"
            stroke="#ef4444"
            strokeWidth={2}
            dot={{ r: 4, cursor: 'pointer' }}
            activeDot={{
              r: 6,
              onClick: (_, event: unknown) => {
                const e = event as { payload?: Record<string, unknown> };
                if (e.payload) handleClick(e.payload, 'actual');
              },
            }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
