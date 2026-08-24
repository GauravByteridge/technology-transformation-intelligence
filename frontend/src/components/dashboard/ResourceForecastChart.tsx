import { useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { LoadingState, ErrorState, EmptyState } from '@/components/common';
import { ChartDetailPanel, type ChartDetailData } from './ChartDetailPanel';

export interface ResourceUtilizationItem {
  project_id: string;
  utilization: number;
}

export interface ResourceForecastChartProps {
  /** Derived resource utilization data from portfolio summary projects */
  data: ResourceUtilizationItem[] | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}

/**
 * ResourceForecastChart — renders per-project resource utilization as an area chart.
 * Accepts pre-derived data props from the portfolio summary.
 */
export function ResourceForecastChart({ data, isLoading, isError, onRetry }: ResourceForecastChartProps) {
  const [detail, setDetail] = useState<ChartDetailData | null>(null);

  if (isLoading) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Resource Utilization</h3>
        <LoadingState variant="skeleton" message="Loading resource data" />
      </div>
    );
  }

  if (isError) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Resource Utilization</h3>
        <ErrorState message="Failed to load resource data" onRetry={onRetry} />
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Resource Utilization</h3>
        <EmptyState message="No resource data available" />
      </div>
    );
  }

  const chartData = data.map((item) => ({
    project: item.project_id,
    utilization: item.utilization,
  }));

  const handleClick = (point: Record<string, unknown>) => {
    setDetail({
      label: point.project as string,
      value: `${point.utilization}%`,
      category: 'Resource Utilization',
    });
  };

  return (
    <div className="relative">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Resource Utilization</h3>
      <ChartDetailPanel data={detail} onClose={() => setDetail(null)} />
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="project"
            tick={{ fontSize: 11 }}
            label={{ value: 'Project', position: 'insideBottom', offset: -5 }}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            domain={[0, 100]}
            label={{ value: 'Utilization (%)', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            formatter={(value) => [`${value}%`, 'Utilization']}
          />
          <Legend formatter={() => 'Utilization'} />
          <Area
            type="monotone"
            dataKey="utilization"
            stroke="#6366f1"
            fill="#c7d2fe"
            strokeWidth={2}
            activeDot={{
              r: 6,
              cursor: 'pointer',
              onClick: (_, event: unknown) => {
                const e = event as { payload?: Record<string, unknown> };
                if (e.payload) handleClick(e.payload);
              },
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
