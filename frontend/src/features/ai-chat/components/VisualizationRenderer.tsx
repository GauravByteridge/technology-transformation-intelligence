import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

// --- Types ---

interface VisualizationRendererProps {
  responseType: 'text' | 'table' | 'chart';
  visualizationSpec: Record<string, unknown> | null;
  isPartial: boolean;
  failedSources: Record<string, unknown>[];
}

interface TableSpec {
  columns: string[];
  rows: Record<string, unknown>[];
}

interface ChartSpec {
  chart_type: 'bar' | 'line' | 'pie';
  data: Record<string, unknown>[];
  xKey: string;
  yKey: string;
}

// Colors for pie chart segments
const PIE_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

// --- Component ---

/**
 * VisualizationRenderer — renders AI response data as table or chart.
 * Does NOT fabricate data; renders nothing if spec is unavailable.
 */
export function VisualizationRenderer({
  responseType,
  visualizationSpec,
  isPartial,
  failedSources,
}: VisualizationRendererProps) {
  return (
    <div className="space-y-3">
      {isPartial && <PartialResponseWarning failedSources={failedSources} />}
      {responseType === 'table' && <TableVisualization spec={visualizationSpec} />}
      {responseType === 'chart' && <ChartVisualization spec={visualizationSpec} />}
      {/* responseType === 'text' renders nothing — text handled by MessageBubble */}
    </div>
  );
}

// --- Partial Response Warning ---

function PartialResponseWarning({ failedSources }: { failedSources: Record<string, unknown>[] }) {
  if (failedSources.length === 0) {
    return (
      <div
        className="rounded-md border border-yellow-200 bg-yellow-50 px-4 py-3"
        role="alert"
        aria-live="polite"
      >
        <p className="text-sm font-medium text-yellow-800">
          Some data sources were unavailable
        </p>
      </div>
    );
  }

  return (
    <div
      className="rounded-md border border-yellow-200 bg-yellow-50 px-4 py-3"
      role="alert"
      aria-live="polite"
    >
      <p className="text-sm font-medium text-yellow-800">
        Some data sources were unavailable
      </p>
      <ul className="mt-2 list-disc pl-5 text-sm text-yellow-700">
        {failedSources.map((source, index) => (
          <li key={index}>
            {getSourceLabel(source)}
          </li>
        ))}
      </ul>
    </div>
  );
}

// --- Table Visualization ---

function TableVisualization({ spec }: { spec: Record<string, unknown> | null }) {
  if (!spec) return null;

  const tableSpec = parseTableSpec(spec);
  if (!tableSpec || tableSpec.columns.length === 0 || tableSpec.rows.length === 0) {
    return null;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {tableSpec.columns.map((col) => (
              <th
                key={col}
                className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {tableSpec.rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {tableSpec.columns.map((col) => (
                <td
                  key={`${rowIndex}-${col}`}
                  className="px-4 py-2 text-sm text-gray-700 whitespace-nowrap"
                >
                  {formatCellValue(row[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --- Chart Visualization ---

function ChartVisualization({ spec }: { spec: Record<string, unknown> | null }) {
  if (!spec) return null;

  const chartSpec = parseChartSpec(spec);
  if (!chartSpec || chartSpec.data.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <ResponsiveContainer width="100%" height={300}>
        {renderChart(chartSpec)}
      </ResponsiveContainer>
    </div>
  );
}

function renderChart(chartSpec: ChartSpec): React.ReactElement {
  const { chart_type, data, xKey, yKey } = chartSpec;

  switch (chart_type) {
    case 'bar':
      return (
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          <Bar dataKey={yKey} fill="#3b82f6" />
        </BarChart>
      );

    case 'line':
      return (
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey={yKey}
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ r: 3 }}
          />
        </LineChart>
      );

    case 'pie':
      return (
        <PieChart>
          <Pie
            data={data}
            dataKey={yKey}
            nameKey={xKey}
            cx="50%"
            cy="50%"
            outerRadius={100}
            label
          >
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      );

    default:
      // Unrecognized chart type — fall back to nothing
      return <BarChart data={[]}><Bar dataKey="" /></BarChart>;
  }
}

// --- Parsing helpers ---

function parseTableSpec(spec: Record<string, unknown>): TableSpec | null {
  const columns = spec.columns;
  const rows = spec.rows;

  if (!Array.isArray(columns) || !Array.isArray(rows)) {
    return null;
  }

  const validColumns = columns.filter((c): c is string => typeof c === 'string');
  if (validColumns.length === 0) {
    return null;
  }

  return {
    columns: validColumns,
    rows: rows as Record<string, unknown>[],
  };
}

function parseChartSpec(spec: Record<string, unknown>): ChartSpec | null {
  const chartType = spec.chart_type;
  const data = spec.data;
  const xKey = spec.xKey;
  const yKey = spec.yKey;

  if (
    typeof chartType !== 'string' ||
    !Array.isArray(data) ||
    typeof xKey !== 'string' ||
    typeof yKey !== 'string'
  ) {
    return null;
  }

  if (!['bar', 'line', 'pie'].includes(chartType)) {
    return null;
  }

  return {
    chart_type: chartType as 'bar' | 'line' | 'pie',
    data: data as Record<string, unknown>[],
    xKey,
    yKey,
  };
}

// --- Utility functions ---

function formatCellValue(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number') return value.toLocaleString();
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return String(value);
}

function getSourceLabel(source: Record<string, unknown>): string {
  // Try common label fields from the backend failed_sources structure
  if (typeof source.name === 'string') return source.name;
  if (typeof source.label === 'string') return source.label;
  if (typeof source.display_name === 'string') return source.display_name;
  if (typeof source.source_name === 'string') return source.source_name;
  return 'Unknown source';
}
