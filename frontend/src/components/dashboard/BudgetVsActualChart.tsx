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
import { useBudgetChart } from '../../hooks/useDashboard';
import { ChartErrorBoundary } from './ChartErrorBoundary';
import { ChartDetailPanel, type ChartDetailData } from './ChartDetailPanel';

function BudgetVsActualChartInner() {
  const { data, isLoading, isError } = useBudgetChart();
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

  const chartData = data.map((item) => ({
    name: item.project_name,
    planned: item.planned_budget,
    actual: item.actual_cost,
    projectId: item.project_id,
  }));

  const handleBarClick = (data: unknown, dataKey: string) => {
    const entry = data as Record<string, unknown>;
    const label = entry.name as string;
    const value = entry[dataKey] as number;
    setDetail({
      label,
      value: `$${value.toLocaleString()}`,
      category: dataKey === 'planned' ? 'Planned Budget' : 'Actual Cost',
    });
  };

  return (
    <div className="relative">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">
        Budget vs Actual
      </h3>
      <ChartDetailPanel data={detail} onClose={() => setDetail(null)} />
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 12 }}
            label={{ value: 'Project', position: 'insideBottom', offset: -5 }}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            label={{ value: 'Amount ($)', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            formatter={(value, name) => [
              `$${Number(value).toLocaleString()}`,
              name === 'planned' ? 'Planned Budget' : 'Actual Cost',
            ]}
          />
          <Legend
            formatter={(value) =>
              value === 'planned' ? 'Planned Budget' : 'Actual Cost'
            }
          />
          <Bar
            dataKey="planned"
            fill="#3b82f6"
            onClick={(data) => handleBarClick(data, 'planned')}
            style={{ cursor: 'pointer' }}
          />
          <Bar
            dataKey="actual"
            fill="#f59e0b"
            onClick={(data) => handleBarClick(data, 'actual')}
            style={{ cursor: 'pointer' }}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function BudgetVsActualChart() {
  return (
    <ChartErrorBoundary>
      <BudgetVsActualChartInner />
    </ChartErrorBoundary>
  );
}
