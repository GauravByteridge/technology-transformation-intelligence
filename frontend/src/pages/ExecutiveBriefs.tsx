import { useState } from 'react';
import {
  FileText,
  Plus,
  Calendar,
  TrendingUp,
  AlertTriangle,
  ExternalLink,
  ArrowLeft,
  Database,
  Eye,
} from 'lucide-react';

interface Brief {
  id: string;
  projectName: string;
  title: string;
  generatedAt: string;
  summary: string;
  metrics: {
    budgetVariance: string;
    progress: string;
    openRisks: number;
  };
  risks: string[];
  evidence: { source: string; detail: string }[];
  status: 'published' | 'draft' | 'generating';
}

const DEMO_BRIEFS: Brief[] = [
  {
    id: '1',
    projectName: 'Project Alpha',
    title: 'Project Alpha — Weekly Brief',
    generatedAt: new Date().toISOString(),
    summary:
      'Project remains at risk due to budget overrun (+14%), UAT delays, and 7 unresolved high-severity risks. Immediate attention required on resource allocation and vendor commitments.',
    metrics: {
      budgetVariance: '+14%',
      progress: '72%',
      openRisks: 7,
    },
    risks: ['UAT delay', 'Resource constraint', 'Budget pressure'],
    evidence: [
      { source: 'PostgreSQL — Finance', detail: 'Budget variance: $140,000 over plan' },
      { source: 'MongoDB — Risks', detail: '7 high-severity risks remain open' },
      { source: 'Meeting Notes.pdf', detail: 'UAT completion slipped by 2 weeks' },
    ],
    status: 'published',
  },
  {
    id: '2',
    projectName: 'Project Beta',
    title: 'Project Beta — Weekly Brief',
    generatedAt: new Date(Date.now() - 86400000).toISOString(),
    summary:
      'Project is on track with strong delivery velocity. Budget is within 3% variance and all milestones are on schedule.',
    metrics: {
      budgetVariance: '+3%',
      progress: '85%',
      openRisks: 2,
    },
    risks: ['Minor integration testing gap'],
    evidence: [
      { source: 'PostgreSQL — Finance', detail: 'Budget well within tolerance' },
      { source: 'MongoDB — Risks', detail: 'Only 2 low-severity risks' },
    ],
    status: 'published',
  },
  {
    id: '3',
    projectName: 'Project Gamma',
    title: 'Project Gamma — Monthly Brief',
    generatedAt: new Date(Date.now() - 604800000).toISOString(),
    summary:
      'Project attention required due to resource constraints. Two key developers transitioning out next sprint, replacement onboarding in progress.',
    metrics: {
      budgetVariance: '+8%',
      progress: '55%',
      openRisks: 4,
    },
    risks: ['Resource transition', 'Knowledge gap', 'Timeline pressure', 'Vendor dependency'],
    evidence: [
      { source: 'PostgreSQL — Resources', detail: '2 developers leaving next sprint' },
      { source: 'MongoDB — Risks', detail: '4 medium-severity risks' },
    ],
    status: 'published',
  },
];

function StatusBadge({ status }: { status: Brief['status'] }) {
  const styles = {
    published: 'bg-green-500/20 text-green-300',
    draft: 'bg-yellow-500/20 text-yellow-300',
    generating: 'bg-blue-500/20 text-blue-300 animate-pulse',
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${styles[status]}`}>
      {status}
    </span>
  );
}

export default function ExecutiveBriefs() {
  const [briefs] = useState<Brief[]>(DEMO_BRIEFS);
  const [selectedBrief, setSelectedBrief] = useState<Brief | null>(null);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Executive Briefs</h1>
          <p className="text-sm text-gray-400 mt-1">
            AI-generated project summaries backed by real evidence from connected sources.
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-teal-600 text-white hover:bg-teal-500 transition-colors">
          <Plus size={16} />
          Generate Brief
        </button>
      </div>

      {selectedBrief ? (
        /* Brief Detail View */
        <div className="space-y-6">
          <button
            onClick={() => setSelectedBrief(null)}
            className="flex items-center gap-1 text-sm text-teal-400 hover:text-teal-300 transition-colors"
          >
            <ArrowLeft size={14} />
            Back to Briefs
          </button>

          <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6 space-y-6">
            {/* Brief Header */}
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-xl font-semibold text-white">{selectedBrief.title}</h2>
                <div className="flex items-center gap-3 mt-2 text-sm text-gray-400">
                  <span className="flex items-center gap-1">
                    <Calendar size={14} />
                    Generated: {new Date(selectedBrief.generatedAt).toLocaleDateString()}
                  </span>
                  <StatusBadge status={selectedBrief.status} />
                </div>
              </div>
              <button className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-md bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors">
                <ExternalLink size={12} />
                Export
              </button>
            </div>

            {/* Executive Summary */}
            <div>
              <h3 className="text-sm font-medium text-gray-300 mb-2">Executive Summary</h3>
              <p className="text-sm text-gray-400 leading-relaxed">{selectedBrief.summary}</p>
            </div>

            {/* Key Metrics */}
            <div>
              <h3 className="text-sm font-medium text-gray-300 mb-3">Key Metrics</h3>
              <div className="grid grid-cols-3 gap-4">
                <MetricCard label="Budget Variance" value={selectedBrief.metrics.budgetVariance} />
                <MetricCard label="Progress" value={selectedBrief.metrics.progress} />
                <MetricCard label="Open Risks" value={selectedBrief.metrics.openRisks.toString()} />
              </div>
            </div>

            {/* Key Risks */}
            <div>
              <h3 className="text-sm font-medium text-gray-300 mb-2">Key Risks</h3>
              <ol className="space-y-2">
                {selectedBrief.risks.map((risk, idx) => (
                  <li key={idx} className="flex items-center gap-2 text-sm text-gray-400">
                    <AlertTriangle size={14} className="text-orange-400 shrink-0" />
                    <span className="text-gray-300">{idx + 1}. {risk}</span>
                  </li>
                ))}
              </ol>
            </div>

            {/* Evidence */}
            <div>
              <h3 className="text-sm font-medium text-gray-300 mb-2">Evidence</h3>
              <div className="space-y-2">
                {selectedBrief.evidence.map((item, idx) => (
                  <div key={idx} className="flex items-start gap-3 p-3 bg-gray-900/50 rounded-lg">
                    <Database size={14} className="text-teal-400 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-xs font-medium text-gray-300">{item.source}</p>
                      <p className="text-xs text-gray-500">{item.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3 pt-3 border-t border-gray-700/50">
              <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors">
                <Eye size={12} />
                View Sources
              </button>
              <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors">
                <ExternalLink size={12} />
                Export PDF
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Briefs List */
        <div className="space-y-3">
          {briefs.map((brief) => (
            <div
              key={brief.id}
              className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-5 hover:border-teal-500/30 transition-colors cursor-pointer"
              onClick={() => setSelectedBrief(brief)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && setSelectedBrief(brief)}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <FileText size={16} className="text-teal-400 shrink-0" />
                    <h3 className="text-sm font-medium text-white">{brief.title}</h3>
                    <StatusBadge status={brief.status} />
                  </div>
                  <p className="text-xs text-gray-400 mt-1 line-clamp-2">{brief.summary}</p>
                  <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <Calendar size={12} />
                      {new Date(brief.generatedAt).toLocaleDateString()}
                    </span>
                    <span className="flex items-center gap-1">
                      <TrendingUp size={12} />
                      Variance: {brief.metrics.budgetVariance}
                    </span>
                    <span className="flex items-center gap-1">
                      <AlertTriangle size={12} />
                      {brief.metrics.openRisks} risks
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-900/50 rounded-lg p-3">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-lg font-semibold text-white">{value}</p>
    </div>
  );
}
