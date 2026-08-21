import { useState } from 'react';
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
import { generateVisualization } from '../api/client';
import type { ChartConfig } from '../types';

const PIE_COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

export default function AIVisualizationScreen() {
  const [query, setQuery] = useState('');
  const [chartConfig, setChartConfig] = useState<ChartConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    setIsLoading(true);
    setError(null);
    setChartConfig(null);

    try {
      const config = await generateVisualization(trimmed);
      setChartConfig(config);
    } catch {
      setError('The requested visualization could not be generated. Please try a different query.');
    } finally {
      setIsLoading(false);
    }
  }

  function renderChart(config: ChartConfig) {
    switch (config.type) {
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={config.data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={config.x_key} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey={config.y_key!} fill="#0088FE" />
            </BarChart>
          </ResponsiveContainer>
        );
      case 'line':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={config.data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={config.x_key} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey={config.y_key!} stroke="#0088FE" />
            </LineChart>
          </ResponsiveContainer>
        );
      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <PieChart>
              <Pie
                data={config.data}
                dataKey={config.data_key!}
                nameKey={config.name_key!}
                cx="50%"
                cy="50%"
                outerRadius={150}
                label
              >
                {config.data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        );
      default:
        return null;
    }
  }

  return (
    <div style={styles.container}>
      <h1 style={styles.heading}>AI Visualization</h1>
      <p style={styles.subtitle}>
        Enter a natural language query to generate a chart from your project data.
      </p>

      <form onSubmit={handleSubmit} style={styles.form}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. Show project costs by category as a bar chart"
          style={styles.input}
          disabled={isLoading}
          aria-label="Visualization query"
        />
        <button type="submit" style={styles.button} disabled={isLoading || !query.trim()}>
          {isLoading ? 'Generating...' : 'Generate'}
        </button>
      </form>

      {error && (
        <div style={styles.error} role="alert">
          {error}
        </div>
      )}

      {chartConfig && (
        <div style={styles.chartContainer}>
          <h2 style={styles.chartTitle}>{chartConfig.title}</h2>
          {renderChart(chartConfig)}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: '900px',
    margin: '0 auto',
    padding: '2rem 1.5rem',
  },
  heading: {
    fontSize: '1.75rem',
    marginBottom: '0.25rem',
  },
  subtitle: {
    color: '#64748b',
    marginBottom: '1.5rem',
  },
  form: {
    display: 'flex',
    gap: '0.75rem',
    marginBottom: '1.5rem',
  },
  input: {
    flex: 1,
    padding: '0.625rem 0.875rem',
    fontSize: '0.95rem',
    border: '1px solid #cbd5e1',
    borderRadius: '0.375rem',
    outline: 'none',
  },
  button: {
    padding: '0.625rem 1.25rem',
    fontSize: '0.95rem',
    fontWeight: 600,
    color: '#ffffff',
    backgroundColor: '#1e293b',
    border: 'none',
    borderRadius: '0.375rem',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
  },
  error: {
    padding: '0.75rem 1rem',
    marginBottom: '1.5rem',
    backgroundColor: '#fef2f2',
    color: '#b91c1c',
    border: '1px solid #fecaca',
    borderRadius: '0.375rem',
  },
  chartContainer: {
    padding: '1.5rem',
    border: '1px solid #e2e8f0',
    borderRadius: '0.5rem',
    backgroundColor: '#ffffff',
  },
  chartTitle: {
    fontSize: '1.25rem',
    marginBottom: '1rem',
    textAlign: 'center' as const,
  },
};
