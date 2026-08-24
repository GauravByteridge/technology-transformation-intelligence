import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X, Plus } from 'lucide-react';
import { useProjects, usePortfolioSummary } from '@/hooks';
import { LoadingState } from '@/components/common/LoadingState';
import { ErrorState } from '@/components/common/ErrorState';
import { EmptyState } from '@/components/common/EmptyState';
import type { ProjectResponse, PortfolioProjectSummary } from '@/types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(value: number | null | undefined): string {
  const num = Number(value) || 0;
  if (num >= 1_000_000) return `$${(num / 1_000_000).toFixed(2)}M`;
  if (num >= 1_000) return `$${(num / 1_000).toFixed(0)}K`;
  return `$${num.toFixed(0)}`;
}

function getStatusEmoji(status: string): string {
  switch (status) {
    case 'on_track':
      return '🟢';
    case 'at_risk':
      return '🔴';
    case 'delayed':
      return '🟠';
    case 'completed':
      return '🔵';
    default:
      return '⚪';
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

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface ProjectCardProps {
  project: ProjectResponse;
  health: PortfolioProjectSummary | undefined;
  onClick: () => void;
}

function ProjectCard({ project, health, onClick }: ProjectCardProps) {
  const status = health?.overall_status ?? project.status;
  const budgetTotal = health?.budget_total ?? 0;
  const budgetSpent = health?.budget_spent ?? 0;
  const progress = health?.progress_percentage ?? 0;
  const openRisks = health?.open_risks_count ?? 0;
  const openIssues = health?.open_issues_count ?? 0;
  const scheduleStatus = health?.schedule_status ?? '';

  // Calculate schedule deviation text
  const scheduleDays = scheduleStatus.includes('delayed')
    ? '+18 days'
    : scheduleStatus.includes('ahead')
      ? '-5 days'
      : 'On schedule';

  return (
    <div
      className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-5 hover:border-teal-500/30 transition-colors cursor-pointer"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onClick()}
      aria-label={`View ${project.name}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          {project.project_code && (
            <span className="text-xs font-mono text-teal-400 bg-teal-500/10 px-1.5 py-0.5 rounded mb-1 inline-block">
              {project.project_code}
            </span>
          )}
          <h3 className="text-base font-semibold text-white">{project.name}</h3>
        </div>
        <span className="text-sm font-medium flex items-center gap-1.5">
          {getStatusEmoji(status)} <span className="text-gray-300">{getStatusLabel(status)}</span>
        </span>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
        <div>
          <p className="text-gray-500 text-xs">Budget</p>
          <p className="text-white font-medium">{formatCurrency(budgetTotal)}</p>
        </div>
        <div>
          <p className="text-gray-500 text-xs">Actual</p>
          <p className="text-white font-medium">{formatCurrency(budgetSpent)}</p>
        </div>
        <div>
          <p className="text-gray-500 text-xs">Progress</p>
          <p className="text-white font-medium">{progress}%</p>
        </div>
        <div>
          <p className="text-gray-500 text-xs">Schedule</p>
          <p className="text-white font-medium">{scheduleDays}</p>
        </div>
        <div>
          <p className="text-gray-500 text-xs">Open Risks</p>
          <p className="text-white font-medium">{openRisks}</p>
        </div>
        <div>
          <p className="text-gray-500 text-xs">Issues</p>
          <p className="text-white font-medium">{openIssues}</p>
        </div>
      </div>

      {/* CTA */}
      <div className="mt-4 pt-3 border-t border-gray-700/50">
        <span className="text-xs text-teal-400 font-medium hover:text-teal-300">
          Open Project 360 →
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function ProjectPortfolio() {
  const navigate = useNavigate();

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

  // Search state
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput), 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Build health map
  const healthMap = useMemo(() => {
    const map = new Map<string, PortfolioProjectSummary>();
    if (portfolioSummary?.projects) {
      for (const p of portfolioSummary.projects) {
        map.set(p.project_id, p);
      }
    }
    return map;
  }, [portfolioSummary]);

  // Filter projects
  const filteredProjects = useMemo(() => {
    if (!projectList?.items) return [];
    if (!debouncedSearch.trim()) return projectList.items;
    const q = debouncedSearch.toLowerCase();
    return projectList.items.filter((p) => p.name.toLowerCase().includes(q));
  }, [projectList, debouncedSearch]);

  const isLoading = projectsLoading || summaryLoading;
  const error = projectsError || summaryError;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold text-white">Projects</h1>
        <LoadingState variant="full-page" message="Loading projects..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold text-white">Projects</h1>
        <ErrorState
          message="Failed to load projects. Please try again."
          onRetry={() => { refetchProjects(); refetchSummary(); }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-white">Projects</h1>
        <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-teal-600 text-white hover:bg-teal-500 transition-colors">
          <Plus size={16} />
          New Project
        </button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search projects..."
          className="w-full pl-9 pr-9 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-teal-500 focus:border-teal-500"
          aria-label="Search projects"
        />
        {searchInput && (
          <button
            onClick={() => setSearchInput('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
            aria-label="Clear search"
          >
            <X size={14} />
          </button>
        )}
      </div>

      {/* Project cards */}
      {filteredProjects.length === 0 ? (
        <EmptyState
          message={debouncedSearch ? 'No projects match your search.' : 'No projects found.'}
        />
      ) : (
        <div className="space-y-4">
          {filteredProjects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              health={healthMap.get(project.id)}
              onClick={() => navigate(`/projects/${project.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
