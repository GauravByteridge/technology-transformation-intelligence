import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  TrendingDown,
  Clock,
  DollarSign,
  ChevronRight,
  Bot,
  ShieldAlert,
  Activity,
} from 'lucide-react';
import { useProjects } from '@/hooks';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ProjectHealth {
  id: string;
  code: string;
  name: string;
  overallStatus: 'Red' | 'Amber' | 'Green';
  scheduleStatus: string;
  budgetStatus: string;
  openRisks: number;
  criticalDefects: number;
  overdueActions: number;
  aiAssessment: string;
  attentionItems: string[];
}

// ---------------------------------------------------------------------------
// Static SMBC POC Data (matches seed data)
// ---------------------------------------------------------------------------

const PROJECTS: ProjectHealth[] = [
  {
    id: 'a1b2c3d4-0002-4000-8000-000000000001',
    code: 'GTB',
    name: 'Global Transaction Banking Platform Modernization',
    overallStatus: 'Red',
    scheduleStatus: 'Delayed',
    budgetStatus: 'Over Budget',
    openRisks: 5,
    criticalDefects: 3,
    overdueActions: 5,
    aiAssessment: 'High Risk — Immediate PMO intervention required',
    attentionItems: [
      'UAT delayed by 2 weeks — 3 critical defects blocking',
      'Budget 8% above plan ($3.6M overrun)',
      '2 senior developers departing — knowledge transfer incomplete',
      '5 overdue actions including disaster recovery test',
    ],
  },
  {
    id: 'a1b2c3d4-0002-4000-8000-000000000002',
    code: 'CMTT',
    name: 'Capital Markets Technology Transformation',
    overallStatus: 'Amber',
    scheduleStatus: 'At Risk',
    budgetStatus: 'On Budget',
    openRisks: 3,
    criticalDefects: 0,
    overdueActions: 2,
    aiAssessment: 'Needs Attention — Requirements deadlock and vendor dependency',
    attentionItems: [
      'Requirements sign-off pending for 10 weeks from 3 business units',
      'Market data vendor API changes require code refactoring',
      'Testing timeline at risk due to delayed requirements',
    ],
  },
  {
    id: 'a1b2c3d4-0002-4000-8000-000000000003',
    code: 'GDP',
    name: 'Global Digital Platform Enhancement',
    overallStatus: 'Green',
    scheduleStatus: 'On Track',
    budgetStatus: 'On Budget',
    openRisks: 2,
    criticalDefects: 0,
    overdueActions: 0,
    aiAssessment: 'On Track — No material concerns',
    attentionItems: [
      'Minor: API rate limiting fine-tuning needed before peak load',
    ],
  },
  {
    id: 'a1b2c3d4-0002-4000-8000-000000000004',
    code: 'RRRT',
    name: 'Regulatory & Risk Reporting Transformation',
    overallStatus: 'Amber',
    scheduleStatus: 'Delayed',
    budgetStatus: 'On Budget',
    openRisks: 3,
    criticalDefects: 0,
    overdueActions: 3,
    aiAssessment: 'Needs Attention — Regulatory deadline at risk',
    attentionItems: [
      'Data quality gaps (34% failure rate) in upstream risk systems',
      'Basel IV reporting requirements changed — scope expansion',
      'Testing delayed — regulatory test scenarios unavailable',
    ],
  },
];

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: 'Red' | 'Amber' | 'Green' }) {
  const config = {
    Red: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30', dot: 'bg-red-500' },
    Amber: { bg: 'bg-amber-500/20', text: 'text-amber-400', border: 'border-amber-500/30', dot: 'bg-amber-500' },
    Green: { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30', dot: 'bg-green-500' },
  };
  const c = config[status];
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
    info: 'border-gray-700/50 bg-gray-800/50',
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
        <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">{label}</span>
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {subtext && <div className="text-xs text-gray-500 mt-1">{subtext}</div>}
    </div>
  );
}

function AttentionCard({ project }: { project: ProjectHealth }) {
  const navigate = useNavigate();

  if (project.overallStatus === 'Green') return null;

  return (
    <div className={`rounded-xl border p-5 ${
      project.overallStatus === 'Red'
        ? 'border-red-500/30 bg-red-500/5'
        : 'border-amber-500/30 bg-amber-500/5'
    }`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <StatusBadge status={project.overallStatus} />
          <span className="text-sm font-semibold text-white">{project.code}</span>
        </div>
        <button
          onClick={() => navigate(`/projects/${project.id}`)}
          className="text-xs text-teal-400 hover:text-teal-300 flex items-center gap-0.5"
        >
          View <ChevronRight size={12} />
        </button>
      </div>
      <h3 className="text-sm font-medium text-gray-200 mb-3">{project.name}</h3>

      <ul className="space-y-1.5 mb-3">
        {project.attentionItems.map((item, idx) => (
          <li key={idx} className="text-xs text-gray-400 flex items-start gap-2">
            <span className="text-gray-600 mt-0.5">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>

      <div className="pt-2 border-t border-gray-700/30">
        <div className="flex items-center gap-1.5">
          <Bot size={12} className="text-teal-400" />
          <span className="text-xs font-medium text-teal-400">AI Assessment:</span>
          <span className="text-xs text-gray-300">{project.aiAssessment}</span>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function PMOOverview() {
  const navigate = useNavigate();

  const totalProjects = PROJECTS.length;
  const projectsAtRisk = PROJECTS.filter(p => p.overallStatus === 'Red' || p.overallStatus === 'Amber').length;
  const highSeverityRisks = PROJECTS.reduce((sum, p) => sum + p.openRisks, 0);
  const overdueActions = PROJECTS.reduce((sum, p) => sum + p.overdueActions, 0);
  const budgetVarianceProjects = PROJECTS.filter(p => p.budgetStatus === 'Over Budget').length;

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">AI PMO Overview</h1>
          <p className="text-sm text-gray-400 mt-0.5">Portfolio health and attention required</p>
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
        <KPICard icon={Activity} label="Total Projects" value={totalProjects} variant="info" />
        <KPICard icon={AlertTriangle} label="Projects at Risk" value={projectsAtRisk} variant="danger" />
        <KPICard icon={ShieldAlert} label="High-Severity Risks" value={highSeverityRisks} variant="warning" />
        <KPICard icon={Clock} label="Overdue Actions" value={overdueActions} variant="danger" />
        <KPICard icon={DollarSign} label="Budget Variance" value={budgetVarianceProjects} subtext="projects over budget" variant="warning" />
      </div>

      {/* Project Health Table */}
      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-700/50">
          <h2 className="text-sm font-semibold text-white">Project Health</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700/30">
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-400 uppercase">Project</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-400 uppercase">Overall</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-400 uppercase">Schedule</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-400 uppercase">Budget</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-400 uppercase">Open Risks</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-400 uppercase">Overdue</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/20">
              {PROJECTS.map((project) => (
                <tr
                  key={project.id}
                  className="hover:bg-gray-700/20 cursor-pointer transition-colors"
                  onClick={() => navigate(`/projects/${project.id}`)}
                >
                  <td className="px-5 py-3">
                    <div className="font-medium text-white">{project.code}</div>
                    <div className="text-xs text-gray-500 max-w-[250px] truncate">{project.name}</div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <StatusBadge status={project.overallStatus} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs font-medium ${
                      project.scheduleStatus === 'On Track' ? 'text-green-400' :
                      project.scheduleStatus === 'At Risk' ? 'text-amber-400' : 'text-red-400'
                    }`}>
                      {project.scheduleStatus}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs font-medium ${
                      project.budgetStatus === 'On Budget' ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {project.budgetStatus}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs font-bold ${project.openRisks >= 4 ? 'text-red-400' : project.openRisks >= 2 ? 'text-amber-400' : 'text-gray-400'}`}>
                      {project.openRisks}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs font-bold ${project.overdueActions > 0 ? 'text-red-400' : 'text-gray-400'}`}>
                      {project.overdueActions}
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
      <div>
        <h2 className="text-sm font-semibold text-white mb-3 uppercase tracking-wide text-gray-400">
          PMO Attention Required
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {PROJECTS.filter(p => p.overallStatus !== 'Green').map(project => (
            <AttentionCard key={project.id} project={project} />
          ))}
        </div>
      </div>
    </div>
  );
}
