import { useState } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useProjectHealthDistribution } from '../../hooks/useDashboard';
import { ChartErrorBoundary } from './ChartErrorBoundary';
import { ChartDetailPanel, type ChartDetailData } from './ChartDetailPanel';

const COLORS: Record<string, string> = {
  'On Track': '#22c55e',
  'At Risk': '#f59e0b',
  'Delayed': '#ef4444',
  'Completed': '#3b82f6',
};

function ProjectHealthChartInner() {
  const { data, isLoading, isError } = useProjectHealthDistribution();
  const [detail, setDetail] = useState<ChartDetailData | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse bg-gray-200 rounded-full w-48 h-48" />
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
              <Cell
                key={entry.name}
                fill={COLORS[entry.name]}
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value, name) => [value, name]}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ProjectHealthChart() {
  return (
    <ChartErrorBoundary>
      <ProjectHealthChartInner />
    </ChartErrorBoundary>
  );
}
