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

export interface BudgetVsActualItem {
  name: string;
  budget: number;
  actual: number;
}

export interface BudgetVsActualChartProps {
  /** Derived budget vs actual data from portfolio summary projects */
  data: BudgetVsActualItem[] | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}

/**
 * BudgetVsActualChart — renders a grouped bar chart comparing planned budget
 * to actual cost per project. Accepts pre-derived data props.
 */
export function BudgetVsActualChart({ data, isLoading, isError, onRetry }: BudgetVsActualChartProps) {
  const [detail, setDetail] = useState<ChartDetailData | null>(null);

  if (isLoading) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Budget vs Actual</h3>
        <LoadingState variant="skeleton" message="Loading budget data" />
      </div>
    );
  }

  if (isError) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Budget vs Actual</h3>
        <ErrorState message="Failed to load budget data" onRetry={onRetry} />
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Budget vs Actual</h3>
        <EmptyState message="No budget data available" />
      </div>
    );
  }

  const chartData = data.map((item) => ({
    name: item.name,
    planned: item.budget,
    actual: item.actual,
  }));

  const handleBarClick = (entry: Record<string, unknown>, dataKey: string) => {
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
      <h3 className="text-sm font-semibold text-gray-700 mb-2">Budget vs Actual</h3>
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
            onClick={(data) => handleBarClick(data as unknown as Record<string, unknown>, 'planned')}
            style={{ cursor: 'pointer' }}
          />
          <Bar
            dataKey="actual"
            fill="#f59e0b"
            onClick={(data) => handleBarClick(data as unknown as Record<string, unknown>, 'actual')}
            style={{ cursor: 'pointer' }}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
