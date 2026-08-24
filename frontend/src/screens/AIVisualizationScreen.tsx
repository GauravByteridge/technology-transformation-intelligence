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

const PIE_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

const SUGGESTED_QUERIES = [
  'Show project costs by category as a bar chart',
  'Display file distribution by type as a pie chart',
  'Create a line chart of costs over time',
  'Visualize budget vs actual spending',
];

export default function AIVisualizationScreen() {
  const [query, setQuery] = useState('');
  const [chartConfig, setChartConfig] = useState<ChartConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    await generateChart(trimmed);
  }

  async function generateChart(queryText: string) {
    setIsLoading(true);
    setError(null);
    setChartConfig(null);

    try {
      const config = await generateVisualization(queryText);
      setChartConfig(config);
    } catch {
      setError('The requested visualization could not be generated. Please try a different query.');
    } finally {
      setIsLoading(false);
    }
  }

  function handleSuggestion(suggestion: string) {
    setQuery(suggestion);
    generateChart(suggestion);
  }

  function renderChart(config: ChartConfig) {
    const tooltipStyle = {
      contentStyle: { backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' },
      labelStyle: { color: '#f8fafc' },
    };

    switch (config.type) {
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={config.data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey={config.x_key} tick={{ fill: '#94a3b8' }} axisLine={{ stroke: '#334155' }} />
              <YAxis tick={{ fill: '#94a3b8' }} axisLine={{ stroke: '#334155' }} />
              <Tooltip {...tooltipStyle} />
              <Legend wrapperStyle={{ color: '#94a3b8' }} />
              <Bar dataKey={config.y_key!} fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        );
      case 'line':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={config.data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey={config.x_key} tick={{ fill: '#94a3b8' }} axisLine={{ stroke: '#334155' }} />
              <YAxis tick={{ fill: '#94a3b8' }} axisLine={{ stroke: '#334155' }} />
              <Tooltip {...tooltipStyle} />
              <Legend wrapperStyle={{ color: '#94a3b8' }} />
              <Line type="monotone" dataKey={config.y_key!} stroke="#3b82f6" strokeWidth={2} dot={{ fill: '#3b82f6' }} />
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
                label={({ name, value }) => `${name}: ${value}`}
                labelLine={{ stroke: '#64748b' }}
              >
                {config.data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip {...tooltipStyle} />
              <Legend wrapperStyle={{ color: '#94a3b8' }} />
            </PieChart>
          </ResponsiveContainer>
        );
      default:
        return null;
    }
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerIcon}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" />
          </svg>
        </div>
        <div>
          <h1 style={styles.title}>AI Visualization</h1>
          <p style={styles.subtitle}>
            Enter a natural language query to generate charts from your project data.
          </p>
        </div>
      </div>

      {/* Input Section */}
      <div style={styles.inputSection}>
        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.inputWrapper}>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Describe the visualization you want..."
              style={styles.input}
              disabled={isLoading}
            />
            <button
              type="submit"
              style={{
                ...styles.generateButton,
                opacity: isLoading || !query.trim() ? 0.5 : 1,
              }}
              disabled={isLoading || !query.trim()}
            >
              {isLoading ? 'Generating...' : 'Generate'}
            </button>
          </div>
        </form>
      </div>

      {/* Error Message */}
      {error && (
        <div style={styles.error}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </div>
      )}

      {/* Chart Display */}
      {chartConfig && (
        <div style={styles.chartContainer}>
          <h2 style={styles.chartTitle}>{chartConfig.title}</h2>
          {renderChart(chartConfig)}
        </div>
      )}

      {/* Suggestions (when no chart is displayed) */}
      {!chartConfig && !error && (
        <div style={styles.suggestionsSection}>
          <h3 style={styles.suggestionsTitle}>Try These Queries</h3>
          <div style={styles.suggestionsList}>
            {SUGGESTED_QUERIES.map((suggestion, idx) => (
              <button
                key={idx}
                onClick={() => handleSuggestion(suggestion)}
                style={styles.suggestionButton}
                disabled={isLoading}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '2rem',
    minHeight: '100vh',
    backgroundColor: '#0f172a',
  },
  header: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '1rem',
    marginBottom: '2rem',
    paddingBottom: '1.5rem',
    borderBottom: '1px solid #1e293b',
  },
  headerIcon: {
    fontSize: '2rem',
    width: '48px',
    height: '48px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1e3a8a',
    borderRadius: '12px',
  },
  title: {
    margin: 0,
    fontSize: '1.5rem',
    fontWeight: 600,
    color: '#f8fafc',
  },
  subtitle: {
    margin: '0.25rem 0 0',
    fontSize: '0.875rem',
    color: '#94a3b8',
  },
  inputSection: {
    marginBottom: '2rem',
  },
  form: {
    width: '100%',
  },
  inputWrapper: {
    display: 'flex',
    gap: '0.75rem',
    backgroundColor: '#1e293b',
    borderRadius: '12px',
    border: '1px solid #334155',
    padding: '0.5rem',
  },
  input: {
    flex: 1,
    backgroundColor: 'transparent',
    border: 'none',
    outline: 'none',
    fontSize: '0.95rem',
    color: '#f8fafc',
    padding: '0.625rem 0.75rem',
  },
  generateButton: {
    padding: '0.625rem 1.5rem',
    backgroundColor: '#3b82f6',
    color: '#ffffff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '0.9rem',
    fontWeight: 600,
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    transition: 'all 0.15s',
  },
  error: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '1rem 1.25rem',
    marginBottom: '1.5rem',
    backgroundColor: 'rgba(127, 29, 29, 0.3)',
    color: '#fca5a5',
    border: '1px solid #7f1d1d',
    borderRadius: '12px',
  },
  errorIcon: {
    fontSize: '1.25rem',
  },
  chartContainer: {
    padding: '1.5rem',
    backgroundColor: '#1e293b',
    borderRadius: '12px',
    border: '1px solid #334155',
  },
  chartTitle: {
    margin: '0 0 1.5rem',
    fontSize: '1.125rem',
    fontWeight: 600,
    color: '#f8fafc',
    textAlign: 'center',
  },
  suggestionsSection: {
    marginTop: '1rem',
  },
  suggestionsTitle: {
    margin: '0 0 1rem',
    fontSize: '0.875rem',
    fontWeight: 600,
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  suggestionsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  },
  suggestionButton: {
    textAlign: 'left',
    padding: '0.875rem 1rem',
    backgroundColor: 'transparent',
    border: '1px solid #1e293b',
    borderRadius: '8px',
    color: '#e2e8f0',
    fontSize: '0.9rem',
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
};
