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

  // ─── Drag and Drop ─────────────────────────────────────────────────────────

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

  // ─── Upload ────────────────────────────────────────────────────────────────

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
      const message =
        err instanceof Error ? err.message : 'Upload failed. Please try again.';
      showNotification('error', message);
    } finally {
      setUploading(false);
    }
  }

  // ─── Download ──────────────────────────────────────────────────────────────

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

  // ─── Delete ────────────────────────────────────────────────────────────────

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

  // ─── Render ────────────────────────────────────────────────────────────────

  return (
    <div style={styles.container}>
      <h1 style={styles.heading}>Data Management</h1>

      {/* Notification */}
      {notification && (
        <div
          style={{
            ...styles.notification,
            backgroundColor: notification.type === 'success' ? '#dcfce7' : '#fee2e2',
            color: notification.type === 'success' ? '#166534' : '#991b1b',
            borderColor: notification.type === 'success' ? '#86efac' : '#fca5a5',
          }}
          role="alert"
        >
          {notification.message}
        </div>
      )}

      {/* Upload Section */}
      <section style={styles.uploadSection}>
        <h2 style={styles.sectionTitle}>Upload File</h2>

        <div
          style={{
            ...styles.dropZone,
            borderColor: dragOver ? '#3b82f6' : '#cbd5e1',
            backgroundColor: dragOver ? '#eff6ff' : '#f8fafc',
          }}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {selectedFile ? (
            <p style={styles.dropText}>
              Selected: <strong>{selectedFile.name}</strong>
            </p>
          ) : (
            <p style={styles.dropText}>
              Drag and drop a file here, or click to browse
            </p>
          )}
          <input
            type="file"
            accept=".pdf,.xlsx,.xls,.csv,.json"
            onChange={handleFileInput}
            style={styles.fileInput}
            aria-label="File upload"
          />
        </div>

        <div style={styles.uploadControls}>
          <label htmlFor="category-select" style={styles.label}>
            Category:
          </label>
          <select
            id="category-select"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value as FileCategory)}
            style={styles.select}
          >
            {FILE_CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>

          <button
            onClick={handleUpload}
            disabled={uploading || !selectedFile}
            style={{
              ...styles.uploadButton,
              opacity: uploading || !selectedFile ? 0.6 : 1,
            }}
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      </section>

      {/* File List Section */}
      <section style={styles.fileSection}>
        <h2 style={styles.sectionTitle}>Uploaded Files</h2>

        {files.length === 0 ? (
          <p style={styles.emptyMessage}>No files uploaded yet.</p>
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
                    <td style={styles.td}>{file.file_name}</td>
                    <td style={styles.td}>{file.file_type.toUpperCase()}</td>
                    <td style={styles.td}>{file.category}</td>
                    <td style={styles.td}>
                      {new Date(file.uploaded_at).toLocaleDateString()}
                    </td>
                    <td style={styles.td}>
                      {deleteConfirmId === file.id ? (
                        <span style={styles.confirmGroup}>
                          <span style={styles.confirmText}>Delete?</span>
                          <button
                            onClick={() => handleDeleteConfirm(file.id)}
                            style={styles.confirmYes}
                          >
                            Yes
                          </button>
                          <button
                            onClick={() => setDeleteConfirmId(null)}
                            style={styles.confirmNo}
                          >
                            No
                          </button>
                        </span>
                      ) : (
                        <span style={styles.actionGroup}>
                          <button
                            onClick={() => handleDownload(file)}
                            style={styles.actionButton}
                          >
                            Download
                          </button>
                          <button
                            onClick={() => setDeleteConfirmId(file.id)}
                            style={styles.deleteButton}
                          >
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

// ─── Styles ────────────────────────────────────────────────────────────────────

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: '1000px',
    margin: '0 auto',
    padding: '2rem 1.5rem',
  },
  heading: {
    fontSize: '1.75rem',
    fontWeight: 700,
    marginBottom: '1.5rem',
    color: '#1e293b',
  },
  notification: {
    padding: '0.75rem 1rem',
    borderRadius: '0.375rem',
    border: '1px solid',
    marginBottom: '1rem',
    fontSize: '0.9rem',
  },
  uploadSection: {
    marginBottom: '2rem',
    padding: '1.5rem',
    borderRadius: '0.5rem',
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
  },
  sectionTitle: {
    fontSize: '1.2rem',
    fontWeight: 600,
    marginBottom: '1rem',
    color: '#334155',
  },
  dropZone: {
    position: 'relative',
    border: '2px dashed',
    borderRadius: '0.5rem',
    padding: '2rem',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'border-color 0.2s, background-color 0.2s',
  },
  dropText: {
    margin: 0,
    color: '#64748b',
    fontSize: '0.95rem',
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
    gap: '1rem',
    marginTop: '1rem',
  },
  label: {
    fontSize: '0.9rem',
    fontWeight: 500,
    color: '#475569',
  },
  select: {
    padding: '0.5rem 0.75rem',
    borderRadius: '0.375rem',
    border: '1px solid #cbd5e1',
    fontSize: '0.9rem',
    backgroundColor: '#ffffff',
  },
  uploadButton: {
    marginLeft: 'auto',
    padding: '0.5rem 1.25rem',
    borderRadius: '0.375rem',
    border: 'none',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    fontWeight: 600,
    fontSize: '0.9rem',
    cursor: 'pointer',
  },
  fileSection: {
    padding: '1.5rem',
    borderRadius: '0.5rem',
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
  },
  emptyMessage: {
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
    borderBottom: '2px solid #e2e8f0',
    fontSize: '0.85rem',
    fontWeight: 600,
    color: '#475569',
    textTransform: 'uppercase',
    letterSpacing: '0.025em',
  },
  tr: {
    borderBottom: '1px solid #f1f5f9',
  },
  td: {
    padding: '0.75rem 1rem',
    fontSize: '0.9rem',
    color: '#334155',
  },
  actionGroup: {
    display: 'flex',
    gap: '0.5rem',
  },
  actionButton: {
    padding: '0.35rem 0.75rem',
    borderRadius: '0.25rem',
    border: '1px solid #cbd5e1',
    backgroundColor: '#ffffff',
    fontSize: '0.8rem',
    cursor: 'pointer',
    color: '#334155',
  },
  deleteButton: {
    padding: '0.35rem 0.75rem',
    borderRadius: '0.25rem',
    border: '1px solid #fca5a5',
    backgroundColor: '#fff1f2',
    fontSize: '0.8rem',
    cursor: 'pointer',
    color: '#991b1b',
  },
  confirmGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  },
  confirmText: {
    fontSize: '0.8rem',
    color: '#991b1b',
    fontWeight: 500,
  },
  confirmYes: {
    padding: '0.25rem 0.5rem',
    borderRadius: '0.25rem',
    border: 'none',
    backgroundColor: '#dc2626',
    color: '#ffffff',
    fontSize: '0.8rem',
    cursor: 'pointer',
  },
  confirmNo: {
    padding: '0.25rem 0.5rem',
    borderRadius: '0.25rem',
    border: '1px solid #cbd5e1',
    backgroundColor: '#ffffff',
    fontSize: '0.8rem',
    cursor: 'pointer',
    color: '#475569',
  },
};
