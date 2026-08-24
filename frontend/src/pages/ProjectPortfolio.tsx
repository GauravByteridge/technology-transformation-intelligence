import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Filter, X, ChevronUp, ChevronDown } from 'lucide-react';
import { useProjects, usePortfolioSummary } from '@/hooks';
import { LoadingState } from '@/components/common/LoadingState';
import { ErrorState } from '@/components/common/ErrorState';
import { EmptyState } from '@/components/common/EmptyState';
import type { ProjectResponse, PortfolioProjectSummary } from '@/types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Enriched project combining base project data with health metrics */
interface EnrichedProject {
  id: string;
  name: string;
  status: string;
  overall_status: string;
  budget_total: number;
  budget_spent: number;
  budget_variance: number;
  progress_percentage: number;
  risk_level: string;
  resource_utilization_percentage: number;
  open_issues_count: number;
}

type SortField =
  | 'name'
  | 'status'
  | 'budget_total'
  | 'budget_spent'
  | 'budget_variance'
  | 'progress_percentage'
  | 'risk_level'
  | 'resource_utilization_percentage'
  | 'open_issues_count';

type SortDirection = 'asc' | 'desc';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Derive a risk level label from overall_status */
function deriveRiskLevel(overallStatus: string): string {
  switch (overallStatus) {
    case 'at_risk':
      return 'high';
    case 'delayed':
      return 'high';
    case 'on_track':
      return 'low';
    case 'completed':
      return 'low';
    default:
      return 'medium';
  }
}

/** Combine project list with portfolio health data */
function enrichProjects(
  projects: ProjectResponse[],
  healthMap: Map<string, PortfolioProjectSummary>,
): EnrichedProject[] {
  return projects.map((project) => {
    const health = healthMap.get(project.id);
    const overallStatus = health?.overall_status ?? project.status;
    return {
      id: project.id,
      name: project.name,
      status: overallStatus,
      overall_status: overallStatus,
      budget_total: health?.budget_total ?? 0,
      budget_spent: health?.budget_spent ?? 0,
      budget_variance: health?.budget_variance ?? 0,
      progress_percentage: health?.progress_percentage ?? 0,
      risk_level: deriveRiskLevel(overallStatus),
      resource_utilization_percentage: health?.resource_utilization_percentage ?? 0,
      open_issues_count: health?.open_issues_count ?? 0,
    };
  });
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'on_track':
      return 'bg-green-100 text-green-800 border-green-200';
    case 'at_risk':
      return 'bg-amber-100 text-amber-800 border-amber-200';
    case 'delayed':
      return 'bg-red-100 text-red-800 border-red-200';
    case 'completed':
      return 'bg-blue-100 text-blue-800 border-blue-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
}

function getStatusLabel(status: string): string {
  switch (status) {
    case 'on_track':
      return 'On Track';
    case 'at_risk':
      return 'At Risk';
    case 'delayed':
      return 'Delayed';
    case 'completed':
      return 'Completed';
    default:
      return status;
  }
}

function getRiskColor(risk: string): string {
  switch (risk) {
    case 'high':
      return 'bg-red-100 text-red-800 border-red-200';
    case 'medium':
      return 'bg-amber-100 text-amber-800 border-amber-200';
    case 'low':
      return 'bg-green-100 text-green-800 border-green-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
}

function getRiskLabel(risk: string): string {
  switch (risk) {
    case 'high':
      return 'High';
    case 'medium':
      return 'Medium';
    case 'low':
      return 'Low';
    default:
      return risk;
  }
}

function getVarianceColor(variance: number): string {
  if (variance > 0) return 'text-green-600';
  if (variance < 0) return 'text-red-600';
  return 'text-gray-600';
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface FilterDropdownProps {
  label: string;
  options: { value: string; label: string }[];
  selected: string[];
  onChange: (selected: string[]) => void;
}

function FilterDropdown({ label, options, selected, onChange }: FilterDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);

  const toggleOption = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((s) => s !== value));
    } else {
      onChange([...selected, value]);
    }
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors ${
          selected.length > 0
            ? 'border-blue-300 bg-blue-50 text-blue-700'
            : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
        }`}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <Filter className="h-3.5 w-3.5" />
        {label}
        {selected.length > 0 && (
          <span className="ml-1 inline-flex h-5 w-5 items-center justify-center rounded-full bg-blue-600 text-xs text-white">
            {selected.length}
          </span>
        )}
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />
          <div
            className="absolute left-0 top-full z-20 mt-1 w-48 rounded-md border border-gray-200 bg-white py-1 shadow-lg"
            role="listbox"
            aria-multiselectable="true"
            aria-label={`Filter by ${label}`}
          >
            {options.map((option) => (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={selected.includes(option.value)}
                onClick={() => toggleOption(option.value)}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-gray-50"
              >
                <span
                  className={`flex h-4 w-4 items-center justify-center rounded border ${
                    selected.includes(option.value)
                      ? 'border-blue-600 bg-blue-600'
                      : 'border-gray-300'
                  }`}
                >
                  {selected.includes(option.value) && (
                    <svg className="h-3 w-3 text-white" fill="currentColor" viewBox="0 0 12 12">
                      <path d="M10.28 2.28L4.5 8.06 1.72 5.28a.75.75 0 00-1.06 1.06l3.5 3.5a.75.75 0 001.06 0l6.5-6.5a.75.75 0 00-1.06-1.06z" />
                    </svg>
                  )}
                </span>
                {option.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function ProgressBar({ value }: { value: number }) {
  const clampedValue = Math.max(0, Math.min(100, value));
  const barColor =
    clampedValue >= 75 ? 'bg-green-500' : clampedValue >= 50 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-2">
      <div
        className="h-2 w-16 overflow-hidden rounded-full bg-gray-200"
        role="progressbar"
        aria-valuenow={clampedValue}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${clampedValue}%` }} />
      </div>
      <span className="text-sm text-gray-600">{clampedValue}%</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Filter & Sort Constants
// ---------------------------------------------------------------------------

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: 'on_track', label: 'On Track' },
  { value: 'at_risk', label: 'At Risk' },
  { value: 'delayed', label: 'Delayed' },
  { value: 'completed', label: 'Completed' },
];

const RISK_OPTIONS: { value: string; label: string }[] = [
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

// ---------------------------------------------------------------------------
// Main Page Component
// ---------------------------------------------------------------------------

export default function ProjectPortfolio() {
  const navigate = useNavigate();

  // Data fetching
  const {
    data: projectList,
    isLoading: projectsLoading,
    error: projectsError,
    refetch: refetchProjects,
  } = useProjects();

  const {
    data: portfolioSummary,
    isLoading: summaryLoading,
    error: summaryError,
    refetch: refetchSummary,
  } = usePortfolioSummary();

  // Search state with debounce
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Filter state
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [riskFilter, setRiskFilter] = useState<string[]>([]);

  // Sort state
  const [sortField, setSortField] = useState<SortField>('name');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  // Debounce search input at 300ms
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Build a health map keyed by project_id for O(1) lookups
  const healthMap = useMemo(() => {
    const map = new Map<string, PortfolioProjectSummary>();
    if (portfolioSummary?.projects) {
      for (const p of portfolioSummary.projects) {
        map.set(p.project_id, p);
      }
    }
    return map;
  }, [portfolioSummary]);

  // Enrich projects with health data
  const enrichedProjects = useMemo(() => {
    if (!projectList?.items) return [];
    return enrichProjects(projectList.items, healthMap);
  }, [projectList, healthMap]);

  // Client-side search filtering
  const searchFiltered = useMemo(() => {
    if (!debouncedSearch.trim()) return enrichedProjects;
    const searchLower = debouncedSearch.toLowerCase();
    return enrichedProjects.filter((p) =>
      p.name.toLowerCase().includes(searchLower),
    );
  }, [enrichedProjects, debouncedSearch]);

  // Client-side status filter
  const statusFiltered = useMemo(() => {
    if (statusFilter.length === 0) return searchFiltered;
    return searchFiltered.filter((p) => statusFilter.includes(p.overall_status));
  }, [searchFiltered, statusFilter]);

  // Client-side risk filter
  const riskFiltered = useMemo(() => {
    if (riskFilter.length === 0) return statusFiltered;
    return statusFiltered.filter((p) => riskFilter.includes(p.risk_level));
  }, [statusFiltered, riskFilter]);

  // Sort the filtered results
  const sortedProjects = useMemo(() => {
    return [...riskFiltered].sort((a, b) => {
      let comparison = 0;
      const aVal = a[sortField];
      const bVal = b[sortField];

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        comparison = aVal.localeCompare(bVal, undefined, { sensitivity: 'base' });
      } else if (typeof aVal === 'number' && typeof bVal === 'number') {
        comparison = aVal - bVal;
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [riskFiltered, sortField, sortDirection]);

  // Handle sort column click
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Clear all filters
  const clearFilters = () => {
    setSearchInput('');
    setDebouncedSearch('');
    setStatusFilter([]);
    setRiskFilter([]);
  };

  const hasActiveFilters =
    searchInput.length > 0 || statusFilter.length > 0 || riskFilter.length > 0;

  // Sort header render helper
  const SortHeader = ({ field, label }: { field: SortField; label: string }) => (
    <th
      className="cursor-pointer select-none px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:text-gray-700"
      onClick={() => handleSort(field)}
      aria-sort={
        sortField === field ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'
      }
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {sortField === field &&
          (sortDirection === 'asc' ? (
            <ChevronUp className="h-3.5 w-3.5" />
          ) : (
            <ChevronDown className="h-3.5 w-3.5" />
          ))}
      </span>
    </th>
  );

  // Combined loading
  const isLoading = projectsLoading || summaryLoading;

  // Combined error
  const error = projectsError || summaryError;

  const handleRetry = () => {
    refetchProjects();
    refetchSummary();
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold text-gray-900">Project Portfolio</h1>
        <LoadingState variant="full-page" message="Loading projects..." />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold text-gray-900">Project Portfolio</h1>
        <ErrorState
          message="Failed to load project portfolio. Please try again."
          onRetry={handleRetry}
          variant="full-page"
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-gray-900">Project Portfolio</h1>

      <div className="flex flex-col gap-4">
        {/* Search and Filters */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Search Field */}
          <div className="relative min-w-[240px] flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search by project name..."
              className="w-full rounded-md border border-gray-300 bg-white py-2 pl-9 pr-9 text-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              aria-label="Search projects"
            />
            {searchInput && (
              <button
                type="button"
                onClick={() => setSearchInput('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                aria-label="Clear search"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Filter Dropdowns */}
          <FilterDropdown
            label="Status"
            options={STATUS_OPTIONS}
            selected={statusFilter}
            onChange={setStatusFilter}
          />
          <FilterDropdown
            label="Risk"
            options={RISK_OPTIONS}
            selected={riskFilter}
            onChange={setRiskFilter}
          />

          {/* Clear Filters */}
          {hasActiveFilters && (
            <button
              type="button"
              onClick={clearFilters}
              className="inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-700"
            >
              <X className="h-3.5 w-3.5" />
              Clear all
            </button>
          )}
        </div>

        {/* Empty State */}
        {sortedProjects.length === 0 ? (
          <EmptyState
            message={
              hasActiveFilters
                ? 'No projects match the current filters'
                : 'No projects found'
            }
          />
        ) : (
          /* Table */
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <SortHeader field="name" label="Project Name" />
                  <SortHeader field="status" label="Status" />
                  <SortHeader field="budget_total" label="Budget" />
                  <SortHeader field="budget_spent" label="Actual Cost" />
                  <SortHeader field="budget_variance" label="Variance" />
                  <SortHeader field="progress_percentage" label="Progress" />
                  <SortHeader field="risk_level" label="Risk Level" />
                  <SortHeader field="resource_utilization_percentage" label="Utilization" />
                  <SortHeader field="open_issues_count" label="Open Issues" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {sortedProjects.map((project) => (
                  <tr
                    key={project.id}
                    onClick={() => navigate(`/projects/${project.id}`)}
                    className="cursor-pointer transition-colors hover:bg-gray-50"
                    role="link"
                    tabIndex={0}
                    aria-label={`View details for ${project.name}`}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        navigate(`/projects/${project.id}`);
                      }
                    }}
                  >
                    <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                      {project.name}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm">
                      <span
                        className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${getStatusColor(project.overall_status)}`}
                      >
                        {getStatusLabel(project.overall_status)}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                      {formatCurrency(project.budget_total)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                      {formatCurrency(project.budget_spent)}
                    </td>
                    <td
                      className={`whitespace-nowrap px-4 py-3 text-sm font-medium ${getVarianceColor(project.budget_variance)}`}
                    >
                      {formatCurrency(project.budget_variance)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm">
                      <ProgressBar value={project.progress_percentage} />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm">
                      <span
                        className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${getRiskColor(project.risk_level)}`}
                      >
                        {getRiskLabel(project.risk_level)}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                      {project.resource_utilization_percentage}%
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                      {project.open_issues_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
