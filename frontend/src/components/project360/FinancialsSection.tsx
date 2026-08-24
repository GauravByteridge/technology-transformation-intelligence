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
import { useProjectFinance } from '@/hooks';
import { LoadingState } from '@/components/common/LoadingState';
import { ErrorState } from '@/components/common/ErrorState';
import { EmptyState } from '@/components/common/EmptyState';

interface FinancialsSectionProps {
  projectId: string;
}

/**
 * FinancialsSection — displays live financial data for a project.
 * Shows budget summary, actual cost entries, and monthly trend chart.
 */
export function FinancialsSection({ projectId }: FinancialsSectionProps) {
  const { data: finance, isLoading, isError, refetch } = useProjectFinance(projectId);

  if (isLoading) {
    return <LoadingState variant="skeleton" message="Loading financial data..." />;
  }

  if (isError) {
    return (
      <ErrorState
        message="Failed to load financial data. Please try again."
        onRetry={() => refetch()}
      />
    );
  }

  if (!finance || (finance.budget === null && finance.actual_costs.length === 0)) {
    return (
      <EmptyState message="No financial data available for this project." />
    );
  }

  const totalBudget = finance.budget?.total_budget ?? 0;

  return (
    <div className="space-y-6">
      {/* Budget Summary */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Budget Summary</h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <SummaryCard
            label="Total Budget"
            value={formatCurrency(totalBudget)}
          />
          <SummaryCard
            label="Total Spent"
            value={formatCurrency(finance.total_spent)}
          />
          <SummaryCard
            label="Budget Variance"
            value={formatCurrency(finance.budget_variance)}
            colorClass={finance.budget_variance >= 0 ? 'text-green-600' : 'text-red-600'}
          />
          <SummaryCard
            label="Variance %"
            value={`${(Number(finance.variance_percentage) || 0) >= 0 ? '+' : ''}${(Number(finance.variance_percentage) || 0).toFixed(1)}%`}
            colorClass={(Number(finance.variance_percentage) || 0) >= 0 ? 'text-green-600' : 'text-red-600'}
          />
        </div>
      </div>

      {/* Actual Cost Entries Table */}
      {finance.actual_costs.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white">
          <div className="border-b border-gray-200 px-4 py-3">
            <h3 className="text-sm font-semibold text-gray-700">Actual Cost Entries</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Category
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">
                    Amount
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Date
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Description
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {finance.actual_costs.map((cost) => (
                  <tr key={cost.id}>
                    <td className="px-4 py-2 text-sm text-gray-900">
                      {cost.cost_category_id}
                    </td>
                    <td className="px-4 py-2 text-sm text-right text-gray-700">
                      {formatCurrency(cost.amount)}
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-700">
                      {formatDate(cost.incurred_date)}
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-500">
                      {cost.description ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Monthly Trend Chart */}
      {finance.monthly_trends.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Monthly Cost Trend</h3>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={finance.monthly_trends}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="year_month"
                tick={{ fontSize: 12 }}
              />
              <YAxis
                tick={{ fontSize: 12 }}
                tickFormatter={(value: number) => formatCompactCurrency(value)}
              />
              <Tooltip
                formatter={(value, name) => [
                  formatCurrency(Number(value)),
                  trendLegendLabel(String(name)),
                ]}
                labelFormatter={(label) => `Month: ${String(label)}`}
              />
              <Legend formatter={(value: string) => trendLegendLabel(value)} />
              <Line
                type="monotone"
                dataKey="planned_spend"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ r: 3 }}
                name="planned_spend"
              />
              <Line
                type="monotone"
                dataKey="actual_spend"
                stroke="#f59e0b"
                strokeWidth={2}
                dot={{ r: 3 }}
                name="actual_spend"
              />
              <Line
                type="monotone"
                dataKey="cumulative_planned"
                stroke="#6366f1"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
                name="cumulative_planned"
              />
              <Line
                type="monotone"
                dataKey="cumulative_actual"
                stroke="#ef4444"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
                name="cumulative_actual"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

// --- Helper components ---

interface SummaryCardProps {
  label: string;
  value: string;
  colorClass?: string;
}

function SummaryCard({ label, value, colorClass }: SummaryCardProps) {
  return (
    <div className="rounded-md bg-gray-50 p-3">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-lg font-semibold ${colorClass ?? 'text-gray-900'}`}>
        {value}
      </p>
    </div>
  );
}

// --- Utility functions ---

function formatCurrency(amount: number): string {
  return `$${amount.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

function formatCompactCurrency(amount: number): string {
  const num = Number(amount) || 0;
  if (Math.abs(num) >= 1_000_000) {
    return `$${(num / 1_000_000).toFixed(1)}M`;
  }
  if (Math.abs(num) >= 1_000) {
    return `$${(num / 1_000).toFixed(0)}K`;
  }
  return `$${num}`;
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

function trendLegendLabel(name: string): string {
  const labels: Record<string, string> = {
    planned_spend: 'Planned Spend',
    actual_spend: 'Actual Spend',
    cumulative_planned: 'Cumulative Planned',
    cumulative_actual: 'Cumulative Actual',
  };
  return labels[name] ?? name;
}
