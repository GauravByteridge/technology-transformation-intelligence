import { useState, useEffect, useCallback } from 'react';
import type { ProjectFile, FileCategory } from '../types';
import { getFiles, uploadFile, downloadFile, deleteFile } from '../api/client';

const FILE_CATEGORIES: FileCategory[] = [
  'Project Costs',
  'Burndown',
  'Audit',
  'IT Controls',
  'Remediation',
  'Business Intelligence',
  'Internal Data',
  'Other',
];

interface Notification {
  type: 'success' | 'error';
  message: string;
}

export default function DataManagementScreen() {
  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<FileCategory>('Other');
  const [uploading, setUploading] = useState(false);
  const [notification, setNotification] = useState<Notification | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const loadFiles = useCallback(async () => {
    try {
      const data = await getFiles();
      setFiles(data);
    } catch {
      showNotification('error', 'Failed to load files.');
    }
  }, []);

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  function showNotification(type: 'success' | 'error', message: string) {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 4000);
  }

  function handleDragOver(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  }

  function handleDragLeave(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setSelectedFile(droppedFile);
    }
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setSelectedFile(file);
  }

  async function handleUpload() {
    if (!selectedFile) {
      showNotification('error', 'Please select a file to upload.');
      return;
    }

    setUploading(true);
    try {
      await uploadFile(selectedFile, selectedCategory);
      showNotification('success', `File "${selectedFile.name}" uploaded successfully.`);
      setSelectedFile(null);
      await loadFiles();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed. Please try again.';
      showNotification('error', message);
    } finally {
      setUploading(false);
    }
  }

  async function handleDownload(file: ProjectFile) {
    try {
      const blob = await downloadFile(file.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = file.file_name;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
    } catch {
      showNotification('error', `Failed to download "${file.file_name}".`);
    }
  }

  async function handleDeleteConfirm(id: number) {
    try {
      await deleteFile(id);
      showNotification('success', 'File deleted successfully.');
      setDeleteConfirmId(null);
      await loadFiles();
    } catch {
      showNotification('error', 'Failed to delete file.');
      setDeleteConfirmId(null);
    }
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerIcon}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        <div>
          <h1 style={styles.title}>Data Management</h1>
          <p style={styles.subtitle}>Upload, manage, and organize your project files.</p>
        </div>
      </div>

      {/* Notification */}
      {notification && (
        <div
          style={{
            ...styles.notification,
            backgroundColor: notification.type === 'success' ? '#064e3b' : '#7f1d1d',
            borderColor: notification.type === 'success' ? '#10b981' : '#f87171',
          }}
        >
          <span style={styles.notificationIcon}>
            {notification.type === 'success' ? '✓' : '✕'}
          </span>
          {notification.message}
        </div>
      )}

      {/* Upload Section */}
      <section style={styles.uploadSection}>
        <h2 style={styles.sectionTitle}>Upload File</h2>

        <div
          style={{
            ...styles.dropZone,
            borderColor: dragOver ? '#3b82f6' : '#334155',
            backgroundColor: dragOver ? 'rgba(59, 130, 246, 0.1)' : '#1e293b',
          }}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div style={styles.dropContent}>
            <span style={styles.dropIcon}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="1.5">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </span>
            {selectedFile ? (
              <p style={styles.dropText}>
                Selected: <strong style={{ color: '#f8fafc' }}>{selectedFile.name}</strong>
              </p>
            ) : (
              <p style={styles.dropText}>
                Drag and drop a file here, or click to browse
              </p>
            )}
            <p style={styles.dropHint}>Supported: PDF, XLSX, XLS, CSV, JSON (max 50MB)</p>
          </div>
          <input
            type="file"
            accept=".pdf,.xlsx,.xls,.csv,.json"
            onChange={handleFileInput}
            style={styles.fileInput}
          />
        </div>

        <div style={styles.uploadControls}>
          <div style={styles.categorySelect}>
            <label htmlFor="category-select" style={styles.label}>Category:</label>
            <select
              id="category-select"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value as FileCategory)}
              style={styles.select}
            >
              {FILE_CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          <button
            onClick={handleUpload}
            disabled={uploading || !selectedFile}
            style={{
              ...styles.uploadButton,
              opacity: uploading || !selectedFile ? 0.5 : 1,
            }}
          >
            {uploading ? 'Uploading...' : 'Upload File'}
          </button>
        </div>
      </section>

      {/* File List Section */}
      <section style={styles.fileSection}>
        <h2 style={styles.sectionTitle}>Uploaded Files ({files.length})</h2>

        {files.length === 0 ? (
          <div style={styles.emptyState}>
            <span style={styles.emptyIcon}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="1.5">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
              </svg>
            </span>
            <p style={styles.emptyText}>No files uploaded yet.</p>
          </div>
        ) : (
          <div style={styles.tableWrapper}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Name</th>
                  <th style={styles.th}>Type</th>
                  <th style={styles.th}>Category</th>
                  <th style={styles.th}>Upload Date</th>
                  <th style={styles.th}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {files.map((file) => (
                  <tr key={file.id} style={styles.tr}>
                    <td style={styles.td}>
                      <span style={styles.fileName}>{file.file_name}</span>
                    </td>
                    <td style={styles.td}>
                      <span style={styles.fileType}>{file.file_type.toUpperCase()}</span>
                    </td>
                    <td style={styles.td}>
                      <span style={styles.categoryTag}>{file.category}</span>
                    </td>
                    <td style={styles.td}>
                      {new Date(file.uploaded_at).toLocaleDateString()}
                    </td>
                    <td style={styles.td}>
                      {deleteConfirmId === file.id ? (
                        <span style={styles.confirmGroup}>
                          <span style={styles.confirmText}>Delete?</span>
                          <button onClick={() => handleDeleteConfirm(file.id)} style={styles.confirmYes}>
                            Yes
                          </button>
                          <button onClick={() => setDeleteConfirmId(null)} style={styles.confirmNo}>
                            No
                          </button>
                        </span>
                      ) : (
                        <span style={styles.actionGroup}>
                          <button onClick={() => handleDownload(file)} style={styles.actionButton}>
                            Download
                          </button>
                          <button onClick={() => setDeleteConfirmId(file.id)} style={styles.deleteButton}>
                            Delete
                          </button>
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
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
  notification: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.875rem 1rem',
    borderRadius: '8px',
    border: '1px solid',
    marginBottom: '1.5rem',
    fontSize: '0.9rem',
    color: '#f8fafc',
  },
  notificationIcon: {
    fontSize: '1rem',
    fontWeight: 'bold',
  },
  uploadSection: {
    marginBottom: '2rem',
    padding: '1.5rem',
    borderRadius: '12px',
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
  },
  sectionTitle: {
    margin: '0 0 1rem',
    fontSize: '1rem',
    fontWeight: 600,
    color: '#f8fafc',
  },
  dropZone: {
    position: 'relative',
    border: '2px dashed',
    borderRadius: '12px',
    padding: '2.5rem',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  dropContent: {
    pointerEvents: 'none',
  },
  dropIcon: {
    display: 'block',
    marginBottom: '0.75rem',
  },
  dropText: {
    margin: 0,
    color: '#94a3b8',
    fontSize: '0.95rem',
  },
  dropHint: {
    margin: '0.5rem 0 0',
    color: '#64748b',
    fontSize: '0.8rem',
  },
  fileInput: {
    position: 'absolute',
    inset: 0,
    width: '100%',
    height: '100%',
    opacity: 0,
    cursor: 'pointer',
  },
  uploadControls: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: '1.25rem',
    paddingTop: '1.25rem',
    borderTop: '1px solid #334155',
  },
  categorySelect: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
  },
  label: {
    fontSize: '0.875rem',
    fontWeight: 500,
    color: '#94a3b8',
  },
  select: {
    padding: '0.5rem 0.75rem',
    borderRadius: '8px',
    border: '1px solid #334155',
    backgroundColor: '#0f172a',
    color: '#f8fafc',
    fontSize: '0.875rem',
  },
  uploadButton: {
    padding: '0.625rem 1.5rem',
    borderRadius: '8px',
    border: 'none',
    backgroundColor: '#3b82f6',
    color: '#ffffff',
    fontWeight: 600,
    fontSize: '0.875rem',
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  fileSection: {
    padding: '1.5rem',
    borderRadius: '12px',
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
  },
  emptyState: {
    textAlign: 'center',
    padding: '3rem 1rem',
  },
  emptyIcon: {
    display: 'block',
    marginBottom: '0.75rem',
  },
  emptyText: {
    margin: 0,
    color: '#64748b',
    fontStyle: 'italic',
  },
  tableWrapper: {
    overflowX: 'auto',
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
    fontWeight: 600,
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  tr: {
    transition: 'background-color 0.15s',
  },
  td: {
    padding: '0.875rem 1rem',
    borderBottom: '1px solid #1e293b',
    fontSize: '0.875rem',
    color: '#e2e8f0',
  },
  fileName: {
    fontWeight: 500,
  },
  fileType: {
    padding: '0.25rem 0.5rem',
    backgroundColor: '#0f172a',
    borderRadius: '4px',
    fontSize: '0.75rem',
    fontWeight: 600,
    color: '#94a3b8',
  },
  categoryTag: {
    padding: '0.25rem 0.5rem',
    backgroundColor: '#1e3a8a',
    borderRadius: '4px',
    fontSize: '0.75rem',
    color: '#93c5fd',
  },
  actionGroup: {
    display: 'flex',
    gap: '0.5rem',
  },
  actionButton: {
    padding: '0.375rem 0.75rem',
    borderRadius: '6px',
    border: '1px solid #334155',
    backgroundColor: '#0f172a',
    fontSize: '0.8rem',
    cursor: 'pointer',
    color: '#e2e8f0',
    transition: 'all 0.15s',
  },
  deleteButton: {
    padding: '0.375rem 0.75rem',
    borderRadius: '6px',
    border: '1px solid #7f1d1d',
    backgroundColor: 'rgba(127, 29, 29, 0.3)',
    fontSize: '0.8rem',
    cursor: 'pointer',
    color: '#fca5a5',
    transition: 'all 0.15s',
  },
  confirmGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  },
  confirmText: {
    fontSize: '0.8rem',
    color: '#fca5a5',
    fontWeight: 500,
  },
  confirmYes: {
    padding: '0.25rem 0.625rem',
    borderRadius: '6px',
    border: 'none',
    backgroundColor: '#dc2626',
    color: '#ffffff',
    fontSize: '0.8rem',
    cursor: 'pointer',
  },
  confirmNo: {
    padding: '0.25rem 0.625rem',
    borderRadius: '6px',
    border: '1px solid #334155',
    backgroundColor: '#0f172a',
    fontSize: '0.8rem',
    cursor: 'pointer',
    color: '#e2e8f0',
  },
};
