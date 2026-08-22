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
import { useProjectFinancials } from '../../hooks';
import { LoadingState } from '../common/LoadingState';
import { EmptyState } from '../common/EmptyState';

interface FinancialsSectionProps {
  projectId: string;
}

export function FinancialsSection({ projectId }: FinancialsSectionProps) {
  const { data: financials, isLoading } = useProjectFinancials(projectId);

  if (isLoading) {
    return <LoadingState message="Loading financials..." />;
  }

  if (!financials || financials.length === 0) {
    return <EmptyState dataType="financial data" message="No budget or cost data available for this project." />;
  }

  // Group by category for breakdown table
  const categoryMap = new Map<string, { planned: number; actual: number; variance: number }>();
  for (const item of financials) {
    const existing = categoryMap.get(item.category) ?? { planned: 0, actual: 0, variance: 0 };
    existing.planned += item.planned_amount;
    existing.actual += item.actual_amount;
    existing.variance += item.variance;
    categoryMap.set(item.category, existing);
  }
  const categories = Array.from(categoryMap.entries()).map(([category, data]) => ({
    category,
    ...data,
  }));

  // Group by month for trend chart
  const monthMap = new Map<string, { planned: number; actual: number }>();
  for (const item of financials) {
    const existing = monthMap.get(item.month) ?? { planned: 0, actual: 0 };
    existing.planned += item.planned_amount;
    existing.actual += item.actual_amount;
    monthMap.set(item.month, existing);
  }
  const trendData = Array.from(monthMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, data]) => ({ month, ...data }));

  return (
    <div className="space-y-6">
      {/* Budget Breakdown Table */}
      <div className="rounded-lg border border-gray-200 bg-white">
        <div className="border-b border-gray-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-gray-700">Budget Breakdown by Category</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Planned</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Actual</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Variance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {categories.map((cat) => (
                <tr key={cat.category}>
                  <td className="px-4 py-2 text-sm text-gray-900">{cat.category}</td>
                  <td className="px-4 py-2 text-sm text-right text-gray-700">${cat.planned.toLocaleString()}</td>
                  <td className="px-4 py-2 text-sm text-right text-gray-700">${cat.actual.toLocaleString()}</td>
                  <td className={`px-4 py-2 text-sm text-right font-medium ${cat.variance >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {cat.variance >= 0 ? '+' : ''}${Math.abs(cat.variance).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Cost Trend Chart (Monthly) */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Monthly Cost Trend</h3>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 12 }}
              label={{ value: 'Month', position: 'insideBottom', offset: -5 }}
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
            <Line
              type="monotone"
              dataKey="planned"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ r: 4 }}
              name="planned"
            />
            <Line
              type="monotone"
              dataKey="actual"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={{ r: 4 }}
              name="actual"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
