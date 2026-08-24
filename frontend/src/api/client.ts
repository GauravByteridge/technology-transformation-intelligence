import { apiClient as baseClient } from '@/services/api-client';
import type { ApiClient } from '@/services/api-client';
import type {
  PortfolioSummaryResponse,
  ProjectListResponse,
  ProjectResponse,
  ProjectHealthResponse,
  ProjectFinanceResponse,
  ProjectJiraResponse,
  ProjectResourceResponse,
  ProjectAuditResponse,
  ProjectControlsResponse,
  ProjectRemediationResponse,
  ProjectSdlcResponse,
  ProjectProgressResponse,
  ProjectRisksResponse,
  DataSourceResponse,
  DocumentResponse,
  DocumentSearchRequest,
  DocumentSearchResponse,
  AIQueryRequest,
  AIResponse,
  FileUploadResponse,
  DatasetResponse,
  DatasetPreviewResponse,
  DatasetDetailResponse,
  DatasetQueryRequest,
  DatasetQueryResponse,
  DatasetConfirmRequest,
} from '../types';

/**
 * Domain-specific API client that delegates HTTP communication
 * to the centralized typed ApiClient in services/api-client.ts.
 *
 * All paths use the versioned /api/v1/ prefix matching the backend router.
 */
class APIClient {
  private client: ApiClient;

  constructor(client: ApiClient = baseClient) {
    this.client = client;
  }

  // ─── Portfolio / Dashboard ──────────────────────────────────

  async getDashboardSummary(): Promise<PortfolioSummaryResponse> {
    const response = await this.client.get<PortfolioSummaryResponse>('/api/v1/portfolio/summary');
    return response.data;
  }

  // ─── Projects ───────────────────────────────────────────────

  async getProjects(): Promise<ProjectListResponse> {
    const response = await this.client.get<ProjectListResponse>('/api/v1/projects');
    return response.data;
  }

  async getProjectById(id: string): Promise<ProjectResponse> {
    const response = await this.client.get<ProjectResponse>(`/api/v1/projects/${id}`);
    return response.data;
  }

  // ─── Project Domain Endpoints ───────────────────────────────

  async getProjectHealth(id: string): Promise<ProjectHealthResponse> {
    const response = await this.client.get<ProjectHealthResponse>(`/api/v1/projects/${id}/health`);
    return response.data;
  }

  async getProjectFinance(id: string): Promise<ProjectFinanceResponse> {
    const response = await this.client.get<ProjectFinanceResponse>(`/api/v1/projects/${id}/finance`);
    return response.data;
  }

  async getProjectJira(id: string): Promise<ProjectJiraResponse> {
    const response = await this.client.get<ProjectJiraResponse>(`/api/v1/projects/${id}/jira`);
    return response.data;
  }

  async getProjectResources(id: string): Promise<ProjectResourceResponse> {
    const response = await this.client.get<ProjectResourceResponse>(
      `/api/v1/projects/${id}/resources`,
    );
    return response.data;
  }

  async getProjectAudit(id: string): Promise<ProjectAuditResponse> {
    const response = await this.client.get<ProjectAuditResponse>(`/api/v1/projects/${id}/audit`);
    return response.data;
  }

  async getProjectControls(id: string): Promise<ProjectControlsResponse> {
    const response = await this.client.get<ProjectControlsResponse>(
      `/api/v1/projects/${id}/controls`,
    );
    return response.data;
  }

  async getProjectRemediation(id: string): Promise<ProjectRemediationResponse> {
    const response = await this.client.get<ProjectRemediationResponse>(
      `/api/v1/projects/${id}/remediation`,
    );
    return response.data;
  }

  async getProjectSdlc(id: string): Promise<ProjectSdlcResponse> {
    const response = await this.client.get<ProjectSdlcResponse>(`/api/v1/projects/${id}/sdlc`);
    return response.data;
  }

  async getProjectProgress(id: string): Promise<ProjectProgressResponse> {
    const response = await this.client.get<ProjectProgressResponse>(
      `/api/v1/projects/${id}/progress`,
    );
    return response.data;
  }

  async getProjectRisks(id: string): Promise<ProjectRisksResponse> {
    const response = await this.client.get<ProjectRisksResponse>(`/api/v1/projects/${id}/risks`);
    return response.data;
  }

  // ─── Documents ──────────────────────────────────────────────

  async getProjectDocuments(id: string): Promise<DocumentResponse[]> {
    const response = await this.client.get<DocumentResponse[]>(
      `/api/v1/documents?project_id=${id}`,
    );
    return response.data;
  }

  async searchDocuments(request: DocumentSearchRequest): Promise<DocumentSearchResponse> {
    const response = await this.client.post<DocumentSearchResponse>(
      '/api/v1/documents/search',
      request,
    );
    return response.data;
  }

  // ─── AI ──────────────────────────────────────────────────────

  async submitAIQuery(request: AIQueryRequest): Promise<AIResponse> {
    const response = await this.client.post<AIResponse>('/api/v1/ai/query', request, {
      timeout: 60_000,
    });
    return response.data;
  }

  // ─── File Upload ─────────────────────────────────────────────

  async uploadFile(file: File, projectId?: string): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (projectId) {
      formData.append('project_id', projectId);
    }
    const response = await this.client.post<FileUploadResponse>(
      '/api/v1/files/upload',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    );
    return response.data;
  }

  async getFileDatasets(fileId: string): Promise<DatasetResponse[]> {
    const response = await this.client.get<DatasetResponse[]>(
      `/api/v1/files/${fileId}/datasets`,
    );
    return response.data;
  }

  // ─── Datasets ──────────────────────────────────────────────

  async getDatasets(): Promise<DatasetResponse[]> {
    const response = await this.client.get<DatasetResponse[]>('/api/v1/datasets');
    return response.data;
  }

  async getDatasetPreview(id: string): Promise<DatasetPreviewResponse> {
    const response = await this.client.get<DatasetPreviewResponse>(
      `/api/v1/datasets/${id}/preview`,
    );
    return response.data;
  }

  async confirmDataset(id: string, request?: DatasetConfirmRequest): Promise<DatasetDetailResponse> {
    const response = await this.client.post<DatasetDetailResponse>(
      `/api/v1/datasets/${id}/confirm`,
      request ?? {},
    );
    return response.data;
  }

  async queryDataset(id: string, request: DatasetQueryRequest): Promise<DatasetQueryResponse> {
    const response = await this.client.post<DatasetQueryResponse>(
      `/api/v1/datasets/${id}/query`,
      request,
    );
    return response.data;
  }

  // ─── Data Sources ───────────────────────────────────────────

  async getDataSources(): Promise<DataSourceResponse[]> {
    const response = await this.client.get<DataSourceResponse[]>('/api/v1/data-sources');
    return response.data;
  }
}

// Export a singleton instance
export const apiClient = new APIClient();

// Also export the class for testing / custom configuration
export { APIClient };
