import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  DollarSign,
  TrendingUp,
  ShieldAlert,
  Activity,
  Bot,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Users,
  Loader2,
} from 'lucide-react';
import { useProjects } from '@/hooks';

// ---------------------------------------------------------------------------
// Types (from /api/v1/pmo/projects/:code)
// ---------------------------------------------------------------------------

interface ProjectDetail {
  code: string;
  name: string;
  overall_status: string;
  schedule_status: string;
  budget_status: string;
  manager: string | null;
  department: string | null;
  finance: { budget: number; actual_cost: number; forecast_cost: number | null; variance: number | null; variance_percentage: number | null } | null;
  progress: { planned_percent: number; actual_percent: number; status_date: string; notes: string | null }[];
  risks: { risk_id: string; severity: string; status: string; category: string | null; description: string | null; owner: string | null; due_date: string | null }[];
  milestones: { name: string; planned_date: string | null; actual_date: string | null; status: string }[];
  resources: { employee_name: string | null; role: string | null; allocation_percent: number | null; utilization_percent: number | null }[];
  issues: { issue_key: string; summary: string; status: string; priority: string; assignee: string | null; story_points: number | null; due_date: string | null }[];
  audit_findings: { finding_id: string; severity: string; status: string; description: string | null; due_date: string | null }[];
  actions: { action: string; owner: string | null; due_date: string | null; status: string; source: string | null; times_repeated: number }[];
  it_controls: { control_id: string; control_name: string; compliance_status: string; last_tested: string | null }[];
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

function useProjectDetailData(projectCode: string | null) {
  const [data, setData] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectCode) { setLoading(false); return; }
    setLoading(true);
    fetch(`http://localhost:8000/api/v1/pmo/projects/${projectCode}`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [projectCode]);

  return { data, loading, error };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string; dot: string }> = {
    red: { bg: 'bg-red-500/15', text: 'text-red-400', dot: 'bg-red-500' },
    amber: { bg: 'bg-amber-500/15', text: 'text-amber-400', dot: 'bg-amber-500' },
    green: { bg: 'bg-green-500/15', text: 'text-green-400', dot: 'bg-green-500' },
  };
  const c = config[status.toLowerCase()] || { bg: 'bg-gray-500/15', text: 'text-gray-400', dot: 'bg-gray-500' };
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${c.bg} ${c.text}`}>
      <span className={`w-2 h-2 rounded-full ${c.dot}`} />{status}
    </span>
  );
}

function formatCurrency(value: number | null): string {
  if (!value) return '$0';
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

// ---------------------------------------------------------------------------
// Tab Sections
// ---------------------------------------------------------------------------

function OverviewTab({ data }: { data: ProjectDetail }) {
  const latestProgress = data.progress[data.progress.length - 1];
  return (
    <div className="space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
          <p className="text-xs text-gray-400 mb-1">Budget</p>
          <p className="text-lg font-bold text-white">{formatCurrency(data.finance?.budget || null)}</p>
        </div>
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
          <p className="text-xs text-gray-400 mb-1">Actual Cost</p>
          <p className="text-lg font-bold text-white">{formatCurrency(data.finance?.actual_cost || null)}</p>
        </div>
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
          <p className="text-xs text-gray-400 mb-1">Progress</p>
          <p className="text-lg font-bold text-white">{latestProgress?.actual_percent || 0}%</p>
          <p className="text-xs text-gray-500">plan: {latestProgress?.planned_percent || 0}%</p>
        </div>
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
          <p className="text-xs text-gray-400 mb-1">Open Risks</p>
          <p className="text-lg font-bold text-red-400">{data.risks.filter(r => r.status === 'Open').length}</p>
        </div>
      </div>

      {/* Milestones */}
      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-white mb-3">Milestones</h3>
        <div className="space-y-2">
          {data.milestones.map((m, i) => (
            <div key={i} className="flex items-center justify-between py-2 border-b border-gray-700/30 last:border-0">
              <div className="flex items-center gap-2">
                {m.status === 'Completed' ? <CheckCircle2 size={14} className="text-green-400" /> :
                 m.status === 'Delayed' || m.status === 'At Risk' ? <AlertTriangle size={14} className="text-amber-400" /> :
                 <Clock size={14} className="text-gray-400" />}
                <span className="text-sm text-gray-200">{m.name}</span>
              </div>
              <div className="flex items-center gap-3 text-xs">
                <span className="text-gray-500">Plan: {m.planned_date || '—'}</span>
                {m.actual_date && <span className="text-green-400">Done: {m.actual_date}</span>}
                <span className={`font-medium ${
                  m.status === 'Completed' ? 'text-green-400' :
                  m.status === 'Delayed' || m.status === 'At Risk' ? 'text-amber-400' : 'text-gray-400'
                }`}>{m.status}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function RisksTab({ data }: { data: ProjectDetail }) {
  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700/30">
            <th className="px-4 py-3 text-left text-xs text-gray-400 uppercase">ID</th>
            <th className="px-4 py-3 text-left text-xs text-gray-400 uppercase">Severity</th>
            <th className="px-4 py-3 text-left text-xs text-gray-400 uppercase">Category</th>
            <th className="px-4 py-3 text-left text-xs text-gray-400 uppercase">Description</th>
            <th className="px-4 py-3 text-left text-xs text-gray-400 uppercase">Owner</th>
            <th className="px-4 py-3 text-left text-xs text-gray-400 uppercase">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-700/20">
          {data.risks.map((r, i) => (
            <tr key={i} className="hover:bg-gray-700/20">
              <td className="px-4 py-2.5 text-gray-300 font-mono text-xs">{r.risk_id}</td>
              <td className="px-4 py-2.5">
                <span className={`text-xs font-semibold ${
                  r.severity === 'Critical' ? 'text-red-400' : r.severity === 'High' ? 'text-amber-400' : 'text-gray-400'
                }`}>{r.severity}</span>
              </td>
              <td className="px-4 py-2.5 text-gray-400 text-xs">{r.category || '—'}</td>
              <td className="px-4 py-2.5 text-gray-300 text-xs max-w-[300px] truncate">{r.description || '—'}</td>
              <td className="px-4 py-2.5 text-gray-400 text-xs">{r.owner || '—'}</td>
              <td className="px-4 py-2.5">
                <span className={`text-xs px-2 py-0.5 rounded ${r.status === 'Open' ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`}>{r.status}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function IssuesTab({ data }: { data: ProjectDetail }) {
  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700/30">
            <th className="px-4 py-3 text-left text-xs text-gray-400 uppercase">Key</th>
            <th className="px-4 py-3 text-left text-xs text-gray-400 uppercase">Summary</th>
            <th className="px-4 py-3 text-left text-xs text-gray-400 uppercase">Priority</th>
            <th className="px-4 py-3 text-left text-xs text-gray-400 uppercase">Status</th>
            <th className="px-4 py-3 text-left text-xs text-gray-400 uppercase">Assignee</th>
            <th className="px-4 py-3 text-center text-xs text-gray-400 uppercase">SP</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-700/20">
          {data.issues.map((issue, i) => (
            <tr key={i} className="hover:bg-gray-700/20">
              <td className="px-4 py-2.5 text-teal-400 font-mono text-xs">{issue.issue_key}</td>
              <td className="px-4 py-2.5 text-gray-200 text-xs max-w-[250px] truncate">{issue.summary}</td>
              <td className="px-4 py-2.5">
                <span className={`text-xs font-semibold ${
                  issue.priority === 'Critical' ? 'text-red-400' : issue.priority === 'High' ? 'text-amber-400' : 'text-gray-400'
                }`}>{issue.priority}</span>
              </td>
              <td className="px-4 py-2.5 text-gray-300 text-xs">{issue.status}</td>
              <td className="px-4 py-2.5 text-gray-400 text-xs">{issue.assignee || '—'}</td>
              <td className="px-4 py-2.5 text-center text-gray-400 text-xs">{issue.story_points || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ResourcesTab({ data }: { data: ProjectDetail }) {
  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700/30">
            <th className="px-4 py-3 text-left text-xs text-gray-400 uppercase">Name</th>
            <th className="px-4 py-3 text-left text-xs text-gray-400 uppercase">Role</th>
            <th className="px-4 py-3 text-center text-xs text-gray-400 uppercase">Allocation</th>
            <th className="px-4 py-3 text-center text-xs text-gray-400 uppercase">Utilization</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-700/20">
          {data.resources.map((r, i) => (
            <tr key={i} className="hover:bg-gray-700/20">
              <td className="px-4 py-2.5 text-gray-200 text-sm">{r.employee_name || '—'}</td>
              <td className="px-4 py-2.5 text-gray-400 text-xs">{r.role || '—'}</td>
              <td className="px-4 py-2.5 text-center text-gray-300 text-xs">{r.allocation_percent}%</td>
              <td className="px-4 py-2.5 text-center">
                <span className={`text-xs font-semibold ${(r.utilization_percent || 0) > 100 ? 'text-red-400' : 'text-green-400'}`}>
                  {r.utilization_percent}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ActionsTab({ data }: { data: ProjectDetail }) {
  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700/30">
            <th className="px-4 py-3 text-left text-xs text-gray-400 uppercase">Action</th>
            <th className="px-4 py-3 text-left text-xs text-gray-400 uppercase">Owner</th>
            <th className="px-4 py-3 text-left text-xs text-gray-400 uppercase">Due</th>
            <th className="px-4 py-3 text-center text-xs text-gray-400 uppercase">Status</th>
            <th className="px-4 py-3 text-left text-xs text-gray-400 uppercase">Source</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-700/20">
          {data.actions.map((a, i) => (
            <tr key={i} className="hover:bg-gray-700/20">
              <td className="px-4 py-2.5 text-gray-200 text-xs max-w-[300px]">{a.action}</td>
              <td className="px-4 py-2.5 text-gray-400 text-xs">{a.owner || '—'}</td>
              <td className="px-4 py-2.5 text-gray-400 text-xs">{a.due_date || '—'}</td>
              <td className="px-4 py-2.5 text-center">
                <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                  a.status === 'Overdue' ? 'bg-red-500/20 text-red-400' : 'bg-gray-700 text-gray-300'
                }`}>{a.status}</span>
              </td>
              <td className="px-4 py-2.5 text-gray-500 text-xs">{a.source || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

const TABS = ['Overview', 'Risks', 'Issues', 'Resources', 'Actions', 'Audit'] as const;
type TabName = (typeof TABS)[number];

export default function Project360() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabName>('Overview');

  // Get project code from app_db UUID
  const { data: projectList } = useProjects();
  const appProject = projectList?.items?.find(p => p.id === projectId);
  const projectCode = appProject?.project_code || null;

  const { data, loading, error } = useProjectDetailData(projectCode);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 size={32} className="animate-spin text-teal-400" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-sm text-gray-400 hover:text-white mb-4">
          <ArrowLeft size={16} /> Back
        </button>
        <div className="text-center py-12">
          <AlertTriangle size={32} className="mx-auto text-red-400 mb-2" />
          <p className="text-gray-300">Failed to load project data</p>
          <p className="text-xs text-gray-500 mt-1">{error || 'Project not found'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={() => navigate(-1)} className="text-gray-400 hover:text-white transition-colors">
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono font-bold text-teal-400 bg-teal-500/10 px-2 py-0.5 rounded">{data.code}</span>
            <h1 className="text-lg font-bold text-white">{data.name}</h1>
            <StatusBadge status={data.overall_status} />
          </div>
          <div className="flex items-center gap-4 mt-1 text-xs text-gray-400">
            {data.manager && <span>Manager: {data.manager}</span>}
            {data.department && <span>• {data.department}</span>}
            <span>• Schedule: <span className={data.schedule_status === 'On Track' ? 'text-green-400' : 'text-amber-400'}>{data.schedule_status}</span></span>
            <span>• Budget: <span className={data.budget_status === 'On Budget' ? 'text-green-400' : 'text-red-400'}>{data.budget_status}</span></span>
          </div>
        </div>
        <button
          onClick={() => navigate('/ai')}
          className="flex items-center gap-2 px-3 py-2 bg-teal-600 hover:bg-teal-500 text-white text-xs font-medium rounded-lg transition-colors"
        >
          <Bot size={14} />
          Ask AI
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-700/50">
        {TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab
                ? 'border-teal-400 text-teal-400'
                : 'border-transparent text-gray-400 hover:text-white'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'Overview' && <OverviewTab data={data} />}
      {activeTab === 'Risks' && <RisksTab data={data} />}
      {activeTab === 'Issues' && <IssuesTab data={data} />}
      {activeTab === 'Resources' && <ResourcesTab data={data} />}
      {activeTab === 'Actions' && <ActionsTab data={data} />}
      {activeTab === 'Audit' && (
        <div className="space-y-4">
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-700/50">
              <h3 className="text-sm font-semibold text-white">Audit Findings</h3>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700/30">
                  <th className="px-4 py-2 text-left text-xs text-gray-400 uppercase">ID</th>
                  <th className="px-4 py-2 text-left text-xs text-gray-400 uppercase">Severity</th>
                  <th className="px-4 py-2 text-left text-xs text-gray-400 uppercase">Description</th>
                  <th className="px-4 py-2 text-left text-xs text-gray-400 uppercase">Status</th>
                  <th className="px-4 py-2 text-left text-xs text-gray-400 uppercase">Due</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/20">
                {data.audit_findings.map((f, i) => (
                  <tr key={i}>
                    <td className="px-4 py-2.5 text-gray-300 font-mono text-xs">{f.finding_id}</td>
                    <td className="px-4 py-2.5"><span className={`text-xs font-semibold ${f.severity === 'Critical' ? 'text-red-400' : f.severity === 'High' ? 'text-amber-400' : 'text-gray-400'}`}>{f.severity}</span></td>
                    <td className="px-4 py-2.5 text-gray-300 text-xs max-w-[300px] truncate">{f.description || '—'}</td>
                    <td className="px-4 py-2.5"><span className={`text-xs px-2 py-0.5 rounded ${f.status === 'Open' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'}`}>{f.status}</span></td>
                    <td className="px-4 py-2.5 text-gray-500 text-xs">{f.due_date || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-700/50">
              <h3 className="text-sm font-semibold text-white">IT Controls</h3>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700/30">
                  <th className="px-4 py-2 text-left text-xs text-gray-400 uppercase">Control ID</th>
                  <th className="px-4 py-2 text-left text-xs text-gray-400 uppercase">Name</th>
                  <th className="px-4 py-2 text-left text-xs text-gray-400 uppercase">Compliance</th>
                  <th className="px-4 py-2 text-left text-xs text-gray-400 uppercase">Last Tested</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/20">
                {data.it_controls.map((c, i) => (
                  <tr key={i}>
                    <td className="px-4 py-2.5 text-gray-300 font-mono text-xs">{c.control_id}</td>
                    <td className="px-4 py-2.5 text-gray-200 text-xs">{c.control_name}</td>
                    <td className="px-4 py-2.5">
                      <span className={`text-xs font-semibold ${
                        c.compliance_status === 'Compliant' ? 'text-green-400' :
                        c.compliance_status === 'Non-Compliant' ? 'text-red-400' : 'text-amber-400'
                      }`}>{c.compliance_status}</span>
                    </td>
                    <td className="px-4 py-2.5 text-gray-500 text-xs">{c.last_tested || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
