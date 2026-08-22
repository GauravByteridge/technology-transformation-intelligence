import { apiClient as baseClient, createApiClient } from '@/services/api-client';
import type { ApiClient } from '@/services/api-client';
import type {
  DashboardKPIs,
  ProjectHealthDistribution,
  BudgetChartItem,
  BurndownPoint,
  AuditChart,
  ResourceForecastPoint,
  ProjectSummary,
  ProjectDetail,
  ProjectFilters,
  Financial,
  JIRAIssue,
  Resource,
  AuditFinding,
  ITControl,
  ProjectDocument,
  AIResponse,
  AIQuestionRequest,
  ExecutiveBrief,
  DataSourceStatus,
} from '../types';

/**
 * Domain-specific API client that delegates HTTP communication
 * to the centralized typed ApiClient in services/api-client.ts.
 */
class APIClient {
  private client: ApiClient;

  constructor(client: ApiClient = baseClient) {
    this.client = client;
  }

  // ─── Dashboard ──────────────────────────────────────────────

  async getDashboardKPIs(): Promise<DashboardKPIs> {
    const response = await this.client.get<DashboardKPIs>('/api/dashboard/kpis');
    return response.data;
  }

  async getProjectHealthDistribution(): Promise<ProjectHealthDistribution> {
    const response = await this.client.get<ProjectHealthDistribution>(
      '/api/dashboard/charts/health'
    );
    return response.data;
  }

  async getBudgetChart(): Promise<BudgetChartItem[]> {
    const response = await this.client.get<BudgetChartItem[]>(
      '/api/dashboard/charts/budget'
    );
    return response.data;
  }

  async getBurndownChart(): Promise<BurndownPoint[]> {
    const response = await this.client.get<BurndownPoint[]>(
      '/api/dashboard/charts/burndown'
    );
    return response.data;
  }

  async getAuditChart(): Promise<AuditChart> {
    const response = await this.client.get<AuditChart>(
      '/api/dashboard/charts/audit'
    );
    return response.data;
  }

  async getResourceForecastChart(): Promise<ResourceForecastPoint[]> {
    const response = await this.client.get<ResourceForecastPoint[]>(
      '/api/dashboard/charts/resources'
    );
    return response.data;
  }

  // ─── Projects ───────────────────────────────────────────────

  async getProjects(filters?: ProjectFilters): Promise<ProjectSummary[]> {
    const params: Record<string, unknown> = {};
    if (filters?.status?.length) params.status = filters.status.join(',');
    if (filters?.risk?.length) params.risk = filters.risk.join(',');
    if (filters?.project_manager?.length)
      params.project_manager = filters.project_manager.join(',');
    if (filters?.search) params.search = filters.search;

    const response = await this.client.get<ProjectSummary[]>('/api/projects', {
      params,
    });
    return response.data;
  }

  async getProjectById(id: string): Promise<ProjectDetail> {
    const response = await this.client.get<ProjectDetail>(`/api/projects/${id}`);
    return response.data;
  }

  async getProjectFinancials(id: string): Promise<Financial[]> {
    const response = await this.client.get<Financial[]>(
      `/api/projects/${id}/financials`
    );
    return response.data;
  }

  async getProjectJIRA(id: string): Promise<JIRAIssue[]> {
    const response = await this.client.get<JIRAIssue[]>(
      `/api/projects/${id}/jira`
    );
    return response.data;
  }

  async getProjectAudit(id: string): Promise<AuditFinding[]> {
    const response = await this.client.get<AuditFinding[]>(
      `/api/projects/${id}/audit`
    );
    return response.data;
  }

  async getProjectControls(id: string): Promise<ITControl[]> {
    const response = await this.client.get<ITControl[]>(
      `/api/projects/${id}/controls`
    );
    return response.data;
  }

  async getProjectResources(id: string): Promise<Resource[]> {
    const response = await this.client.get<Resource[]>(
      `/api/projects/${id}/resources`
    );
    return response.data;
  }

  async getProjectDocuments(id: string): Promise<ProjectDocument[]> {
    const response = await this.client.get<ProjectDocument[]>(
      `/api/projects/${id}/documents`
    );
    return response.data;
  }

  // ─── AI ─────────────────────────────────────────────────────

  async askQuestion(request: AIQuestionRequest): Promise<AIResponse> {
    const response = await this.client.post<AIResponse>('/api/ai/ask', request, {
      timeout: 30_000,
    });
    return response.data;
  }

  // ─── Executive Brief ────────────────────────────────────────

  async generateBrief(projectId: string): Promise<ExecutiveBrief> {
    const response = await this.client.post<ExecutiveBrief>(
      `/api/briefs/${projectId}/generate`,
      {},
      { timeout: 60_000 },
    );
    return response.data;
  }

  async exportBriefPDF(projectId: string): Promise<Blob> {
    // NOTE: Blob response requires a separate axios call since the typed
    // ApiClient returns JSON by default. Using a dedicated client with
    // responseType configuration for binary downloads.
    const blobClient = createApiClient();
    const response = await blobClient.get<Blob>(
      `/api/briefs/${projectId}/export`,
      { timeout: 60_000 },
    );
    return response.data;
  }

  // ─── Data Sources ───────────────────────────────────────────

  async getDataSources(): Promise<DataSourceStatus[]> {
    const response = await this.client.get<DataSourceStatus[]>(
      '/api/datasources'
    );
    return response.data;
  }
}

// Export a singleton instance
export const apiClient = new APIClient();

// Also export the class for testing / custom configuration
export { APIClient };
