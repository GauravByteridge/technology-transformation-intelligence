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

const PIE_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

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
      onProjectReset();
      navigate('/');
    } catch (err) {
      setError('Failed to reset project.');
      console.error(err);
    } finally {
      setShowResetConfirm(false);
    }
  }

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loadingState}>
          <div style={styles.spinner} />
          <span style={styles.loadingText}>Loading dashboard...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.container}>
        <div style={styles.errorState}>
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#f87171" strokeWidth="2">
            <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <p style={styles.errorText}>{error}</p>
        </div>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <div style={styles.headerIcon}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
            </svg>
          </div>
          <div>
            <h1 style={styles.title}>{stats.project_name}</h1>
            {stats.project_description && (
              <p style={styles.description}>{stats.project_description}</p>
            )}
          </div>
        </div>
        <button
          style={styles.resetButton}
          onClick={() => setShowResetConfirm(true)}
        >
          Reset Project
        </button>
      </header>

      {/* Reset Confirmation Dialog */}
      {showResetConfirm && (
        <div style={styles.dialogOverlay}>
          <div style={styles.dialog}>
            <div style={styles.dialogIcon}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#f87171" strokeWidth="2">
                <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <h2 style={styles.dialogTitle}>Confirm Reset</h2>
            <p style={styles.dialogText}>
              All data will be permanently deleted, including uploaded files, chat history, and project metadata. This action cannot be undone.
            </p>
            <div style={styles.dialogActions}>
              <button style={styles.cancelButton} onClick={() => setShowResetConfirm(false)}>
                Cancel
              </button>
              <button style={styles.confirmButton} onClick={handleReset}>
                Delete Everything
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      <div style={styles.statsGrid}>
        <div style={styles.statCard}>
          <div style={styles.statIcon}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <div>
            <span style={styles.statValue}>{stats.total_files}</span>
            <span style={styles.statLabel}>Total Files</span>
          </div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statIcon}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" />
            </svg>
          </div>
          <div>
            <span style={styles.statValue}>{stats.files_by_type.length}</span>
            <span style={styles.statLabel}>File Types</span>
          </div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statIcon}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" /><line x1="7" y1="7" x2="7.01" y2="7" />
            </svg>
          </div>
          <div>
            <span style={styles.statValue}>{stats.files_by_category.length}</span>
            <span style={styles.statLabel}>Categories</span>
          </div>
        </div>
      </div>

      {/* Empty State */}
      {stats.total_files === 0 ? (
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="1.5">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <h3 style={styles.emptyTitle}>No files uploaded yet</h3>
          <p style={styles.emptyText}>
            Go to Data Management to upload your first file and start analyzing your project data.
          </p>
        </div>
      ) : (
        <>
          {/* Charts Section */}
          <div style={styles.chartsRow}>
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
                    label={({ name, value }) => `${name} (${value})`}
                    labelLine={{ stroke: '#64748b' }}
                  >
                    {stats.files_by_type.map((_entry, index) => (
                      <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                    labelStyle={{ color: '#f8fafc' }}
                  />
                  <Legend wrapperStyle={{ color: '#94a3b8' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div style={styles.chartCard}>
              <h3 style={styles.chartTitle}>Files by Category</h3>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={stats.files_by_category}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="category" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#334155' }} />
                  <YAxis allowDecimals={false} tick={{ fill: '#94a3b8' }} axisLine={{ stroke: '#334155' }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                    labelStyle={{ color: '#f8fafc' }}
                  />
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
                    <td style={styles.td}>{new Date(file.uploaded_at).toLocaleDateString()}</td>
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
    minHeight: '100vh',
    backgroundColor: '#0f172a',
  },
  loadingState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '50vh',
    gap: '1rem',
  },
  spinner: {
    width: '40px',
    height: '40px',
    border: '3px solid #1e293b',
    borderTop: '3px solid #3b82f6',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  loadingText: {
    color: '#94a3b8',
    fontSize: '0.9rem',
  },
  errorState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '50vh',
    gap: '0.5rem',
  },
  errorIcon: {
    fontSize: '1.5rem',
    color: '#f87171',
  },
  errorText: {
    color: '#f87171',
    fontWeight: 500,
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '2rem',
    paddingBottom: '1.5rem',
    borderBottom: '1px solid #1e293b',
  },
  headerContent: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '1rem',
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
  description: {
    margin: '0.25rem 0 0',
    color: '#94a3b8',
    fontSize: '0.875rem',
  },
  resetButton: {
    padding: '0.625rem 1.25rem',
    backgroundColor: '#7f1d1d',
    color: '#fecaca',
    border: '1px solid #991b1b',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 500,
    fontSize: '0.875rem',
    transition: 'all 0.15s',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '1rem',
    marginBottom: '2rem',
  },
  statCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    padding: '1.25rem',
    backgroundColor: '#1e293b',
    borderRadius: '12px',
    border: '1px solid #334155',
  },
  statIcon: {
    fontSize: '1.5rem',
    width: '48px',
    height: '48px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#0f172a',
    borderRadius: '10px',
  },
  statValue: {
    display: 'block',
    fontSize: '1.75rem',
    fontWeight: 700,
    color: '#f8fafc',
  },
  statLabel: {
    display: 'block',
    fontSize: '0.8rem',
    color: '#64748b',
    marginTop: '0.125rem',
  },
  emptyState: {
    textAlign: 'center',
    padding: '4rem 2rem',
    backgroundColor: '#1e293b',
    borderRadius: '12px',
    border: '1px dashed #334155',
  },
  emptyIcon: {
    fontSize: '3rem',
    marginBottom: '1rem',
  },
  emptyTitle: {
    margin: '0 0 0.5rem',
    fontSize: '1.25rem',
    color: '#f8fafc',
    fontWeight: 600,
  },
  emptyText: {
    margin: 0,
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
    padding: '1.5rem',
    backgroundColor: '#1e293b',
    borderRadius: '12px',
    border: '1px solid #334155',
  },
  chartTitle: {
    margin: '0 0 1rem',
    fontSize: '1rem',
    color: '#f8fafc',
    fontWeight: 600,
  },
  recentCard: {
    padding: '1.5rem',
    backgroundColor: '#1e293b',
    borderRadius: '12px',
    border: '1px solid #334155',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  th: {
    textAlign: 'left',
    padding: '0.75rem 1rem',
    borderBottom: '1px solid #334155',
    fontSize: '0.75rem',
    color: '#64748b',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  td: {
    padding: '0.875rem 1rem',
    borderBottom: '1px solid #1e293b',
    fontSize: '0.9rem',
    color: '#e2e8f0',
  },
  dialogOverlay: {
    position: 'fixed',
    inset: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  dialog: {
    backgroundColor: '#1e293b',
    borderRadius: '16px',
    padding: '2rem',
    maxWidth: '420px',
    width: '90%',
    border: '1px solid #334155',
    textAlign: 'center',
  },
  dialogIcon: {
    fontSize: '3rem',
    marginBottom: '1rem',
  },
  dialogTitle: {
    margin: '0 0 0.75rem',
    fontSize: '1.25rem',
    color: '#f8fafc',
    fontWeight: 600,
  },
  dialogText: {
    margin: '0 0 1.5rem',
    color: '#94a3b8',
    fontSize: '0.9rem',
    lineHeight: 1.6,
  },
  dialogActions: {
    display: 'flex',
    justifyContent: 'center',
    gap: '0.75rem',
  },
  cancelButton: {
    padding: '0.625rem 1.25rem',
    backgroundColor: '#0f172a',
    color: '#e2e8f0',
    border: '1px solid #334155',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 500,
    fontSize: '0.875rem',
  },
  confirmButton: {
    padding: '0.625rem 1.25rem',
    backgroundColor: '#dc2626',
    color: '#ffffff',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '0.875rem',
  },
};
