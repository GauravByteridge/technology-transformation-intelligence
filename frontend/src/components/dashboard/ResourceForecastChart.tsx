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
import { useResourceForecastChart } from '../../hooks/useDashboard';
import { ChartErrorBoundary } from './ChartErrorBoundary';
import { ChartDetailPanel, type ChartDetailData } from './ChartDetailPanel';

function ResourceForecastChartInner() {
  const { data, isLoading, isError } = useResourceForecastChart();
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
    month: point.month,
    demand: point.demand,
    capacity: point.capacity,
  }));

  const handleClick = (point: Record<string, unknown>, dataKey: string) => {
    setDetail({
      label: point.month as string,
      value: point[dataKey] as number,
      category: dataKey === 'demand' ? 'Resource Demand' : 'Available Capacity',
    });
  };

  return (
    <div className="relative">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">
        Resource Forecast
      </h3>
      <ChartDetailPanel data={detail} onClose={() => setDetail(null)} />
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 12 }}
            label={{ value: 'Month', position: 'insideBottom', offset: -5 }}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            label={{ value: 'Headcount', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            formatter={(value, name) => [
              value,
              name === 'demand' ? 'Demand' : 'Capacity',
            ]}
          />
          <Legend
            formatter={(value) =>
              value === 'demand' ? 'Demand' : 'Capacity'
            }
          />
          <Area
            type="monotone"
            dataKey="demand"
            stroke="#ef4444"
            fill="#fecaca"
            strokeWidth={2}
            activeDot={{
              r: 6,
              cursor: 'pointer',
              onClick: (_, event: unknown) => {
                const e = event as { payload?: Record<string, unknown> };
                if (e.payload) handleClick(e.payload, 'demand');
              },
            }}
          />
          <Area
            type="monotone"
            dataKey="capacity"
            stroke="#22c55e"
            fill="#bbf7d0"
            strokeWidth={2}
            activeDot={{
              r: 6,
              cursor: 'pointer',
              onClick: (_, event: unknown) => {
                const e = event as { payload?: Record<string, unknown> };
                if (e.payload) handleClick(e.payload, 'capacity');
              },
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ResourceForecastChart() {
  return (
    <ChartErrorBoundary>
      <ResourceForecastChartInner />
    </ChartErrorBoundary>
  );
}
