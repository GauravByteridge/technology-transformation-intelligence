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
import { useBurndownChart } from '../../hooks/useDashboard';
import { ChartErrorBoundary } from './ChartErrorBoundary';
import { ChartDetailPanel, type ChartDetailData } from './ChartDetailPanel';

function BurnDownChartInner() {
  const { data, isLoading, isError } = useBurndownChart();
  const [detail, setDetail] = useState<ChartDetailData | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse bg-gray-200 rounded w-full h-48" />
      </div>
    );
  }

  if (isError || !data || data.length < 2) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 border border-gray-200 rounded-lg">
        <p className="text-gray-500 text-sm">Chart unavailable</p>
      </div>
    );
  }

  const chartData = data.map((point) => ({
    date: point.date,
    planned: point.planned_progress,
    actual: point.actual_progress,
  }));

  const handleClick = (point: Record<string, unknown>, dataKey: string) => {
    setDetail({
      label: point.date as string,
      value: `${point[dataKey]}%`,
      category: dataKey === 'planned' ? 'Planned Progress' : 'Actual Progress',
    });
  };

  return (
    <div className="relative">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">
        Project Burn Down
      </h3>
      <ChartDetailPanel data={detail} onClose={() => setDetail(null)} />
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            label={{ value: 'Date', position: 'insideBottom', offset: -5 }}
          />
          <YAxis
            tick={{ fontSize: 12 }}
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

export function BurnDownChart() {
  return (
    <ChartErrorBoundary>
      <BurnDownChartInner />
    </ChartErrorBoundary>
  );
}
