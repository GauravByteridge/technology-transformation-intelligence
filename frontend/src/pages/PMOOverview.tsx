import { useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  Clock,
  DollarSign,
  ChevronRight,
  Bot,
  ShieldAlert,
  Activity,
  Loader2,
} from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';

// ---------------------------------------------------------------------------
// Types (matches backend PMOOverviewResponse)
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

interface PMOAttentionItem {
  project_code: string;
  project_name: string;
  overall_status: string;
  items: string[];
  ai_assessment: string;
}

interface UnattendedAction {
  id: number;
  project_code: string;
  action: string;
  owner: string | null;
  due_date: string | null;
  status: string;
  source: string | null;
  times_repeated: number;
}

interface PMOOverviewData {
  total_projects: number;
  projects_at_risk: number;
  high_severity_risks: number;
  overdue_actions: number;
  budget_variance_projects: number;
  projects: PMOProject[];
  attention_items: PMOAttentionItem[];
  unattended_actions: UnattendedAction[];
}

// ---------------------------------------------------------------------------
// API Hook
// ---------------------------------------------------------------------------

function usePMOData() {
  const [data, setData] = useState<PMOOverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/v1/pmo');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        setData(json);
      } catch (e: any) {
        setError(e.message || 'Failed to load PMO data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  return { data, loading, error };
}

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const config: Record<string, { bg: string; text: string; border: string; dot: string }> = {
    red: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30', dot: 'bg-red-500' },
    amber: { bg: 'bg-amber-500/20', text: 'text-amber-400', border: 'border-amber-500/30', dot: 'bg-amber-500' },
    green: { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30', dot: 'bg-green-500' },
  };
  const c = config[normalized] || config.amber;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${c.bg} ${c.text} ${c.border}`}>
      <span className={`w-2 h-2 rounded-full ${c.dot}`} />
      {status}
    </span>
  );
}

function KPICard({ icon: Icon, label, value, subtext, variant }: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  subtext?: string;
  variant?: 'danger' | 'warning' | 'info';
}) {
  const colors = {
    danger: 'border-red-500/30 bg-red-500/5',
    warning: 'border-amber-500/30 bg-amber-500/5',
    info: 'border-gray-700/50 bg-gray-800/10 dark:bg-gray-800/50',
  };
  const iconColors = {
    danger: 'text-red-400',
    warning: 'text-amber-400',
    info: 'text-teal-400',
  };

  return (
    <div className={`rounded-xl border p-5 ${colors[variant || 'info']}`}>
      <div className="flex items-center gap-3 mb-2">
        <Icon size={18} className={iconColors[variant || 'info']} />
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</span>
      </div>
      <div className="text-2xl font-bold text-gray-900 dark:text-white">{value}</div>
      {subtext && <div className="text-xs text-gray-500 mt-1">{subtext}</div>}
    </div>
  );
}

function AttentionCard({ item, onNavigate }: { item: PMOAttentionItem; onNavigate: () => void }) {
  const isRed = item.overall_status.toLowerCase() === 'red';

  return (
    <div className={`rounded-xl border p-5 ${
      isRed ? 'border-red-500/30 bg-red-500/5' : 'border-amber-500/30 bg-amber-500/5'
    }`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <StatusBadge status={item.overall_status} />
          <span className="text-sm font-semibold text-white">{item.project_code}</span>
        </div>
        <button
          onClick={onNavigate}
          className="text-xs text-teal-400 hover:text-teal-300 flex items-center gap-0.5"
        >
          View <ChevronRight size={12} />
        </button>
      </div>
      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-3">{item.project_name}</h3>

      <ul className="space-y-1.5 mb-3">
        {item.items.slice(0, 5).map((text, idx) => (
          <li key={idx} className="text-xs text-gray-600 dark:text-gray-400 flex items-start gap-2">
            <span className="text-gray-400 dark:text-gray-600 mt-0.5">•</span>
            <span>{text}</span>
          </li>
        ))}
      </ul>

      <div className="pt-2 border-t border-gray-200 dark:border-gray-700/30">
        <div className="flex items-center gap-1.5">
          <Bot size={12} className="text-teal-400" />
          <span className="text-xs font-medium text-teal-400">AI Assessment:</span>
          <span className="text-xs text-gray-700 dark:text-gray-300">{item.ai_assessment}</span>
        </div>
      </div>
    </div>
  );
}

function ActionsTable({ actions }: { actions: UnattendedAction[] }) {
  if (actions.length === 0) return null;

  return (
    <div className="bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700/50 rounded-xl overflow-hidden shadow-sm dark:shadow-none">
      <div className="px-5 py-3 border-b border-gray-200 dark:border-gray-700/50">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Unattended Actions</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700/30">
              <th className="px-5 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Action</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Owner</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Due Date</th>
              <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Source</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700/20">
            {actions.map((action) => (
              <tr key={action.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/20">
                <td className="px-5 py-2.5">
                  <div className="text-gray-800 dark:text-gray-200 max-w-[300px] truncate">{action.action}</div>
                  <div className="text-xs text-gray-500">{action.project_code} • Raised {action.times_repeated}x</div>
                </td>
                <td className="px-4 py-2.5 text-gray-600 dark:text-gray-400 text-xs">{action.owner || '—'}</td>
                <td className="px-4 py-2.5 text-gray-600 dark:text-gray-400 text-xs">{action.due_date || '—'}</td>
                <td className="px-4 py-2.5 text-center">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                    action.status === 'Overdue' ? 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400' : 'bg-gray-700 text-gray-100 dark:bg-gray-600 dark:text-gray-200'
                  }`}>
                    {action.status}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-gray-500 text-xs">{action.source || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function PMOOverview() {
  const navigate = useNavigate();
  const { data, loading, error } = usePMOData();
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 size={32} className="animate-spin text-teal-400" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <AlertTriangle size={32} className="mx-auto text-red-400 mb-2" />
          <p className="text-gray-300">Failed to load PMO data</p>
          <p className="text-xs text-gray-500 mt-1">{error}</p>
        </div>
      </div>
    );
  }

  // Find project UUIDs from app_db for navigation (use project codes as fallback)
  const getProjectPath = (code: string) => {
    // Navigate to portfolio with code filter
    return `/portfolio`;
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>AI PMO Overview</h1>
          <p className={`text-sm mt-0.5 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Portfolio health and attention required</p>
        </div>
        <button
          onClick={() => navigate('/ai')}
          className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Bot size={16} />
          Ask AI
        </button>
      </div>

      {/* Top KPI Indicators */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <KPICard icon={Activity} label="Total Projects" value={data.total_projects} variant="info" />
        <KPICard icon={AlertTriangle} label="Projects at Risk" value={data.projects_at_risk} variant="danger" />
        <KPICard icon={ShieldAlert} label="High-Severity Risks" value={data.high_severity_risks} variant="warning" />
        <KPICard icon={Clock} label="Overdue Actions" value={data.overdue_actions} variant="danger" />
        <KPICard icon={DollarSign} label="Budget Variance" value={data.budget_variance_projects} subtext="projects over budget" variant="warning" />
      </div>

      {/* Project Health Table */}
      <div className="bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700/50 rounded-xl overflow-hidden shadow-sm dark:shadow-none">
        <div className="px-5 py-3 border-b border-gray-200 dark:border-gray-700/50">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Project Health</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700/30">
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Project</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Overall</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Schedule</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Budget</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actual</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Planned</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Open Risks</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Overdue</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700/20">
              {data.projects.map((project) => (
                <tr
                  key={project.id}
                  className="hover:bg-gray-50 dark:hover:bg-gray-700/20 cursor-pointer transition-colors"
                  onClick={() => navigate('/portfolio')}
                >
                  <td className="px-5 py-3">
                    <div className="font-medium text-gray-900 dark:text-white">{project.code}</div>
                    <div className="text-xs text-gray-500 max-w-[280px] truncate">{project.name}</div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <StatusBadge status={project.overall_status} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs font-medium ${
                      project.schedule_status === 'On Track' ? 'text-green-400' :
                      project.schedule_status === 'At Risk' ? 'text-amber-400' : 'text-red-400'
                    }`}>
                      {project.schedule_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs font-medium ${
                      project.budget_status === 'On Budget' ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {project.budget_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {project.actual_percent != null && project.planned_percent != null ? (
                      <span className={`text-xs font-bold ${
                        project.actual_percent >= project.planned_percent ? 'text-green-400' : 'text-amber-400'
                      }`}>
                        {project.actual_percent}%
                      </span>
                    ) : (
                      <span className="text-xs text-gray-500">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {project.planned_percent != null ? (
                      <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                        {project.planned_percent}%
                      </span>
                    ) : (
                      <span className="text-xs text-gray-500">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs font-bold ${project.open_risks >= 4 ? 'text-red-400' : project.open_risks >= 2 ? 'text-amber-400' : 'text-gray-400'}`}>
                      {project.open_risks}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs font-bold ${project.overdue_actions > 0 ? 'text-red-400' : 'text-gray-400'}`}>
                      {project.overdue_actions}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <ChevronRight size={14} className="text-gray-500" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* PMO Attention Required */}
      {data.attention_items.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-400 mb-3">
            PMO Attention Required
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {data.attention_items.map((item) => (
              <AttentionCard
                key={item.project_code}
                item={item}
                onNavigate={() => navigate('/portfolio')}
              />
            ))}
          </div>
        </div>
      )}

      {/* Unattended Actions */}
      <ActionsTable actions={data.unattended_actions} />
    </div>
  );
}
