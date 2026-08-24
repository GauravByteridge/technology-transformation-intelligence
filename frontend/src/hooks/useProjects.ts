import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type {
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
  DocumentResponse,
} from '@/types';

export function useProjects() {
  return useQuery<ProjectListResponse>({
    queryKey: ['projects'],
    queryFn: () => apiClient.getProjects(),
  });
}

export function useProjectDetail(id: string) {
  return useQuery<ProjectResponse>({
    queryKey: ['projects', id],
    queryFn: () => apiClient.getProjectById(id),
    enabled: !!id,
  });
}

export function useProjectHealth(id: string) {
  return useQuery<ProjectHealthResponse>({
    queryKey: ['projects', id, 'health'],
    queryFn: () => apiClient.getProjectHealth(id),
    enabled: !!id,
  });
}

export function useProjectFinance(id: string) {
  return useQuery<ProjectFinanceResponse>({
    queryKey: ['projects', id, 'finance'],
    queryFn: () => apiClient.getProjectFinance(id),
    enabled: !!id,
  });
}

export function useProjectJira(id: string) {
  return useQuery<ProjectJiraResponse>({
    queryKey: ['projects', id, 'jira'],
    queryFn: () => apiClient.getProjectJira(id),
    enabled: !!id,
  });
}

export function useProjectResources(id: string) {
  return useQuery<ProjectResourceResponse>({
    queryKey: ['projects', id, 'resources'],
    queryFn: () => apiClient.getProjectResources(id),
    enabled: !!id,
  });
}

export function useProjectAudit(id: string) {
  return useQuery<ProjectAuditResponse>({
    queryKey: ['projects', id, 'audit'],
    queryFn: () => apiClient.getProjectAudit(id),
    enabled: !!id,
  });
}

export function useProjectControls(id: string) {
  return useQuery<ProjectControlsResponse>({
    queryKey: ['projects', id, 'controls'],
    queryFn: () => apiClient.getProjectControls(id),
    enabled: !!id,
  });
}

export function useProjectRemediation(id: string) {
  return useQuery<ProjectRemediationResponse>({
    queryKey: ['projects', id, 'remediation'],
    queryFn: () => apiClient.getProjectRemediation(id),
    enabled: !!id,
  });
}

export function useProjectSdlc(id: string) {
  return useQuery<ProjectSdlcResponse>({
    queryKey: ['projects', id, 'sdlc'],
    queryFn: () => apiClient.getProjectSdlc(id),
    enabled: !!id,
  });
}

export function useProjectProgress(id: string) {
  return useQuery<ProjectProgressResponse>({
    queryKey: ['projects', id, 'progress'],
    queryFn: () => apiClient.getProjectProgress(id),
    enabled: !!id,
  });
}

export function useProjectDocuments(projectId: string) {
  return useQuery<DocumentResponse[]>({
    queryKey: ['documents', projectId],
    queryFn: () => apiClient.getProjectDocuments(projectId),
    enabled: !!projectId,
  });
}
