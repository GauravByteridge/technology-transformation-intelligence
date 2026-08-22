import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type {
  DashboardKPIs,
  ProjectHealthDistribution,
  BudgetChartItem,
  BurndownPoint,
  AuditChart,
  ResourceForecastPoint,
} from '../types';

export function useDashboardKPIs() {
  return useQuery<DashboardKPIs>({
    queryKey: ['dashboard', 'kpis'],
    queryFn: () => apiClient.getDashboardKPIs(),
  });
}

export function useProjectHealthDistribution() {
  return useQuery<ProjectHealthDistribution>({
    queryKey: ['dashboard', 'charts', 'health'],
    queryFn: () => apiClient.getProjectHealthDistribution(),
  });
}

export function useBudgetChart() {
  return useQuery<BudgetChartItem[]>({
    queryKey: ['dashboard', 'charts', 'budget'],
    queryFn: () => apiClient.getBudgetChart(),
  });
}

export function useBurndownChart() {
  return useQuery<BurndownPoint[]>({
    queryKey: ['dashboard', 'charts', 'burndown'],
    queryFn: () => apiClient.getBurndownChart(),
  });
}

export function useAuditChart() {
  return useQuery<AuditChart>({
    queryKey: ['dashboard', 'charts', 'audit'],
    queryFn: () => apiClient.getAuditChart(),
  });
}

export function useResourceForecastChart() {
  return useQuery<ResourceForecastPoint[]>({
    queryKey: ['dashboard', 'charts', 'resources'],
    queryFn: () => apiClient.getResourceForecastChart(),
  });
}
