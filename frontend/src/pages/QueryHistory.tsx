import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Clock, Database, FileText, Bot, History } from 'lucide-react';

interface QueryHistoryItem {
  id: string;
  question: string;
  projectName: string;
  createdAt: string;
  sources: string[];
  durationMs: number | null;
}

// Demo data — replaced by API call in production
const DEMO_HISTORY: QueryHistoryItem[] = [
  {
    id: '1',
    question: 'Why is Project Alpha at risk?',
    projectName: 'Project Alpha',
    createdAt: new Date().toISOString(),
    sources: ['PostgreSQL', 'MongoDB', 'RAG'],
    durationMs: 3200,
  },
  {
    id: '2',
    question: "What is Project Beta's budget variance?",
    projectName: 'Project Beta',
    createdAt: new Date(Date.now() - 86400000).toISOString(),
    sources: ['PostgreSQL'],
    durationMs: 1800,
  },
  {
    id: '3',
    question: 'What are the biggest unresolved issues across the portfolio?',
    projectName: 'All Projects',
    createdAt: new Date(Date.now() - 172800000).toISOString(),
    sources: ['PostgreSQL', 'MongoDB'],
    durationMs: 4100,
  },
  {
    id: '4',
    question: 'What should the project manager prioritize for Project Gamma?',
    projectName: 'Project Gamma',
    createdAt: new Date(Date.now() - 259200000).toISOString(),
    sources: ['PostgreSQL', 'MongoDB', 'RAG'],
    durationMs: 2900,
  },
  {
    id: '5',
    question: 'Show me the resource utilization trend for the last quarter.',
    projectName: 'All Projects',
    createdAt: new Date(Date.now() - 345600000).toISOString(),
    sources: ['PostgreSQL'],
    durationMs: 2100,
  },
];

function formatRelativeTime(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `Today ${new Date(isoDate).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'Yesterday';
  return `${days} days ago`;
}

function SourceBadge({ source }: { source: string }) {
  const iconMap: Record<string, typeof Database> = {
    PostgreSQL: Database,
    MongoDB: Database,
    RAG: FileText,
  };
  const Icon = iconMap[source] || Database;

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-700/50 text-xs text-gray-300">
      <Icon size={11} />
      {source}
    </span>
  );
}

export default function QueryHistory() {
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  const filtered = DEMO_HISTORY.filter(
    (item) =>
      item.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.projectName.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-white">Query History</h1>
        <p className="text-sm text-gray-400 mt-1">
          Browse and restore previous AI query results with full source attribution.
        </p>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
        <input
          type="text"
          placeholder="Search queries..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-9 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-teal-500 focus:border-teal-500"
        />
      </div>

      {/* Query list */}
      <div className="space-y-3">
        {filtered.map((item) => (
          <div
            key={item.id}
            className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4 hover:border-teal-500/30 transition-colors cursor-pointer"
            onClick={() => navigate(`/ai?restore=${item.id}`)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && navigate(`/ai?restore=${item.id}`)}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <Bot size={14} className="text-teal-400 shrink-0" />
                  <h3 className="text-sm font-medium text-white truncate">
                    {item.question}
                  </h3>
                </div>
                <div className="flex items-center gap-3 text-xs text-gray-400">
                  <span>{item.projectName}</span>
                  <span className="flex items-center gap-1">
                    <Clock size={12} />
                    {formatRelativeTime(item.createdAt)}
                  </span>
                  {item.durationMs && <span>{(item.durationMs / 1000).toFixed(1)}s</span>}
                </div>
                <div className="flex items-center gap-2 mt-2">
                  {item.sources.map((source) => (
                    <SourceBadge key={source} source={source} />
                  ))}
                </div>
              </div>
              <button
                className="shrink-0 px-3 py-1.5 text-xs font-medium rounded-md bg-teal-600/20 text-teal-300 hover:bg-teal-600/30 transition-colors"
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/ai?restore=${item.id}`);
                }}
              >
                Open
              </button>
            </div>
          </div>
        ))}

        {filtered.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <History size={32} className="mx-auto mb-3 opacity-50" />
            <p className="text-sm">No queries found matching your search.</p>
          </div>
        )}
      </div>
    </div>
  );
}
