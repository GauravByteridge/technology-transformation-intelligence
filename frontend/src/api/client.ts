import axios from 'axios';
import type {
  Project,
  ProjectFile,
  FileCategory,
  ChatMessage,
  DashboardStats,
  ChartConfig,
} from '../types';

// Axios instance with base configuration
const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// ─── Project Endpoints ───────────────────────────────────────────────────────

/** POST /api/project — Create a new project */
export async function createProject(
  name: string,
  description?: string
): Promise<Project> {
  const response = await apiClient.post<Project>('/project', {
    name,
    description: description ?? null,
  });
  return response.data;
}

/** GET /api/project — Retrieve current project details */
export async function getProject(): Promise<Project | null> {
  try {
    const response = await apiClient.get<Project>('/project');
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      return null;
    }
    throw error;
  }
}

/** DELETE /api/project/reset — Reset all project data */
export async function resetProject(): Promise<void> {
  await apiClient.delete('/project/reset');
}

// ─── File Endpoints ──────────────────────────────────────────────────────────

/** POST /api/files/upload — Upload a file with category metadata */
export async function uploadFile(
  file: File,
  category: FileCategory
): Promise<ProjectFile> {
  // Check file size on client side first (50 MB limit)
  const MAX_FILE_SIZE_MB = 50;
  const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
  
  if (file.size > MAX_FILE_SIZE_BYTES) {
    throw new Error(`File size (${(file.size / 1024 / 1024).toFixed(1)} MB) exceeds maximum allowed size of ${MAX_FILE_SIZE_MB} MB.`);
  }

  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await apiClient.post<ProjectFile>(
      `/files/upload?category=${encodeURIComponent(category)}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000, // 5 minutes timeout for large file uploads
        maxContentLength: Infinity,
        maxBodyLength: Infinity,
      }
    );
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      if (error.response?.status === 413) {
        throw new Error('File is too large. Maximum allowed size is 50 MB.');
      }
      if (error.response?.status === 422) {
        throw new Error(error.response.data?.detail || 'Failed to process file. Please check the file format.');
      }
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      if (error.code === 'ECONNABORTED') {
        throw new Error('Upload timed out. Please try again with a smaller file.');
      }
    }
    throw error;
  }
}

/** GET /api/files — List all uploaded files */
export async function getFiles(): Promise<ProjectFile[]> {
  const response = await apiClient.get<ProjectFile[]>('/files');
  return response.data;
}

/** GET /api/files/{id} — Download a specific file */
export async function downloadFile(id: number): Promise<Blob> {
  const response = await apiClient.get(`/files/${id}`, {
    responseType: 'blob',
  });
  return response.data;
}

/** DELETE /api/files/{id} — Delete a specific file */
export async function deleteFile(id: number): Promise<void> {
  await apiClient.delete(`/files/${id}`);
}

// ─── Dashboard Endpoint ──────────────────────────────────────────────────────

/** GET /api/dashboard — Retrieve dashboard statistics */
export async function getDashboard(): Promise<DashboardStats> {
  const response = await apiClient.get<DashboardStats>('/dashboard');
  return response.data;
}

// ─── Chat Endpoint ───────────────────────────────────────────────────────────

/** Response shape from POST /api/chat */
interface ChatApiResponse {
  answer: string;
  sources: string[];
}

/** POST /api/chat — Send a chat message and receive AI response */
export async function sendChatMessage(question: string): Promise<ChatMessage> {
  const response = await apiClient.post<ChatApiResponse>('/chat', { question });
  return {
    id: crypto.randomUUID(),
    role: 'assistant',
    content: response.data.answer,
    sources: response.data.sources,
    timestamp: new Date().toISOString(),
  };
}

// ─── Visualization Endpoint ──────────────────────────────────────────────────

/** POST /api/visualize — Generate a chart from a natural language query */
export async function generateVisualization(
  query: string
): Promise<ChartConfig> {
  const response = await apiClient.post<ChartConfig>('/visualize', { query });
  return response.data;
}

// Export the axios instance for advanced use cases
export default apiClient;
