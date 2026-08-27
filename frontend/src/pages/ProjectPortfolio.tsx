import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X, Plus, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { useProjects } from '@/hooks';

// ---------------------------------------------------------------------------
// Types (from PMO API)
// ---------------------------------------------------------------------------

interface PMOProject {
  id: number;
  code: string;
  name: string;
  overall_status: string;
  schedule_status: string;
  budget_status: string;
  manager: string | null;
  department: string | null;
  budget: number | null;
  actual_cost: number | null;
  variance_percentage: number | null;
  planned_percent: number | null;
  actual_percent: number | null;
  open_risks: number;
  high_severity_risks: number;
  overdue_actions: number;
  critical_defects: number;
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

function usePMOProjects() {
  const [projects, setProjects] = useState<PMOProject[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8000/api/v1/pmo')
      .then(r => r.json())
      .then(data => setProjects(data.projects || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return { projects, loading };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCurrency(value: number | null): string {
  if (!value) return '$0';
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const config: Record<string, { bg: string; text: string; dot: string }> = {
    red: { bg: 'bg-red-500/15', text: 'text-red-400', dot: 'bg-red-500' },
    amber: { bg: 'bg-amber-500/15', text: 'text-amber-400', dot: 'bg-amber-500' },
    green: { bg: 'bg-green-500/15', text: 'text-green-400', dot: 'bg-green-500' },
  };
  const c = config[normalized] || { bg: 'bg-gray-500/15', text: 'text-gray-400', dot: 'bg-gray-500' };
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${c.bg} ${c.text}`}>
      <span className={`w-2 h-2 rounded-full ${c.dot}`} />
      {status}
    </span>
  );
}

function ProgressBar({ planned, actual }: { planned: number; actual: number }) {
  const behind = actual < planned;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className={`font-semibold ${behind ? 'text-amber-400' : 'text-green-400'}`}>{actual}%</span>
        <span className="text-gray-500">plan: {planned}%</span>
      </div>
      <div className="h-1.5 bg-gray-700/50 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${behind ? 'bg-amber-500' : 'bg-green-500'}`}
          style={{ width: `${Math.min(actual, 100)}%` }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Project Card
// ---------------------------------------------------------------------------

function ProjectCard({ project, onClick }: { project: PMOProject; onClick: () => void }) {
  return (
    <div
      className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5 hover:border-teal-500/30 transition-all cursor-pointer"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onClick()}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono font-bold text-teal-400 bg-teal-500/10 px-2 py-0.5 rounded">
              {project.code}
            </span>
            {project.manager && (
              <span className="text-xs text-gray-500">• {project.manager}</span>
            )}
          </div>
          <h3 className="text-sm font-semibold text-white leading-snug">{project.name}</h3>
        </div>
        <StatusBadge status={project.overall_status} />
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Budget</p>
          <p className="text-sm font-semibold text-white">{formatCurrency(project.budget)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Actual</p>
          <p className="text-sm font-semibold text-white">{formatCurrency(project.actual_cost)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Variance</p>
          <p className={`text-sm font-semibold ${
            (project.variance_percentage || 0) < 0 ? 'text-red-400' : 'text-green-400'
          }`}>
            {project.variance_percentage != null ? `${project.variance_percentage > 0 ? '+' : ''}${project.variance_percentage}%` : '—'}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Schedule</p>
          <p className={`text-sm font-semibold ${
            project.schedule_status === 'On Track' ? 'text-green-400' :
            project.schedule_status === 'At Risk' ? 'text-amber-400' : 'text-red-400'
          }`}>
            {project.schedule_status}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Open Risks</p>
          <p className={`text-sm font-semibold ${project.open_risks >= 4 ? 'text-red-400' : project.open_risks >= 2 ? 'text-amber-400' : 'text-white'}`}>
            {project.open_risks}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Overdue</p>
          <p className={`text-sm font-semibold ${project.overdue_actions > 0 ? 'text-red-400' : 'text-white'}`}>
            {project.overdue_actions}
          </p>
        </div>
      </div>

      {/* Progress bar */}
      {project.planned_percent != null && project.actual_percent != null && (
        <ProgressBar planned={project.planned_percent} actual={project.actual_percent} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function ProjectPortfolio() {
  const navigate = useNavigate();
  const { projects, loading } = usePMOProjects();
  const { data: appProjects } = useProjects(); // For UUID-based navigation

  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput), 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Build code→UUID map from app_db projects
  const codeToId = useMemo(() => {
    const map = new Map<string, string>();
    if (appProjects?.items) {
      for (const p of appProjects.items) {
        if (p.project_code) map.set(p.project_code, p.id);
      }
    }
    return map;
  }, [appProjects]);

  const filteredProjects = useMemo(() => {
    if (!debouncedSearch.trim()) return projects;
    const q = debouncedSearch.toLowerCase();
    return projects.filter(p =>
      p.name.toLowerCase().includes(q) || p.code.toLowerCase().includes(q)
    );
  }, [projects, debouncedSearch]);

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <h1 className="text-2xl font-semibold text-white">Projects</h1>
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin w-6 h-6 border-2 border-teal-400 border-t-transparent rounded-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Projects</h1>
          <p className="text-sm text-gray-400 mt-0.5">{projects.length} active transformation programmes</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-teal-600 text-white hover:bg-teal-500 transition-colors">
          <Plus size={16} />
          New Project
        </button>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search projects..."
          className="w-full pl-9 pr-9 py-2.5 bg-gray-800/50 border border-gray-700/50 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-teal-500 focus:border-teal-500"
        />
        {searchInput && (
          <button
            onClick={() => setSearchInput('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
          >
            <X size={14} />
          </button>
        )}
      </div>

      {/* Project cards */}
      {filteredProjects.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          {debouncedSearch ? 'No projects match your search.' : 'No projects found.'}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredProjects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onClick={() => {
                const uuid = codeToId.get(project.code);
                if (uuid) navigate(`/projects/${uuid}`);
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
