import { useState } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { LoadingState, ErrorState, EmptyState } from '@/components/common';
import { ChartDetailPanel, type ChartDetailData } from './ChartDetailPanel';

const COLORS: Record<string, string> = {
  'On Track': '#22c55e',
  'At Risk': '#f59e0b',
  'Delayed': '#ef4444',
  'Completed': '#3b82f6',
};

export interface HealthDistributionData {
  on_track: number;
  at_risk: number;
  delayed: number;
  completed: number;
}

export interface ProjectHealthChartProps {
  /** Derived health distribution counts from portfolio summary */
  data: HealthDistributionData | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}

/**
 * ProjectHealthChart — renders a donut chart showing the distribution of
 * project health statuses. Accepts pre-derived data props rather than
 * fetching its own data.
 */
export function ProjectHealthChart({ data, isLoading, isError, onRetry }: ProjectHealthChartProps) {
  const [detail, setDetail] = useState<ChartDetailData | null>(null);

  if (isLoading) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          Project Health Distribution
        </h3>
        <LoadingState variant="skeleton" message="Loading health distribution" />
      </div>
    );
  }

  if (isError) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          Project Health Distribution
        </h3>
        <ErrorState message="Failed to load health distribution" onRetry={onRetry} />
      </div>
    );
  }

  if (!data || (data.on_track === 0 && data.at_risk === 0 && data.delayed === 0 && data.completed === 0)) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          Project Health Distribution
        </h3>
        <EmptyState message="No project health data available" />
      </div>
    );
  }

  const chartData = [
    { name: 'On Track', value: data.on_track },
    { name: 'At Risk', value: data.at_risk },
    { name: 'Delayed', value: data.delayed },
    { name: 'Completed', value: data.completed },
  ];

  const handleClick = (entry: { name: string; value: number }) => {
    setDetail({
      label: entry.name,
      value: entry.value,
      category: 'Project Health Distribution',
    });
  };

  return (
    <div className="relative">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">
        Project Health Distribution
      </h3>
      <ChartDetailPanel data={detail} onClose={() => setDetail(null)} />
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={100}
            dataKey="value"
            nameKey="name"
            onClick={(_, index) => handleClick(chartData[index])}
            style={{ cursor: 'pointer' }}
          >
            {chartData.map((entry) => (
              <Cell key={entry.name} fill={COLORS[entry.name]} />
            ))}
          </Pie>
          <Tooltip formatter={(value, name) => [value, name]} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
