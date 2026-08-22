import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Filter, X, ChevronUp, ChevronDown } from 'lucide-react';
import { useProjects } from '../../hooks';
import { LoadingState } from '../common/LoadingState';
import { EmptyState } from '../common/EmptyState';
import type { ProjectSummary, ProjectFilters, ProjectStatus, RiskLevel } from '../../types';

// --- Helpers ---

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function getStatusColor(status: ProjectStatus): string {
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

function getStatusLabel(status: ProjectStatus): string {
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

function getRiskColor(risk: RiskLevel): string {
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

function getRiskLabel(risk: RiskLevel): string {
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

// --- Filter Dropdown Component ---

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

// --- Progress Bar Component ---

function ProgressBar({ value }: { value: number }) {
  const clampedValue = Math.max(0, Math.min(100, value));
  const barColor =
    clampedValue >= 75 ? 'bg-green-500' : clampedValue >= 50 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-16 overflow-hidden rounded-full bg-gray-200" role="progressbar" aria-valuenow={clampedValue} aria-valuemin={0} aria-valuemax={100}>
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${clampedValue}%` }} />
      </div>
      <span className="text-sm text-gray-600">{clampedValue}%</span>
    </div>
  );
}

// --- Sort Logic ---

type SortField = 'name' | 'project_manager' | 'status' | 'budget' | 'actual_cost' | 'variance' | 'progress' | 'risk' | 'resource_utilization' | 'open_issues';
type SortDirection = 'asc' | 'desc';

function sortProjects(projects: ProjectSummary[], field: SortField, direction: SortDirection): ProjectSummary[] {
  return [...projects].sort((a, b) => {
    let comparison = 0;
    const aVal = a[field];
    const bVal = b[field];

    if (typeof aVal === 'string' && typeof bVal === 'string') {
      comparison = aVal.localeCompare(bVal, undefined, { sensitivity: 'base' });
    } else if (typeof aVal === 'number' && typeof bVal === 'number') {
      comparison = aVal - bVal;
    }

    return direction === 'asc' ? comparison : -comparison;
  });
}

// --- Main Component ---

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

export function ProjectTable() {
  const navigate = useNavigate();

  // Search state with debounce
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Filter state
  const [statusFilter, setStatusFilter] = useState<string[]>([]);
  const [riskFilter, setRiskFilter] = useState<string[]>([]);
  const [managerFilter, setManagerFilter] = useState<string[]>([]);

  // Sort state - default: Project Name ascending
  const [sortField, setSortField] = useState<SortField>('name');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  // Debounce search input at 300ms
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Build API filters
  const apiFilters: ProjectFilters = useMemo(() => {
    const filters: ProjectFilters = {};
    if (statusFilter.length > 0) filters.status = statusFilter as ProjectStatus[];
    if (riskFilter.length > 0) filters.risk = riskFilter as RiskLevel[];
    if (managerFilter.length > 0) filters.project_manager = managerFilter;
    return filters;
  }, [statusFilter, riskFilter, managerFilter]);

  // Fetch projects with server-side filters
  const { data: projects, isLoading, error } = useProjects(apiFilters);

  // Client-side search filtering on debounced value
  const filteredProjects = useMemo(() => {
    if (!projects) return [];
    if (!debouncedSearch.trim()) return projects;

    const searchLower = debouncedSearch.toLowerCase();
    return projects.filter(
      (p) =>
        p.name.toLowerCase().includes(searchLower) ||
        p.project_manager.toLowerCase().includes(searchLower)
    );
  }, [projects, debouncedSearch]);

  // Sort the filtered results
  const sortedProjects = useMemo(() => {
    return sortProjects(filteredProjects, sortField, sortDirection);
  }, [filteredProjects, sortField, sortDirection]);

  // Derive unique project managers for filter dropdown
  const managerOptions = useMemo(() => {
    if (!projects) return [];
    const managers = [...new Set(projects.map((p) => p.project_manager))].sort();
    return managers.map((m) => ({ value: m, label: m }));
  }, [projects]);

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
    setManagerFilter([]);
  };

  const hasActiveFilters = searchInput || statusFilter.length > 0 || riskFilter.length > 0 || managerFilter.length > 0;

  // Sort header render helper
  const SortHeader = ({ field, label }: { field: SortField; label: string }) => (
    <th
      className="cursor-pointer select-none px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:text-gray-700"
      onClick={() => handleSort(field)}
      aria-sort={sortField === field ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {sortField === field && (
          sortDirection === 'asc' ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />
        )}
      </span>
    </th>
  );

  // Loading state
  if (isLoading) {
    return <LoadingState message="Loading projects..." size="lg" />;
  }

  // Error state
  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm text-red-700">Failed to load projects. Please try again later.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Search and Filters */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Search Field */}
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search by project name or manager..."
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
        <FilterDropdown
          label="Manager"
          options={managerOptions}
          selected={managerFilter}
          onChange={setManagerFilter}
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
          dataType="projects"
          message={
            hasActiveFilters
              ? `No projects match the current ${searchInput ? 'search' : ''}${searchInput && (statusFilter.length > 0 || riskFilter.length > 0 || managerFilter.length > 0) ? ' and ' : ''}${statusFilter.length > 0 || riskFilter.length > 0 || managerFilter.length > 0 ? 'filters' : ''}`
              : undefined
          }
        />
      ) : (
        /* Table */
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <SortHeader field="name" label="Project Name" />
                <SortHeader field="project_manager" label="Project Manager" />
                <SortHeader field="status" label="Status" />
                <SortHeader field="budget" label="Budget" />
                <SortHeader field="actual_cost" label="Actual Cost" />
                <SortHeader field="variance" label="Variance" />
                <SortHeader field="progress" label="Progress" />
                <SortHeader field="risk" label="Risk" />
                <SortHeader field="resource_utilization" label="Utilization" />
                <SortHeader field="open_issues" label="Open Issues" />
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
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                    {project.project_manager}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${getStatusColor(project.status)}`}>
                      {getStatusLabel(project.status)}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                    {formatCurrency(project.budget)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                    {formatCurrency(project.actual_cost)}
                  </td>
                  <td className={`whitespace-nowrap px-4 py-3 text-sm font-medium ${getVarianceColor(project.variance)}`}>
                    {formatCurrency(project.variance)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    <ProgressBar value={project.progress} />
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${getRiskColor(project.risk)}`}>
                      {getRiskLabel(project.risk)}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                    {project.resource_utilization}%
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                    {project.open_issues}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
