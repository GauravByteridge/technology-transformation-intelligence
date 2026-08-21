import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { getDashboard, resetProject } from '../api/client';
import type { DashboardStats } from '../types';

const PIE_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

interface DashboardScreenProps {
  onProjectReset: () => void;
}

export default function DashboardScreen({ onProjectReset }: DashboardScreenProps) {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  useEffect(() => {
    async function fetchDashboard() {
      try {
        const data = await getDashboard();
        setStats(data);
      } catch (err) {
        setError('Failed to load dashboard data.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchDashboard();
  }, []);

  async function handleReset() {
    try {
      await resetProject();
      onProjectReset(); // Update App state first
      navigate('/');
    } catch (err) {
      setError('Failed to reset project.');
      console.error(err);
    } finally {
      setShowResetConfirm(false);
    }
  }

  if (loading) {
    return <div style={styles.container}><p>Loading dashboard...</p></div>;
  }

  if (error) {
    return <div style={styles.container}><p style={styles.errorText}>{error}</p></div>;
  }

  if (!stats) {
    return null;
  }

  return (
    <div style={styles.container}>
      {/* Project Info */}
      <header style={styles.header}>
        <div>
          <h1 style={styles.title}>{stats.project_name}</h1>
          {stats.project_description && (
            <p style={styles.description}>{stats.project_description}</p>
          )}
        </div>
        <button
          style={styles.resetButton}
          onClick={() => setShowResetConfirm(true)}
          aria-label="Reset project"
        >
          Reset Project
        </button>
      </header>

      {/* Reset Confirmation Dialog */}
      {showResetConfirm && (
        <div style={styles.dialogOverlay} role="dialog" aria-modal="true" aria-labelledby="reset-dialog-title">
          <div style={styles.dialog}>
            <h2 id="reset-dialog-title" style={styles.dialogTitle}>Confirm Reset</h2>
            <p style={styles.dialogText}>
              All data will be permanently deleted, including uploaded files, chat history, and project metadata. This action cannot be undone.
            </p>
            <div style={styles.dialogActions}>
              <button
                style={styles.cancelButton}
                onClick={() => setShowResetConfirm(false)}
              >
                Cancel
              </button>
              <button
                style={styles.confirmButton}
                onClick={handleReset}
              >
                Delete Everything
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Total Files */}
      <div style={styles.statsCard}>
        <span style={styles.statsLabel}>Total Files</span>
        <span style={styles.statsValue}>{stats.total_files}</span>
      </div>

      {/* Empty State */}
      {stats.total_files === 0 ? (
        <div style={styles.emptyState}>
          <p style={styles.emptyText}>No files have been uploaded yet.</p>
          <p style={styles.emptySubtext}>
            Go to Data Management to upload your first file.
          </p>
        </div>
      ) : (
        <>
          {/* Charts Section */}
          <div style={styles.chartsRow}>
            {/* Pie Chart - File Distribution by Type */}
            <div style={styles.chartCard}>
              <h3 style={styles.chartTitle}>Files by Type</h3>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={stats.files_by_type}
                    dataKey="count"
                    nameKey="type"
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    label={({ name, value }: { name?: string; value?: number }) => `${name ?? ''} (${value ?? 0})`}
                  >
                    {stats.files_by_type.map((_entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={PIE_COLORS[index % PIE_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Bar Chart - File Distribution by Category */}
            <div style={styles.chartCard}>
              <h3 style={styles.chartTitle}>Files by Category</h3>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={stats.files_by_category}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="category" tick={{ fontSize: 12 }} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Recent Files */}
          <div style={styles.recentCard}>
            <h3 style={styles.chartTitle}>Recent Files</h3>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>File Name</th>
                  <th style={styles.th}>Upload Date</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_files.map((file) => (
                  <tr key={file.id}>
                    <td style={styles.td}>{file.file_name}</td>
                    <td style={styles.td}>
                      {new Date(file.uploaded_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '2rem',
    maxWidth: '1200px',
    margin: '0 auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '1.5rem',
  },
  title: {
    margin: 0,
    fontSize: '1.75rem',
    color: '#1e293b',
  },
  description: {
    margin: '0.5rem 0 0',
    color: '#64748b',
    fontSize: '1rem',
  },
  resetButton: {
    padding: '0.5rem 1rem',
    backgroundColor: '#dc2626',
    color: '#ffffff',
    border: 'none',
    borderRadius: '0.375rem',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '0.875rem',
  },
  statsCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '1rem 1.5rem',
    backgroundColor: '#f1f5f9',
    borderRadius: '0.5rem',
    marginBottom: '1.5rem',
  },
  statsLabel: {
    fontSize: '0.9rem',
    color: '#64748b',
    fontWeight: 500,
  },
  statsValue: {
    fontSize: '1.5rem',
    fontWeight: 700,
    color: '#1e293b',
  },
  emptyState: {
    textAlign: 'center' as const,
    padding: '3rem 1rem',
    backgroundColor: '#f8fafc',
    borderRadius: '0.5rem',
    border: '1px dashed #cbd5e1',
  },
  emptyText: {
    margin: 0,
    fontSize: '1.1rem',
    color: '#475569',
    fontWeight: 500,
  },
  emptySubtext: {
    margin: '0.5rem 0 0',
    color: '#94a3b8',
    fontSize: '0.9rem',
  },
  chartsRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '1.5rem',
    marginBottom: '1.5rem',
  },
  chartCard: {
    padding: '1.25rem',
    backgroundColor: '#ffffff',
    borderRadius: '0.5rem',
    border: '1px solid #e2e8f0',
  },
  chartTitle: {
    margin: '0 0 1rem',
    fontSize: '1rem',
    color: '#334155',
    fontWeight: 600,
  },
  recentCard: {
    padding: '1.25rem',
    backgroundColor: '#ffffff',
    borderRadius: '0.5rem',
    border: '1px solid #e2e8f0',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
  },
  th: {
    textAlign: 'left' as const,
    padding: '0.75rem',
    borderBottom: '2px solid #e2e8f0',
    fontSize: '0.85rem',
    color: '#64748b',
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.05em',
  },
  td: {
    padding: '0.75rem',
    borderBottom: '1px solid #f1f5f9',
    fontSize: '0.9rem',
    color: '#334155',
  },
  dialogOverlay: {
    position: 'fixed' as const,
    inset: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  dialog: {
    backgroundColor: '#ffffff',
    borderRadius: '0.75rem',
    padding: '2rem',
    maxWidth: '420px',
    width: '90%',
    boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1)',
  },
  dialogTitle: {
    margin: '0 0 0.75rem',
    fontSize: '1.25rem',
    color: '#1e293b',
  },
  dialogText: {
    margin: '0 0 1.5rem',
    color: '#64748b',
    fontSize: '0.9rem',
    lineHeight: 1.6,
  },
  dialogActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '0.75rem',
  },
  cancelButton: {
    padding: '0.5rem 1rem',
    backgroundColor: '#f1f5f9',
    color: '#475569',
    border: '1px solid #e2e8f0',
    borderRadius: '0.375rem',
    cursor: 'pointer',
    fontWeight: 500,
    fontSize: '0.875rem',
  },
  confirmButton: {
    padding: '0.5rem 1rem',
    backgroundColor: '#dc2626',
    color: '#ffffff',
    border: 'none',
    borderRadius: '0.375rem',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '0.875rem',
  },
  errorText: {
    color: '#dc2626',
    fontWeight: 500,
  },
};
