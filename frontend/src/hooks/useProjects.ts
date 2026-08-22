import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type {
  ProjectSummary,
  ProjectDetail,
  ProjectFilters,
  Financial,
  JIRAIssue,
  Resource,
  AuditFinding,
  ITControl,
  ProjectDocument,
} from '../types';

export function useProjects(filters?: ProjectFilters) {
  return useQuery<ProjectSummary[]>({
    queryKey: ['projects', filters],
    queryFn: () => apiClient.getProjects(filters),
  });
}

export function useProjectDetail(projectId: string) {
  return useQuery<ProjectDetail>({
    queryKey: ['projects', projectId],
    queryFn: () => apiClient.getProjectById(projectId),
    enabled: !!projectId,
  });
}

export function useProjectFinancials(projectId: string) {
  return useQuery<Financial[]>({
    queryKey: ['projects', projectId, 'financials'],
    queryFn: () => apiClient.getProjectFinancials(projectId),
    enabled: !!projectId,
  });
}

export function useProjectJIRA(projectId: string) {
  return useQuery<JIRAIssue[]>({
    queryKey: ['projects', projectId, 'jira'],
    queryFn: () => apiClient.getProjectJIRA(projectId),
    enabled: !!projectId,
  });
}

export function useProjectAudit(projectId: string) {
  return useQuery<AuditFinding[]>({
    queryKey: ['projects', projectId, 'audit'],
    queryFn: () => apiClient.getProjectAudit(projectId),
    enabled: !!projectId,
  });
}

export function useProjectControls(projectId: string) {
  return useQuery<ITControl[]>({
    queryKey: ['projects', projectId, 'controls'],
    queryFn: () => apiClient.getProjectControls(projectId),
    enabled: !!projectId,
  });
}

export function useProjectResources(projectId: string) {
  return useQuery<Resource[]>({
    queryKey: ['projects', projectId, 'resources'],
    queryFn: () => apiClient.getProjectResources(projectId),
    enabled: !!projectId,
  });
}

export function useProjectDocuments(projectId: string) {
  return useQuery<ProjectDocument[]>({
    queryKey: ['projects', projectId, 'documents'],
    queryFn: () => apiClient.getProjectDocuments(projectId),
    enabled: !!projectId,
  });
}
