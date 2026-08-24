import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { createProject } from '../api/client';

interface CreateProjectScreenProps {
  onProjectCreated: () => void;
}

export default function CreateProjectScreen({ onProjectCreated }: CreateProjectScreenProps) {
  const navigate = useNavigate();

  const [projectName, setProjectName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!projectName.trim()) {
      setError('Project name is required.');
      return;
    }

    setLoading(true);
    try {
      await createProject(projectName.trim(), description.trim() || undefined);
      onProjectCreated();
      navigate('/dashboard');
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        const detail = axiosErr.response?.data?.detail;
        setError(detail ?? 'Failed to create project. Please try again.');
      } else {
        setError('Failed to create project. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.logoSection}>
          <div style={styles.logo}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 16v-4M12 8h.01" />
            </svg>
          </div>
          <h1 style={styles.brandName}>Intelligence Hub</h1>
        </div>

        <h2 style={styles.title}>Create a New Project</h2>
        <p style={styles.subtitle}>
          Set up your project to begin uploading and analyzing data with AI-powered insights.
        </p>

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.field}>
            <label htmlFor="projectName" style={styles.label}>
              Project Name <span style={styles.required}>*</span>
            </label>
            <input
              id="projectName"
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="Enter project name"
              style={styles.input}
              autoFocus
              disabled={loading}
            />
          </div>

          <div style={styles.field}>
            <label htmlFor="description" style={styles.label}>
              Description
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe your project (optional)"
              rows={3}
              style={styles.textarea}
              disabled={loading}
            />
          </div>

          {error && (
            <p role="alert" style={styles.error}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
              </svg>
              {error}
            </p>
          )}

          <button 
            type="submit" 
            style={{
              ...styles.button,
              opacity: loading ? 0.7 : 1,
            }}
            disabled={loading}
          >
            {loading ? 'Creating...' : 'Create Project'}
          </button>
        </form>

        <p style={styles.footerText}>
          Your data stays secure and private within your project.
        </p>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    padding: '2rem',
    backgroundColor: '#0f172a',
  },
  card: {
    backgroundColor: '#1e293b',
    borderRadius: '16px',
    padding: '2.5rem',
    width: '100%',
    maxWidth: '440px',
    border: '1px solid #334155',
  },
  logoSection: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '0.75rem',
    marginBottom: '2rem',
  },
  logo: {
    fontSize: '2rem',
    width: '48px',
    height: '48px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1e40af',
    borderRadius: '12px',
  },
  brandName: {
    margin: 0,
    fontSize: '1.25rem',
    fontWeight: 600,
    color: '#f8fafc',
  },
  title: {
    margin: '0 0 0.5rem',
    fontSize: '1.375rem',
    fontWeight: 600,
    color: '#f8fafc',
    textAlign: 'center',
  },
  subtitle: {
    margin: '0 0 2rem',
    fontSize: '0.875rem',
    color: '#94a3b8',
    textAlign: 'center',
    lineHeight: 1.5,
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.25rem',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  },
  label: {
    fontSize: '0.875rem',
    fontWeight: 500,
    color: '#e2e8f0',
  },
  required: {
    color: '#f87171',
  },
  input: {
    padding: '0.75rem 1rem',
    border: '1px solid #334155',
    borderRadius: '8px',
    fontSize: '0.95rem',
    backgroundColor: '#0f172a',
    color: '#f8fafc',
    outline: 'none',
    transition: 'border-color 0.15s',
  },
  textarea: {
    padding: '0.75rem 1rem',
    border: '1px solid #334155',
    borderRadius: '8px',
    fontSize: '0.95rem',
    backgroundColor: '#0f172a',
    color: '#f8fafc',
    outline: 'none',
    resize: 'vertical',
    fontFamily: 'inherit',
    transition: 'border-color 0.15s',
  },
  error: {
    margin: 0,
    padding: '0.75rem 1rem',
    backgroundColor: 'rgba(127, 29, 29, 0.3)',
    border: '1px solid #7f1d1d',
    borderRadius: '8px',
    color: '#fca5a5',
    fontSize: '0.875rem',
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  },
  errorIcon: {
    fontWeight: 'bold',
  },
  button: {
    padding: '0.875rem',
    backgroundColor: '#3b82f6',
    color: '#ffffff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '0.95rem',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s',
    marginTop: '0.5rem',
  },
  footerText: {
    margin: '1.5rem 0 0',
    fontSize: '0.75rem',
    color: '#64748b',
    textAlign: 'center',
  },
};
