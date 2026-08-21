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

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    // Client-side validation: project name must not be empty/whitespace
    if (!projectName.trim()) {
      setError('Project name is required.');
      return;
    }

    try {
      await createProject(projectName.trim(), description.trim() || undefined);
      onProjectCreated(); // Update App state first
      navigate('/dashboard');
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        const detail = axiosErr.response?.data?.detail;
        setError(detail ?? 'Failed to create project. Please try again.');
      } else {
        setError('Failed to create project. Please try again.');
      }
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Create a New Project</h1>
        <p style={styles.subtitle}>
          Set up your project to begin uploading and analyzing data.
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
            />
          </div>

          {error && (
            <p role="alert" style={styles.error}>
              {error}
            </p>
          )}

          <button type="submit" style={styles.button}>
            Create Project
          </button>
        </form>
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
    backgroundColor: '#f1f5f9',
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: '0.75rem',
    padding: '2.5rem',
    width: '100%',
    maxWidth: '480px',
    boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1)',
  },
  title: {
    margin: '0 0 0.5rem',
    fontSize: '1.5rem',
    fontWeight: 700,
    color: '#1e293b',
  },
  subtitle: {
    margin: '0 0 1.5rem',
    fontSize: '0.9rem',
    color: '#64748b',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.25rem',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.375rem',
  },
  label: {
    fontSize: '0.85rem',
    fontWeight: 600,
    color: '#334155',
  },
  required: {
    color: '#ef4444',
  },
  input: {
    padding: '0.625rem 0.75rem',
    border: '1px solid #cbd5e1',
    borderRadius: '0.375rem',
    fontSize: '0.95rem',
    outline: 'none',
  },
  textarea: {
    padding: '0.625rem 0.75rem',
    border: '1px solid #cbd5e1',
    borderRadius: '0.375rem',
    fontSize: '0.95rem',
    outline: 'none',
    resize: 'vertical',
    fontFamily: 'inherit',
  },
  error: {
    margin: 0,
    padding: '0.5rem 0.75rem',
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '0.375rem',
    color: '#dc2626',
    fontSize: '0.85rem',
  },
  button: {
    padding: '0.75rem',
    backgroundColor: '#1e293b',
    color: '#ffffff',
    border: 'none',
    borderRadius: '0.375rem',
    fontSize: '0.95rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
};
