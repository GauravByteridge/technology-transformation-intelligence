import { useState } from 'react';
import { Bot, ChevronDown, ChevronUp, Database, FileText, GitBranch, BarChart3, Table2, Info } from 'lucide-react';
import {
  useAIChat,
  useQueryHistory,
  useChatSessionStore,
  ChatThread,
  ChatInput,
  EvidencePanel,
  VisualizationRenderer,
  QueryHistory,
  SourcesUsedPanel,
  PartialFailureWarning,
  DataLineagePanel,
} from '@/features/ai-chat';
import type { SourceReference, EvidenceItem, LineageTrace, PartialFailureInfo } from '@/features/ai-chat/types';
import { ProjectSelector } from '@/components/common';

// ---------------------------------------------------------------------------
// Suggested Questions
// ---------------------------------------------------------------------------

const SUGGESTED_QUESTIONS = [
  'Why is this project at risk?',
  'Show me budget vs actual for all projects.',
  'What are the biggest unresolved issues?',
  'Show me risk distribution by severity.',
  'What should the project manager prioritize?',
  'Show me resource utilization trend.',
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Execution status steps shown while AI is processing */
function ExecutionStatus({ isVisible }: { isVisible: boolean }) {
  if (!isVisible) return null;

  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4 space-y-2">
      <p className="text-sm text-gray-300 font-medium">Analyzing...</p>
      <div className="space-y-1.5">
        <StatusStep label="Understanding question" done />
        <StatusStep label="Finding relevant catalog datasets" done />
        <StatusStep label="Identifying project/risk context" active />
        <StatusStep label="Querying relevant sources" pending />
        <StatusStep label="Preparing analytical dataset" pending />
        <StatusStep label="Generating visualization" pending />
      </div>
    </div>
  );
}

function StatusStep({ label, done, active, pending }: {
  label: string;
  done?: boolean;
  active?: boolean;
  pending?: boolean;
}) {
  return (
    <div className={`flex items-center gap-2 text-xs ${done ? 'text-green-400' : active ? 'text-teal-400' : 'text-gray-500'}`}>
      {done && <span>✓</span>}
      {active && <span className="animate-spin">⟳</span>}
      {pending && <span className="opacity-30">○</span>}
      <span>{label}</span>
    </div>
  );
}

/** Toggle between Chart and Table view */
function ViewToggle({ view, onViewChange }: { view: 'chart' | 'table'; onViewChange: (v: 'chart' | 'table') => void }) {
  return (
    <div className="inline-flex rounded-md bg-gray-700/50 p-0.5">
      <button
        onClick={() => onViewChange('chart')}
        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded transition-colors ${
          view === 'chart' ? 'bg-teal-600 text-white' : 'text-gray-400 hover:text-white'
        }`}
      >
        <BarChart3 size={12} />
        Chart
      </button>
      <button
        onClick={() => onViewChange('table')}
        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded transition-colors ${
          view === 'table' ? 'bg-teal-600 text-white' : 'text-gray-400 hover:text-white'
        }`}
      >
        <Table2 size={12} />
        Table
      </button>
    </div>
  );
}

/** Dataset info panel showing what was retrieved */
function DatasetInfoPanel({ sources, recordCount }: { sources: SourceReference[]; recordCount: number }) {
  if (sources.length === 0) return null;

  const sourceNames = sources
    .map((s: any) => s.source_name || s.name || '')
    .filter(Boolean)
    .join(', ') || 'Connected Sources';

  return (
    <div className="bg-gray-800/30 border border-gray-700/30 rounded-lg px-4 py-3">
      <div className="flex items-center gap-2 mb-2">
        <Info size={14} className="text-teal-400" />
        <span className="text-xs font-medium text-gray-300">Dataset Information</span>
      </div>
      <div className="flex items-center gap-4 text-xs text-gray-400 flex-wrap">
        <span>Sources: {sourceNames}</span>
        <span>Records: {recordCount}</span>
        <span>Retrieved: just now</span>
      </div>
    </div>
  );
}

/** Collapsible sources panel (dark themed) */
function SourcesPanel({ sources }: { sources: SourceReference[] }) {
  const [expanded, setExpanded] = useState(false);

  if (sources.length === 0) return null;

  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-700/30 transition-colors"
      >
        <span className="text-sm font-medium text-gray-300 flex items-center gap-2">
          <Database size={14} className="text-teal-400" />
          Sources Consulted ({sources.length})
        </span>
        {expanded ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
      </button>
      {expanded && (
        <div className="px-4 pb-3 space-y-2 border-t border-gray-700/50">
          {sources.map((source: any, idx) => {
            const name = source.source_name || source.name || 'Unknown';
            const type = source.source_type || source.type || 'document';
            const object = source.object_name || '';
            const records = source.records_returned ?? 0;
            const duration = source.query_duration_ms ?? 0;
            return (
              <div key={idx} className="flex items-center justify-between py-1.5">
                <div className="flex items-center gap-2 text-sm text-gray-300">
                  <SourceIcon type={type} />
                  <span>✓ {name}{object ? ` — ${object}` : ''}</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  <span>{records} records</span>
                  {duration > 0 && <span>{duration}ms</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function SourceIcon({ type }: { type: string }) {
  switch (type) {
    case 'postgresql':
      return <Database size={14} className="text-blue-400" />;
    case 'mongodb':
      return <Database size={14} className="text-green-400" />;
    case 'document':
    case 'rag':
      return <FileText size={14} className="text-amber-400" />;
    default:
      return <Database size={14} className="text-gray-400" />;
  }
}

/** Collapsible evidence panel (dark themed) */
function EvidencePanelDark({ evidence }: { evidence: EvidenceItem[] }) {
  const [expanded, setExpanded] = useState(false);

  if (evidence.length === 0) return null;

  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-700/30 transition-colors"
      >
        <span className="text-sm font-medium text-gray-300 flex items-center gap-2">
          📋 Evidence ({evidence.length})
        </span>
        {expanded ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
      </button>
      {expanded && (
        <div className="px-4 pb-3 space-y-2 border-t border-gray-700/50">
          {evidence.map((item: any, idx) => {
            // Handle both typed EvidenceItem and raw backend response format
            const sourceName = item.source_name || item.source || 'Unknown';
            const sourceType = item.source_type || item.data?.type || 'document';
            const objectName = item.object_name || item.data?.file_name || '';
            const confidence = item.confidence || '';
            const excerpt = item.excerpt || item.claim || item.data?.text_excerpt || '';
            const pageOrSection = item.page_number || item.data?.page_or_section || '';

            return (
              <div key={idx} className="bg-gray-900/50 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <SourceIcon type={sourceType} />
                  <span className="text-xs font-medium text-gray-300">
                    {sourceName}{objectName ? ` — ${objectName}` : ''}
                  </span>
                  {pageOrSection && (
                    <span className="text-xs text-gray-500">p.{pageOrSection}</span>
                  )}
                  {confidence && (
                    <span className="ml-auto text-xs px-1.5 py-0.5 rounded bg-gray-700 text-gray-400">
                      {String(confidence).replace('_', ' ')}
                    </span>
                  )}
                </div>
                {excerpt && (
                  <p className="text-xs text-gray-400 italic mt-1 line-clamp-4 whitespace-pre-line">
                    "{excerpt.slice(0, 300)}{excerpt.length > 300 ? '...' : ''}"
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/** Collapsible lineage panel (dark themed) */
function LineagePanelDark({ lineage }: { lineage: LineageTrace | null }) {
  const [expanded, setExpanded] = useState(false);

  if (!lineage) return null;

  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-700/30 transition-colors"
      >
        <span className="text-sm font-medium text-gray-300 flex items-center gap-2">
          <GitBranch size={14} className="text-teal-400" />
          Data Lineage
        </span>
        {expanded ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
      </button>
      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-700/50">
          <DataLineagePanel lineage={lineage} />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page — AI Query / Analytics Canvas
// ---------------------------------------------------------------------------

export default function AIAssistant() {
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<'chart' | 'table'>('chart');

  const { sendMessage, isLoading, messages, latestResponse, startNewConversation } =
    useAIChat(selectedProject ?? undefined);
  const { history } = useQueryHistory();
  const setActiveConversation = useChatSessionStore(
    (state) => state.setActiveConversation,
  );

  // Phase 8 — typed fields from latest response
  const sourcesConsulted: SourceReference[] =
    (latestResponse?.sources as unknown as SourceReference[]) ?? [];
  const evidenceItems: EvidenceItem[] =
    (latestResponse?.evidence as unknown as EvidenceItem[]) ?? [];
  const lineageTrace: LineageTrace | null =
    (latestResponse?.lineage_trace as unknown as LineageTrace) ?? null;
  const failedSources: PartialFailureInfo[] =
    (latestResponse?.failed_sources as unknown as PartialFailureInfo[]) ?? [];
  const isPartial = latestResponse?.is_partial ?? false;

  const hasVisualization =
    latestResponse &&
    latestResponse.visualization_spec &&
    latestResponse.response_type !== 'text';

  const totalRecords = sourcesConsulted.reduce((sum, s) => sum + (s.records_returned || 0), 0);

  const handleSuggestedQuestion = (question: string) => {
    sendMessage(question);
  };

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Sidebar — Query History */}
      <aside className="hidden lg:flex w-64 flex-shrink-0 flex-col border-r border-gray-700/50 bg-gray-900/50">
        <div className="flex items-center gap-2 border-b border-gray-700/50 px-3 py-3">
          <button
            type="button"
            onClick={startNewConversation}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-teal-600 px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-teal-500"
            aria-label="Start new conversation"
          >
            + New Query
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          <QueryHistory
            history={history}
            onSelectConversation={setActiveConversation}
          />
        </div>
      </aside>

      {/* Main Canvas Area */}
      <main className="flex flex-1 flex-col overflow-hidden">
        {/* Header with project context */}
        <header className="flex-shrink-0 border-b border-gray-700/50 px-6 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Bot size={20} className="text-teal-400" />
              <h1 className="text-lg font-semibold text-white">AI Query</h1>
            </div>
            <ProjectSelector
              value={selectedProject}
              onChange={setSelectedProject}
              label="Project:"
              showAllOption={true}
            />
          </div>
        </header>

        {/* Content area */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <div className="max-w-4xl mx-auto space-y-4">
            {/* Empty state — suggested questions */}
            {messages.length === 0 && !isLoading && (
              <div className="py-8 space-y-6">
                <div className="text-center">
                  <Bot size={40} className="mx-auto text-teal-400/50 mb-3" />
                  <h2 className="text-base font-medium text-white">
                    Ask questions across your connected enterprise information.
                  </h2>
                  <p className="text-sm text-gray-400 mt-1">
                    Get grounded answers with evidence, or analytical visualizations from real data.
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-2xl mx-auto">
                  {SUGGESTED_QUESTIONS.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSuggestedQuestion(q)}
                      className="text-left px-4 py-3 bg-gray-800/50 border border-gray-700/50 rounded-lg text-sm text-gray-300 hover:border-teal-500/30 hover:text-white transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Chat messages */}
            {messages.length > 0 && <ChatThread messages={messages} />}

            {/* Execution status */}
            <ExecutionStatus isVisible={isLoading} />

            {/* Partial failure warning */}
            {isPartial && failedSources.length > 0 && (
              <PartialFailureWarning failedSources={failedSources} />
            )}

            {/* Analytics Visualization Area */}
            {hasVisualization && (
              <div className="space-y-3">
                {/* View toggle */}
                <div className="flex items-center justify-between">
                  <ViewToggle view={activeView} onViewChange={setActiveView} />
                  <DatasetInfoPanel sources={sourcesConsulted} recordCount={totalRecords} />
                </div>

                {/* Chart or Table */}
                <div className="bg-gray-800/30 border border-gray-700/30 rounded-lg p-4">
                  {activeView === 'chart' ? (
                    <VisualizationRenderer
                      responseType={latestResponse!.response_type}
                      visualizationSpec={latestResponse!.visualization_spec}
                      isPartial={latestResponse!.is_partial}
                      failedSources={latestResponse!.failed_sources}
                    />
                  ) : (
                    /* Force table view of the same spec */
                    <VisualizationRenderer
                      responseType="table"
                      visualizationSpec={latestResponse!.visualization_spec}
                      isPartial={latestResponse!.is_partial}
                      failedSources={latestResponse!.failed_sources}
                    />
                  )}
                </div>
              </div>
            )}

            {/* Sources, Evidence, Lineage */}
            {sourcesConsulted.length > 0 && (
              <SourcesPanel sources={sourcesConsulted} />
            )}

            {evidenceItems.length > 0 && (
              <EvidencePanelDark evidence={evidenceItems} />
            )}

            <LineagePanelDark lineage={lineageTrace} />
          </div>
        </div>

        {/* Input area */}
        <div className="flex-shrink-0 border-t border-gray-700/50 px-6 py-3">
          <div className="max-w-4xl mx-auto">
            <ChatInput onSubmit={sendMessage} isLoading={isLoading} />
          </div>
        </div>
      </main>
    </div>
  );
}
